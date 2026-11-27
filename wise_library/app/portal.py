"""Read only rendered Wise pages; no private API keys or endpoint assumptions."""
import asyncio
import json
import logging
import re
import time
from urllib.parse import urljoin, urlsplit
from .domain import PORTAL_HOST, PortalError, AuthenticationError

log = logging.getLogger('wise_library')
PAGE_TIMEOUT_MS = 35000
NETWORK_RETRY_SECONDS = 10
ALERTS = '[role="alert"], .auth0-global-message-error, [id^="error-element"]'

# Wise keeps hidden copies of its lists (e.g. for printing), so only rendered text and cards count.
LOANS_SHOWN = "() => location.hostname === 'bibliotheek.wise.oclc.org' && document.body.innerText.includes('Totaal geleend:')"
HOLDS_SHOWN = """() => document.body.innerText.includes('Uitloggen') && (
  ['Je lijst is leeg', 'Geen reserveringen gevonden'].some(empty => document.body.innerText.includes(empty)) ||
  Array.from(document.querySelectorAll('app-publication-list-item')).some(el => el.getClientRects().length))"""
CARD_SCRIPT = """elements => elements.filter(el => el.getClientRects().length).map(el => ({
 title: (el.querySelector('[role="heading"][aria-level="4"],h4')?.textContent || '').trim(),
 text: el.innerText
}))"""


