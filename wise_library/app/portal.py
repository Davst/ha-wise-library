"""Read only rendered Wise pages; no private API keys or endpoint assumptions."""

import base64
import json
import logging
import re
import time
from contextlib import asynccontextmanager
from urllib.parse import urljoin, urlsplit

from .covers import CoverError, openlibrary_cover
from .domain import PORTAL_HOST, AuthenticationError, PortalError, isbn_of

log = logging.getLogger("wise_library")
PAGE_TIMEOUT_MS = 35000
ALERTS = '[role="alert"], .auth0-global-message-error, [id^="error-element"]'

# Wise keeps hidden copies of its lists (e.g. for printing), so only rendered text and cards count.
LOANS_SHOWN = """() => location.hostname === 'bibliotheek.wise.oclc.org' &&
  document.body.innerText.includes('Totaal geleend:')"""
HOLDS_SHOWN = """() => document.body.innerText.includes('Uitloggen') && (
  ['Je lijst is leeg', 'Geen reserveringen gevonden'].some(empty => document.body.innerText.includes(empty)) ||
  Array.from(document.querySelectorAll('app-publication-list-item')).some(el => el.getClientRects().length))"""
CARD_SCRIPT = """elements => elements.filter(el => el.getClientRects().length).map(el => ({
 title: (el.querySelector('[role="heading"][aria-level="4"],h4')?.textContent || '').trim(),
 text: el.innerText,
 id: (el.querySelector('input[type="checkbox"]')?.dataset.test || '').match(/-(\\d+)$/)?.[1] || '',
 author: (el.querySelector('p strong')?.textContent || '').trim(),
 cover: el.querySelector('img[data-test="cover-image"]')?.src || '',
 renewUntil: (el.querySelector('[data-test="new-due-date"]')?.textContent || '').trim()
}))"""
COVER_SCRIPT = """async isbn => {
  const response = await fetch(`/cgi-bin/momredir.pl?size=280&isbn=${isbn}`, {credentials: 'same-origin'});
  if (!response.ok) throw new Error(`status ${response.status}`);
  const bytes = new Uint8Array(await response.arrayBuffer());
  if (bytes.length > 2097152) throw new Error('too large');
  let text = '';
  for (let at = 0; at < bytes.length; at += 8192) text += String.fromCharCode(...bytes.subarray(at, at + 8192));
  return btoa(text);
}"""
RENEWED = "De geselecteerde exemplaren zijn verlengd"
CHECKBOX = '[data-test="physical-materials-renew-item-checkbox-{id}"]'
CHECKED = 'input[type="checkbox"][data-test^="physical-materials-renew-item-checkbox-"]:checked'


