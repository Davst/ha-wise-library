"""Read only rendered Wise pages; no private API keys or endpoint assumptions."""
import json
from .domain import PORTAL_HOST, PortalError

CARD_SCRIPT = """elements => elements.map(el => ({
 title: (el.querySelector('[role="heading"][aria-level="4"],h4')?.textContent || '').trim(),
 text: el.innerText
}))"""


class Portal:
    def __init__(self, branch_id, session_path):
        self.base = f"https://{PORTAL_HOST}/wise-apps/opac/branch/{branch_id}/my-account"
        self.session_path = session_path

    async def read(self):
        from playwright.async_api import async_playwright, TimeoutError as BrowserTimeout
        from .domain import parse_loans
        state = json.loads(self.session_path.read_text(encoding='utf-8'))
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
                try:
                    await page.get_by_text('Totaal geleend:', exact=False).wait_for(timeout=30000)
                except BrowserTimeout:
                    raise PortalError('Library login expired or the loan page did not load. Reconnect your session.') from None
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
