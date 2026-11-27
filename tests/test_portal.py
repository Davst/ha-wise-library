"""Exercise the actual Chromium reader with controlled network responses."""

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from playwright.async_api import Browser

from wise_library.app import portal
from wise_library.app.domain import PortalError
from wise_library.app.portal import Portal

LOANS = """<html lang="nl"><body><a>Uitloggen</a><h3>Wat heb ik thuis</h3><p>Totaal geleend: 1</p>
<app-publication-list-item><input type="checkbox" data-test="physical-materials-renew-item-checkbox-7000001">
<img data-test="cover-image" src="https://bibliotheek.wise.oclc.org/cgi-bin/momredir.pl?size=280;isbn=9781234567897;key=1;">
<p><strong>Example, Ann</strong></p><div role="heading" aria-level="4">A test novel</div>
Geleend op: 01-11-2026 | Inleverdatum: 05-12-2026 | Van vestiging: Bibliotheek Example | Exemplaar: 123
<div data-test="new-due-date">Verlengen tot en met 24-12-2026</div></app-publication-list-item></body></html>"""
EMPTY_HOLDS = "<html><body><a>Uitloggen</a><h3>Mijn reserveringen</h3>Je lijst is leeg</body></html>"


class PortalBrowserTests(unittest.IsolatedAsyncioTestCase):
    async def test_actual_browser_reads_loans_and_verified_empty_holds(self):
        original = Browser.new_context

        async def context_with_fixture(browser, **kwargs):
            context = await original(browser, **kwargs)

            async def respond(route):
                html = LOANS if "/checkouts/" in route.request.url else EMPTY_HOLDS
                await route.fulfill(status=200, content_type="text/html", body=html)

            await context.route("**/*", respond)
            return context

        with tempfile.TemporaryDirectory() as temporary:
            state = Path(temporary) / "state.json"
            state.write_text(json.dumps({"cookies": [], "origins": []}), encoding="utf-8")
            with patch.object(Browser, "new_context", context_with_fixture):
                loans, holds, refreshed = await Portal("2709", state).read()
            self.assertEqual(
                loans,
                [
                    {
                        "id": "123",
                        "renew_id": "7000001",
                        "title": "A test novel",
                        "author": "Example, Ann",
                        "isbn": "9781234567897",
                        "due_date": "2026-12-05",
                        "branch": "Bibliotheek Example",
                        "renew_until": "2026-12-24",
                    }
                ],
            )
            self.assertEqual(holds, [])
            self.assertIn("sessionStorage", refreshed)


RENEW_PAGE = """<html lang="nl"><body><a>Uitloggen</a><h3>Wat heb ik thuis</h3><p>Totaal geleend: 3</p>
<div role="alert" id="alert"></div>
<button data-test="physical-materials-uncheck-all-button" onclick="document.querySelectorAll('input').forEach(i => i.checked = false)">Wis selectie</button>
<button data-test="physical-materials-renew-button" onclick="
  const picked = [...document.querySelectorAll('input:checked')].map(i => i.dataset.test.split('-').pop());
  fetch('/renewed?ids=' + picked.join(',')).then(() => document.getElementById('alert').textContent = %(message)r)">Verleng geselecteerde exemplaren</button>
%(cards)s</body></html>"""
CARD = """<app-publication-list-item><input type="checkbox" checked
 data-test="physical-materials-renew-item-checkbox-%(id)s"><div role="heading" aria-level="4">%(title)s</div>
Inleverdatum: 05-12-2026 | Van vestiging: Bibliotheek Example</app-publication-list-item>"""


class RenewBrowserTests(unittest.IsolatedAsyncioTestCase):
    async def renew(self, ids, message="De geselecteerde exemplaren zijn verlengd"):
        original = Browser.new_context
        renewed = []
        cards = "".join(CARD % {"id": number, "title": f"Book {number}"} for number in (101, 102, 103))
        page = RENEW_PAGE % {"cards": cards, "message": message}

        async def context_with_fixture(browser, **kwargs):
            context = await original(browser, **kwargs)

            async def respond(route):
                url = route.request.url
                if "/renewed" in url:
                    renewed.append(url.split("ids=")[-1])
                    await route.fulfill(status=200, body="ok")
                else:
                    await route.fulfill(status=200, content_type="text/html", body=page)

            await context.route("**/*", respond)
            return context

        with tempfile.TemporaryDirectory() as temporary:
            state = Path(temporary) / "state.json"
            state.write_text(json.dumps({"cookies": [], "origins": []}), encoding="utf-8")
            with (
                patch.object(Browser, "new_context", context_with_fixture),
                patch.object(portal, "PAGE_TIMEOUT_MS", 3000),
            ):
                try:
                    await Portal("2709", state).renew(ids)
                finally:
                    self.renewed = renewed

    async def test_renewing_one_loan_selects_only_that_loan_though_the_page_selects_all(self):
        await self.renew(["102"])
        self.assertEqual(self.renewed, ["102"])

    async def test_renewing_two_loans_selects_exactly_those(self):
        await self.renew(["101", "103"])
        self.assertEqual(self.renewed, ["101,103"])

    async def test_a_renewal_the_library_does_not_confirm_is_reported(self):
        with self.assertRaises(PortalError) as raised:
            await self.renew(["102"], message="Verlengen is niet mogelijk")
        self.assertIn("did not confirm", str(raised.exception))
        self.assertIn("Verlengen is niet mogelijk", str(raised.exception))

    async def test_a_loan_that_is_not_on_the_page_is_never_guessed(self):
        with self.assertRaises(PortalError):
            await self.renew(["999"])
        self.assertEqual(self.renewed, [])

    async def test_ids_that_are_not_numbers_are_refused_before_a_browser_opens(self):
        with self.assertRaises(PortalError):
            await Portal("2709", Path("unused.json")).renew(["1; drop"])