class Portal:
    def __init__(self, branch_id, session_path, username="", password="", covers=None):
        self.base = f"https://{PORTAL_HOST}/wise-apps/opac/branch/{branch_id}/my-account"
        self.session_path = session_path
        self.username = username
        self.password = password
        self.covers = covers

    def _watch(self, page):
        self.trail, self.failures, self.script_errors, self.pending = [], [], [], set()
        self.started = time.monotonic()
        page.on("response", self._record)
        page.on("request", lambda request: self.pending.add(request))
        page.on("requestfinished", lambda request: self.pending.discard(request))
        page.on("requestfailed", self._failed)
        page.on("pageerror", lambda error: self.script_errors.append(str(error)[:150]))

    def _record(self, response):
        # Host and path only: query strings on the sign-in hops carry OAuth state.
        if response.request.is_navigation_request() and response.frame.parent_frame is None:
            self.trail.append(f"{time.monotonic() - self.started:.1f}s {response.status} {_where(response.url)}")

    def _failed(self, request):
        self.pending.discard(request)
        self.failures.append(f"{_where(request.url)} ({request.failure})")

    async def _describe(self, page):
        from playwright.async_api import Error as BrowserError

        details = [
            f"at {_where(page.url)}",
            f"navigations: {' -> '.join(self.trail) or 'none'}",
            f"failed requests: {self.failures[-8:] or 'none'}",
            f"pending requests: {sorted(_where(r.url) for r in self.pending)[:8] or 'none'}",
            f"script errors: {self.script_errors[-3:] or 'none'}",
        ]
        # A stalled page may still be navigating; describing it must never replace the caller's own error.
        try:
            details.append(f"title {await page.title()!r}")
            # The login host can echo the username, so headings and page text are only logged for Wise itself.
            if urlsplit(page.url).hostname == PORTAL_HOST:
                heading = page.locator("h1, h2").first
                heading = (await heading.inner_text()).strip()[:120] if await heading.count() else ""
                content = page.locator('main, [role="main"]').first
                content = content if await content.count() else page.locator("body")
                text = " ".join((await content.inner_text()).split())
                details.append(f"heading {heading!r}; page text: {text[:1200]!r}")
        except BrowserError:
            details.append("the page could not be described further because it was changing")
        return "; ".join(details)

    async def _sign_in(self, page):
        from playwright.async_api import Error as BrowserError
        from playwright.async_api import TimeoutError as BrowserTimeout

        # Wait through the Wise -> IAM -> KB redirects. Never guess an auth URL.
        try:
            await page.wait_for_function(
                f"""() => ({LOANS_SHOWN})() ||
              (document.querySelector('#username') && document.querySelector('#password'))
            """,
                timeout=PAGE_TIMEOUT_MS,
            )
        except BrowserTimeout:
            log.warning("Neither the loans page nor the login form appeared %s", await self._describe(page))
            # Nothing was submitted, so this is safe to retry at the next refresh.
            raise PortalError(
                "The library login did not load. Will retry at the next refresh; details are in the app log."
            ) from None
        if await page.evaluate(LOANS_SHOWN):
            log.info("Saved session is still signed in")
            return
        log.info("Sign-in needed; login form reached at %s", _where(page.url))
        if not self.username or not self.password:
            raise AuthenticationError(
                "Library session expired. Enter your library username and password in the app Configuration tab, or import a session."
            )
        parsed = urlsplit(page.url)
        if parsed.scheme != "https" or parsed.hostname != "inloggen.kb.nl":
            raise AuthenticationError("Unexpected library login destination. Automatic sign-in was stopped.")
        form = page.locator("form").filter(has=page.locator("#username"))
        if await form.count() != 1:
            raise AuthenticationError("The library login form has changed. Automatic sign-in was stopped.")
        action = urlsplit(urljoin(page.url, await form.get_attribute("action") or page.url))
        method = (await form.get_attribute("method") or "").upper()
        if action.scheme != "https" or action.hostname != "inloggen.kb.nl" or method != "POST":
            raise AuthenticationError("Unexpected library form destination. Automatic sign-in was stopped.")
        if await page.locator('iframe[src*="captcha"], [data-sitekey]').count():
            raise AuthenticationError("The library requires a CAPTCHA. Sign in manually and import a session.")
        await form.locator("#username").fill(self.username)
        await form.locator("#password").fill(self.password)
        # Auth0 puts an invisible, pointer-events:none default-submit first; Playwright counts opacity:0 as visible.
        submit = form.locator('button[type="submit"][name="action"][value="default"]:not([aria-hidden="true"])')
        try:
            await submit.click(timeout=10000)
        except BrowserTimeout:
            # Nothing was submitted, so the next poll may safely try again.
            raise PortalError(
                "The library sign-in button could not be pressed. Will retry at the next refresh."
            ) from None
        try:
            # Wise renders its own live regions, so alerts only signal a refusal on the login host.
            await page.wait_for_function(
                """alerts => location.hostname === 'bibliotheek.wise.oclc.org' ||
              Array.from(document.querySelectorAll(alerts + ', iframe[src*="captcha"], [data-sitekey]'))
                .some(el => el.getClientRects().length)
            """,
                arg=ALERTS,
                timeout=PAGE_TIMEOUT_MS,
            )
        except BrowserTimeout:
            log.warning("Sign-in submitted but not completed %s", await self._describe(page))
            raise AuthenticationError(
                "Sign-in was not completed. Check your credentials; an extra verification step may require manual sign-in. Automatic retries are paused."
            ) from None
        if urlsplit(page.url).hostname == PORTAL_HOST:
            try:
                await page.wait_for_function(LOANS_SHOWN, timeout=PAGE_TIMEOUT_MS)
            except BrowserTimeout:
                log.warning("Signed in, but the loans page did not finish loading %s", await self._describe(page))
                raise PortalError(
                    "Signed in, but the loans page did not load. Will retry at the next refresh."
                ) from None
            log.info("Signed in")
            return
        try:
            alerts = [text.strip() for text in await page.locator(ALERTS).all_inner_texts() if text.strip()]
        except BrowserError:
            alerts = ["unreadable while the page was changing"]
        log.warning("Sign-in refused with %s %s", alerts or "no visible message", await self._describe(page))
        raise AuthenticationError(
            "The library did not accept the sign-in or requires extra verification. Check the Configuration tab. Automatic retries are paused."
        )

    @asynccontextmanager
    async def _session(self):
        """Open the loans page in a fresh browser with the saved session, signed in, and hand back its context."""
        from playwright.async_api import Error as BrowserError
        from playwright.async_api import async_playwright

        try:
            state = json.loads(self.session_path.read_text(encoding="utf-8"))
        except (FileNotFoundError, ValueError):
            state = {"cookies": [], "origins": []}
        session_storage = state.pop("sessionStorage", {})
        async with async_playwright() as pw:
            browser = await pw.chromium.launch(headless=True, args=["--disable-dev-shm-usage"])
            try:
                context = await browser.new_context(storage_state=state, locale="nl-NL")
                # sessionStorage is excluded by Playwright's regular storage_state.
                if session_storage:
                    await context.add_init_script(
                        "const saved = "
                        + json.dumps(session_storage)
                        + "; if (location.origin === "
                        + json.dumps(f"https://{PORTAL_HOST}")
                        + ") { for (const [k,v] of Object.entries(saved)) if (sessionStorage.getItem(k) === null) sessionStorage.setItem(k,v); }"
                    )
                page = await context.new_page()
                self._watch(page)
                try:
                    await page.goto(
                        f"{self.base}/checkouts/physical-materials", wait_until="domcontentloaded", timeout=60000
                    )
                except BrowserError as error:
                    code = re.search(r"net::ERR_[A-Z_]+", str(error))
                    reason = code[0] if code else type(error).__name__
                    log.warning("The library portal could not be reached: %s", reason)
                    raise PortalError(
                        f"The library portal could not be reached ({reason}). Will retry at the next refresh."
                    ) from None
                await self._sign_in(page)
                yield context, page
            finally:
                await browser.close()

    @staticmethod
    async def _saved_state(context, page):
        refreshed = await context.storage_state()
        refreshed["sessionStorage"] = await page.evaluate("Object.fromEntries(Object.entries(sessionStorage))")
        return refreshed

    async def _cover(self, page, isbn):
        """Fetch a cover from inside the signed-in page; the library refuses plain scripts but serves its own page."""
        from playwright.async_api import Error as BrowserError

        try:
            return base64.b64decode(await page.evaluate(COVER_SCRIPT, isbn))
        except BrowserError as error:
            raise CoverError(str(error).splitlines()[0][:80]) from None

    async def read(self):
        from playwright.async_api import TimeoutError as BrowserTimeout

        from .domain import parse_loans, with_ids

        async with self._session() as (context, page):
            rows = await page.locator("app-publication-list-item").evaluate_all(CARD_SCRIPT)
            loans = parse_loans(rows, await page.locator("body").inner_text())
            reservations = []
            # These are separate collections, not three copies of one list.
            for kind in ["STANDARD", "PARTIAL", "SEQUENTIAL"]:
                await page.goto(
                    f"{self.base}/my-holds/physical-materials/{kind}", wait_until="domcontentloaded", timeout=60000
                )
                try:
                    await page.wait_for_function(HOLDS_SHOWN, timeout=PAGE_TIMEOUT_MS)
                except BrowserTimeout:
                    log.warning("Reservation list %s could not be verified %s", kind, await self._describe(page))
                    raise PortalError(
                        "Reservation page could not be verified. Last successful data is retained."
                    ) from None
                cards = await page.locator("app-publication-list-item").evaluate_all(CARD_SCRIPT)
                for card in cards:
                    if not card["title"]:
                        raise PortalError("Reservation layout has changed; a title could not be read.")
                    # Preserve displayed status text rather than guessing pickup-ready states.
                    reservations.append(
                        {
                            "title": card["title"],
                            "author": card["author"],
                            "isbn": isbn_of(card["cover"]),
                            "details": card["text"],
                            "collection": kind,
                        }
                    )
            if self.covers:
                shown = [item["isbn"] for item in loans + reservations]
                await self.covers.fetch_missing(shown, lambda isbn: self._cover(page, isbn))
                await self.covers.upgrade(shown, openlibrary_cover)
            return (
                loans,
                with_ids(reservations, ["title", "collection"], "hold|"),
                await self._saved_state(context, page),
            )

    async def renew(self, loan_ids):
        """Renew exactly these loans through the portal's own selection and renew button, then confirm it."""
        from playwright.async_api import TimeoutError as BrowserTimeout

        if not loan_ids or not all(re.fullmatch(r"[0-9]{1,12}", loan_id) for loan_id in loan_ids):
            raise PortalError("That loan cannot be renewed from here.")
        async with self._session() as (context, page):
            # The page opens with every loan selected, so the selection is cleared before choosing.
            await page.locator('[data-test="physical-materials-uncheck-all-button"]:visible').first.click(timeout=10000)
            for loan_id in loan_ids:
                box = page.locator(CHECKBOX.format(id=loan_id))
                if not await box.count():
                    raise PortalError("That loan is no longer on the account. Refresh and try again.")
                await box.check(timeout=10000)
            if await page.locator(CHECKED).count() != len(loan_ids):
                raise PortalError("The wrong books were selected, so nothing was renewed.")
            await page.locator('[data-test="physical-materials-renew-button"]:visible').first.click(timeout=10000)
            try:
                await page.get_by_text(RENEWED).first.wait_for(timeout=PAGE_TIMEOUT_MS)
            except BrowserTimeout:
                alerts = " ".join(await page.locator('[role="alert"]').all_inner_texts()).split()
                log.warning("Renewal was not confirmed; alerts %r", " ".join(alerts)[:200])
                raise PortalError(
                    "The library did not confirm the renewal. Check the loan in Wise."
                    + (f" It said: {' '.join(alerts)[:120]}" if alerts else "")
                ) from None
            return await self._saved_state(context, page)


def _where(url):
    parts = urlsplit(url)
    return f"{parts.hostname}{parts.path}"
