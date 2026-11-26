"""Read only rendered Wise pages; no private API keys or endpoint assumptions."""
import json
from urllib.parse import urljoin, urlsplit
from .domain import PORTAL_HOST, PortalError, AuthenticationError

CARD_SCRIPT = """elements => elements.map(el => ({
 title: (el.querySelector('[role="heading"][aria-level="4"],h4')?.textContent || '').trim(),
 text: el.innerText
}))"""


class Portal:
    def __init__(self, branch_id, session_path, username='', password=''):
        self.base = f"https://{PORTAL_HOST}/wise-apps/opac/branch/{branch_id}/my-account"
        self.session_path = session_path
        self.username = username
        self.password = password

    async def _sign_in(self, page):
        from playwright.async_api import TimeoutError as BrowserTimeout
        # Wait through the Wise -> IAM -> KB redirects. Never guess an auth URL.
        try:
            await page.wait_for_function("""() =>
              (location.hostname === 'bibliotheek.wise.oclc.org' && document.body.innerText.includes('Totaal geleend:')) ||
              (document.querySelector('#username') && document.querySelector('#password'))
            """, timeout=35000)
        except BrowserTimeout:
            raise AuthenticationError('The library login did not load. Check the login settings or import a session.') from None
        if urlsplit(page.url).hostname == PORTAL_HOST and await page.get_by_text('Totaal geleend:', exact=False).is_visible():
            return
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
            await page.wait_for_function("""() =>
              (location.hostname === 'bibliotheek.wise.oclc.org' && document.body.innerText.includes('Totaal geleend:')) ||
              Array.from(document.querySelectorAll('[role="alert"], .auth0-global-message-error, [id^="error-element"], iframe[src*="captcha"], [data-sitekey]')).some(el => el.getClientRects().length)
            """, timeout=35000)
        except BrowserTimeout:
            raise AuthenticationError('Sign-in was not completed. Check your credentials; an extra verification step may require manual sign-in. Automatic retries are paused.') from None
        if urlsplit(page.url).hostname != PORTAL_HOST or not await page.get_by_text('Totaal geleend:', exact=False).is_visible():
            raise AuthenticationError('The library did not accept the sign-in or requires extra verification. Check the Configuration tab. Automatic retries are paused.')

    async def read(self):
        from playwright.async_api import async_playwright, TimeoutError as BrowserTimeout
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
                page = await context.new_page()
                await page.goto(f'{self.base}/checkouts/physical-materials', wait_until='domcontentloaded', timeout=60000)
                await self._sign_in(page)
                rows = await page.locator('app-publication-list-item').evaluate_all(CARD_SCRIPT)
                loans = parse_loans(rows, await page.locator('body').inner_text())
                reservations = []
                # These are separate collections, not three copies of one list.
                for kind in ['STANDARD', 'PARTIAL', 'SEQUENTIAL']:
                    await page.goto(f'{self.base}/my-holds/physical-materials/{kind}', wait_until='domcontentloaded', timeout=60000)
                    try:
                        await page.get_by_text('Uitloggen', exact=True).wait_for(timeout=30000)
                        await page.locator('app-publication-list-item').first.wait_for(timeout=5000)
                    except BrowserTimeout:
                        pass
                    text = await page.locator('body').inner_text()
                    cards = await page.locator('app-publication-list-item').evaluate_all(CARD_SCRIPT)
                    if not cards:
                        if 'Je lijst is leeg' not in text or 'Uitloggen' not in text:
                            raise PortalError('Reservation page could not be verified. Last successful data is retained.')
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
