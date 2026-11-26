"""Sign in in an isolated browser and export only library authentication state."""
import argparse
import json
import re
import sys
from pathlib import Path
from urllib.parse import urlsplit

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from wise_library.app.domain import ALLOWED_HOSTS, PORTAL_HOST, validate_session
from wise_library.app.server import write_private


def main():
    from playwright.sync_api import sync_playwright
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--branch', default='2709', help='AanZet portal branch route')
    parser.add_argument('--output', type=Path, default=Path('.data/storage-state.json'))
    args = parser.parse_args()
    if not re.fullmatch(r'[0-9]{1,8}', args.branch):
        parser.error('branch must be numeric')
    url = f'https://{PORTAL_HOST}/wise-apps/opac/branch/{args.branch}/my-account/checkouts/physical-materials'
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=False)
        try:
            context = browser.new_context(locale='nl-NL')
            page = context.new_page()
            page.goto(url, wait_until='domcontentloaded')
            print('Sign in to the library in the new browser. Leave the Dutch loan overview open.')
            input('When "Totaal geleend" is visible, press Enter here to save the session: ')
            if urlsplit(page.url).hostname != PORTAL_HOST or not page.get_by_text('Totaal geleend:', exact=False).is_visible():
                raise SystemExit('No verified loan overview. Nothing was saved. Run the helper again after signing in.')
            state = context.storage_state()
            state['cookies'] = [cookie for cookie in state['cookies'] if cookie['domain'].lstrip('.') in ALLOWED_HOSTS]
            state['origins'] = [origin for origin in state['origins'] if urlsplit(origin['origin']).hostname in ALLOWED_HOSTS]
            state['sessionStorage'] = page.evaluate('Object.fromEntries(Object.entries(sessionStorage))')
            validate_session(state)
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.parent.chmod(0o700)
            write_private(args.output, state)
            print(f'Saved private session to {args.output.resolve()}')
            print('Import it in the Wise Library add-on, then delete this transfer copy. Never commit or share it.')
        finally:
            browser.close()


if __name__ == '__main__':
    main()