class Portal:
    def __init__(self, branch_id, session_path, username='', password=''):
        self.base = f"https://{PORTAL_HOST}/wise-apps/opac/branch/{branch_id}/my-account"
        self.session_path = session_path
        self.username = username
        self.password = password

    def _watch(self, page):
        self.trail, self.failures, self.script_errors, self.pending = [], [], [], set()
        self.started = time.monotonic()
        page.on('response', self._record)
        page.on('request', lambda request: self.pending.add(request))
        page.on('requestfinished', lambda request: self.pending.discard(request))
        page.on('requestfailed', self._failed)
        page.on('pageerror', lambda error: self.script_errors.append(str(error)[:150]))

    def _record(self, response):
        # Host and path only: query strings on the sign-in hops carry OAuth state.
        if response.request.is_navigation_request() and response.frame.parent_frame is None:
            self.trail.append(f'{time.monotonic() - self.started:.1f}s {response.status} {_where(response.url)}')

    def _failed(self, request):
        self.pending.discard(request)
        self.failures.append(f'{_where(request.url)} ({request.failure})')

    async def _describe(self, page):
        heading = page.locator('h1, h2').first
        heading = (await heading.inner_text()).strip()[:120] if await heading.count() else ''
        details = [f'at {_where(page.url)}, title {await page.title()!r}, heading {heading!r}',
                   f'navigations: {" -> ".join(self.trail) or "none"}',
                   f'failed requests: {self.failures[-8:] or "none"}',
                   f'pending requests: {sorted(_where(r.url) for r in self.pending)[:8] or "none"}',
                   f'script errors: {self.script_errors[-3:] or "none"}']
        # The login host can echo the username, so page text is only logged for Wise itself.
        if urlsplit(page.url).hostname == PORTAL_HOST:
            content = page.locator('main, [role="main"]').first
            content = content if await content.count() else page.locator('body')
            text = ' '.join((await content.inner_text()).split())
            details.append(f'page text: {text[:1200]!r}')
        return '; '.join(details)

    async def _sign_in(self, page):
        from playwright.async_api import TimeoutError as BrowserTimeout
        # Wait through the Wise -> IAM -> KB redirects. Never guess an auth URL.
        try:
            await page.wait_for_function("""() =>
              (location.hostname === 'bibliotheek.wise.oclc.org' && document.body.innerText.includes('Totaal geleend:')) ||
              (document.querySelector('#username') && document.querySelector('#password'))
            """, timeout=PAGE_TIMEOUT_MS)
        except BrowserTimeout:
            log.warning('Neither the loans page nor the login form appeared %s', await self._describe(page))
            # Nothing was submitted, so this is safe to retry at the next refresh.
            raise PortalError('The library login did not load. Will retry at the next refresh; '
                              'details are in the app log.') from None
        if await page.evaluate(LOANS_SHOWN):
            log.info('Saved session is still signed in')
            return
        log.info('Sign-in needed; login form reached at %s', _where(page.url))
        if not self.username or not self.password:
            raise AuthenticationError('Library session expired. Enter your library username and password in the app Configuration tab, or import a session.')
        parsed = urlsplit(page.url)
        if parsed.scheme != 'https' or parsed.hostname != 'inloggen.kb.nl':
            raise AuthenticationError('Unexpected library login destination. Automatic sign-in was stopped.')
        form = page.locator('form').filter(has=page.locator('#username'))
        if await form.count() != 1:
            raise AuthenticationError('The library login form has changed. Automatic sign-in was stopped.')
        action = urlsplit(urljoin(page.url, await form.get_attribute('action') or page.url))
        method = (await form.get_attribute('method') or '').upper()
        if action.scheme != 'https' or action.hostname != 'inloggen.kb.nl' or method != 'POST':
            raise AuthenticationError('Unexpected library form destination. Automatic sign-in was stopped.')
        if await page.locator('iframe[src*="captcha"], [data-sitekey]').count():
            raise AuthenticationError('The library requires a CAPTCHA. Sign in manually and import a session.')
        await form.locator('#username').fill(self.username)
        await form.locator('#password').fill(self.password)
        # Auth0 puts an invisible, pointer-events:none default-submit first; Playwright counts opacity:0 as visible.
        submit = form.locator('button[type="submit"][name="action"][value="default"]:not([aria-hidden="true"])')
        try:
            await submit.click(timeout=10000)
        except BrowserTimeout:
            # Nothing was submitted, so the next poll may safely try again.
            raise PortalError('The library sign-in button could not be pressed. '
                              'Will retry at the next refresh.') from None
        try:
            # Wise renders its own live regions, so alerts only signal a refusal on the login host.
            await page.wait_for_function("""alerts => location.hostname === 'bibliotheek.wise.oclc.org' ||
              Array.from(document.querySelectorAll(alerts + ', iframe[src*="captcha"], [data-sitekey]')).some(el => el.getClientRects().length)
            """, arg=ALERTS, timeout=PAGE_TIMEOUT_MS)
        except BrowserTimeout:
            log.warning('Sign-in submitted but not completed %s', await self._describe(page))
            raise AuthenticationError('Sign-in was not completed. Check your credentials; an extra verification step may require manual sign-in. Automatic retries are paused.') from None
        if urlsplit(page.url).hostname == PORTAL_HOST:
            try:
                await page.wait_for_function(LOANS_SHOWN, timeout=PAGE_TIMEOUT_MS)
            except BrowserTimeout:
                log.warning('Signed in, but the loans page did not finish loading %s', await self._describe(page))
                raise PortalError('Signed in, but the loans page did not load. Will retry at the next refresh.') from None
            log.info('Signed in')
            return
        alerts = [text.strip() for text in await page.locator(ALERTS).all_inner_texts() if text.strip()]
        log.warning('Sign-in refused with %s %s', alerts or 'no visible message', await self._describe(page))
        raise AuthenticationError('The library did not accept the sign-in or requires extra verification. Check the Configuration tab. Automatic retries are paused.')

    async def read(self):
        from playwright.async_api import async_playwright, Error as BrowserError, TimeoutError as BrowserTimeout
        from .domain import parse_loans
        try:
            state = json.loads(self.session_path.read_text(encoding='utf-8'))
        except (FileNotFoundError, ValueError):
            state = {'cookies':[], 'origins':[]}
        session_storage = state.pop('sessionStorage', {})
        async with async_playwright() as pw:
            browser = await pw.chromium.launch(headless=True, args=['--disable-dev-shm-usage'])
            try:
                context = await browser.new_context(storage_state=state, locale='nl-NL')
                # sessionStorage is excluded by Playwright's regular storage_state.
                if session_storage:
                    await context.add_init_script("const saved = " + json.dumps(session_storage) + "; if (location.origin === " + json.dumps(f'https://{PORTAL_HOST}') + ") { for (const [k,v] of Object.entries(saved)) if (sessionStorage.getItem(k) === null) sessionStorage.setItem(k,v); }")
                for attempt in (1, 2):
                    # A fresh page, because the failed one is still loading Chromium's error page.
                    page = await context.new_page()
                    self._watch(page)
                    try:
                        await page.goto(f'{self.base}/checkouts/physical-materials', wait_until='domcontentloaded',
                                        timeout=60000)
                        break
                    except BrowserError as error:
                        code = re.search(r'net::ERR_[A-Z_]+', str(error))
                        reason = code[0] if code else type(error).__name__
                        # Chromium reports ERR_NETWORK_CHANGED while the container network settles after start.
                        if code and attempt == 1:
                            log.info('The library portal is not reachable yet (%s); retrying in %s seconds',
                                     reason, NETWORK_RETRY_SECONDS)
                            await page.close()
                            await asyncio.sleep(NETWORK_RETRY_SECONDS)
                            continue
                        log.warning('The library portal could not be reached: %s', reason)
                        raise PortalError(f'The library portal could not be reached ({reason}). '
                                          'Will retry at the next refresh.') from None
                await self._sign_in(page)
                rows = await page.locator('app-publication-list-item').evaluate_all(CARD_SCRIPT)
                loans = parse_loans(rows, await page.locator('body').inner_text())
                reservations = []
                # These are separate collections, not three copies of one list.
                for kind in ['STANDARD', 'PARTIAL', 'SEQUENTIAL']:
                    await page.goto(f'{self.base}/my-holds/physical-materials/{kind}', wait_until='domcontentloaded', timeout=60000)
                    try:
                        await page.wait_for_function(HOLDS_SHOWN, timeout=PAGE_TIMEOUT_MS)
                    except BrowserTimeout:
                        log.warning('Reservation list %s could not be verified %s', kind, await self._describe(page))
                        raise PortalError('Reservation page could not be verified. Last successful data is retained.') from None
                    cards = await page.locator('app-publication-list-item').evaluate_all(CARD_SCRIPT)
                    for card in cards:
                        if not card['title']:
                            raise PortalError('Reservation layout has changed; a title could not be read.')
                        # Preserve displayed status text rather than guessing pickup-ready states.
                        reservations.append({'title': card['title'], 'details': card['text'], 'collection': kind})
                refreshed = await context.storage_state()
                refreshed['sessionStorage'] = await page.evaluate('Object.fromEntries(Object.entries(sessionStorage))')
                return loans, reservations, refreshed
            finally:
                await browser.close()


def _where(url):
    parts = urlsplit(url)
    return f'{parts.hostname}{parts.path}'
