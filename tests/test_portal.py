"""Exercise the actual Chromium reader with controlled network responses."""

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from playwright.async_api import Browser

from wise_library.app.portal import Portal

LOANS = """<html lang="nl"><body><a>Uitloggen</a><h3>Wat heb ik thuis</h3><p>Totaal geleend: 1</p>
<app-publication-list-item><div role="heading" aria-level="4">A test novel</div>
Geleend op: 01-11-2026 | Inleverdatum: 05-12-2026 | Van vestiging: Bibliotheek Example | Exemplaar: 123
Verlengen tot en met 24-12-2026</app-publication-list-item></body></html>"""
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
                loans, [{"title": "A test novel", "due_date": "2026-12-05", "branch": "Bibliotheek Example"}]
            )
            self.assertEqual(holds, [])
            self.assertIn("sessionStorage", refreshed)
