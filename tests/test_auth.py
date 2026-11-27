import inspect
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from urllib.parse import parse_qs
from playwright.async_api import Browser, Error as BrowserError
from wise_library.app import portal
from wise_library.app.portal import Portal
from wise_library.app.domain import AuthenticationError, PortalError

LOANS = '''<html><body><a>Uitloggen</a><p>Totaal geleend: 1</p><app-publication-list-item><h4>Test novel</h4>
Inleverdatum: 05-12-2026 | Van vestiging: Example | Exemplaar: 123</app-publication-list-item></body></html>'''
HOLDS = '<html><body><a>Uitloggen</a>Je lijst is leeg</body></html>'
# Mirrors inloggen.kb.nl (Auth0): an invisible, unclickable default-submit button precedes the real one.
LOGIN = '''<html><body><form method="POST">
<button type="submit" value="default" aria-hidden="true" tabindex="-1" name="action"
style="opacity:0 !important;position:absolute !important;pointer-events:none !important">Continue</button>
<label for="username">Username</label><input id="username" name="username">
<label for="password">Password</label><input id="password" type="password" name="password">
<button type="submit" name="action" value="default">Continue</button></form>{error}</body></html>'''

# Wise keeps a hidden copy of the loan list (for printing) ahead of the visible one.
HIDDEN_COPY = LOANS.replace('<html><body>', '<html><body><div style="display:none"><p>Totaal geleend: 1</p>'
                            '<app-publication-list-item><h4>Test novel</h4>Inleverdatum: 05-12-2026'
                            '</app-publication-list-item></div>')
# Wise is a single-page app: a visible live region renders before the account content does.
SLOW_SPA = '''<html><body><div role="alert">Welkom</div><div id="app"></div>
<script>setTimeout(() => document.getElementById('app').outerHTML = {body}, 1500)</script></body></html>'''


class AutomaticLoginTests(unittest.IsolatedAsyncioTestCase):
    async def run_portal(self, *, signed_in=False, reject=False, unsafe_action=False, saved_session=False,
                         no_clickable_submit=False, stuck=False, slow_portal=False, loans_page=LOANS,
                         unreachable=False, holds_page=HOLDS):
        self.assertIn('username', inspect.signature(Portal).parameters)
        self.posts = []
        original = Browser.new_context
        logged_in = signed_in
        async def fixture_context(browser, **kwargs):
            context = await original(browser, **kwargs)
            async def respond(route):
                nonlocal logged_in
                url = route.request.url
                if unreachable:
                    await route.abort('namenotresolved')
                    return
                if 'inloggen.kb.nl' in url:
                    if route.request.method == 'POST':
                        self.posts.append(parse_qs(route.request.post_data))
                        if not reject:
                            logged_in = True
                            await route.fulfill(content_type='text/html', body='<script>location.replace("https://bibliotheek.wise.oclc.org/wise-apps/opac/branch/2709/my-account/checkouts/physical-materials")</script>')
                            return
                    html = LOGIN.format(error='<p role="alert">Invalid login</p>' if self.posts else '')
                    if unsafe_action:
                        html = html.replace('method="POST"', 'method="POST" action="https://example.invalid/steal"')
                    if no_clickable_submit:
                        html = html.replace('<button type="submit" name="action" value="default">Continue</button>', '')
                    await route.fulfill(content_type='text/html', body=html)
                elif stuck and url.endswith('/bootstrap.js'):
                    await route.abort('timedout')
                elif stuck and 'iam-emea' in url:
                    await route.fulfill(content_type='text/html', status=403,
                                        body='<title>Blocked</title><h1>Access denied</h1>'
                                             '<script src="https://iam-emea.wise.oclc.org/bootstrap.js"></script>')
                elif stuck:
                    await route.fulfill(content_type='text/html', body='<script>location.replace("https://iam-emea.wise.oclc.org/realms/wise/auth?state=secret-state")</script>')
                elif not logged_in:
                    await route.fulfill(content_type='text/html', body='<script>location.replace("https://inloggen.kb.nl/u/login")</script>')
                else:
                    body = loans_page if '/checkouts/' in url else holds_page
                    if slow_portal:
                        body = SLOW_SPA.format(body=json.dumps(body))
                    await route.fulfill(content_type='text/html', body=body)
            await context.route('**/*', respond)
            return context
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'state.json'
            if signed_in or saved_session:
                path.write_text(json.dumps({'cookies':[], 'origins':[]}))
            with patch.object(Browser, 'new_context', fixture_context), patch.object(portal, 'PAGE_TIMEOUT_MS', 3000):
                return await Portal('2709', path, username='example-reader', password='example-password').read()

    async def test_cold_start_signs_in_without_session_file(self):
        loans, holds, state = await self.run_portal()
        self.assertEqual(loans[0]['title'], 'Test novel')
        self.assertEqual(len(self.posts), 1)
        self.assertEqual(self.posts[0]['username'], ['example-reader'])
        self.assertEqual(self.posts[0]['password'], ['example-password'])

    async def test_expired_saved_session_signs_in_again(self):
        await self.run_portal(saved_session=True)
        self.assertEqual(len(self.posts), 1)

    async def test_working_session_skips_password_login(self):
        await self.run_portal(signed_in=True)
        self.assertEqual(self.posts, [])

    async def test_rejected_password_is_not_retried_or_echoed(self):
        self.assertIn('username', inspect.signature(Portal).parameters)
        with self.assertRaises(PortalError) as raised, self.assertLogs('wise_library', 'WARNING') as logs:
            await self.run_portal(reject=True)
        self.assertEqual(len(self.posts), 1)
        self.assertIn('Invalid login', '\n'.join(logs.output))
        self.assertNotIn('example-password', '\n'.join(logs.output))
        self.assertNotIn('example-password', str(raised.exception))
        self.assertNotIn('example-reader', str(raised.exception))

    async def test_unpressable_sign_in_button_submits_nothing_and_stays_retryable(self):
        with self.assertRaises(PortalError) as raised:
            await self.run_portal(no_clickable_submit=True)
        self.assertNotIsInstance(raised.exception, AuthenticationError)
        self.assertEqual(self.posts, [])

    async def test_credentials_never_post_to_foreign_form_action(self):
        self.assertIn('username', inspect.signature(Portal).parameters)
        with self.assertRaises(PortalError):
            await self.run_portal(unsafe_action=True)
        self.assertEqual(self.posts, [])

    async def test_login_that_never_loads_stays_retryable_and_logs_where_it_stopped(self):
        with self.assertRaises(PortalError) as raised, self.assertLogs('wise_library', 'WARNING') as logs:
            await self.run_portal(stuck=True)
        self.assertNotIsInstance(raised.exception, AuthenticationError)
        self.assertEqual(self.posts, [])
        output = '\n'.join(logs.output)
        self.assertIn('403 iam-emea.wise.oclc.org/realms/wise/auth', output)
        self.assertIn("title 'Blocked'", output)
        self.assertNotIn('Access denied', output)
        self.assertNotIn('secret-state', output)
        self.assertIn('iam-emea.wise.oclc.org/bootstrap.js (net::ERR_TIMED_OUT)', output)

    async def test_sign_in_succeeds_when_portal_shows_an_alert_before_the_loans(self):
        loans, holds, state = await self.run_portal(slow_portal=True)
        self.assertEqual(loans[0]['title'], 'Test novel')
        self.assertEqual(len(self.posts), 1)

    async def test_signed_in_but_unrecognised_loans_page_is_retryable_and_logs_its_text(self):
        page = ('<html><body><a>Uitloggen</a><main><h2>Wat heb ik thuis</h2><p>Onbekende melding</p></main>'
                '</body></html>')
        with self.assertRaises(PortalError) as raised, self.assertLogs('wise_library', 'WARNING') as logs:
            await self.run_portal(loans_page=page)
        self.assertNotIsInstance(raised.exception, AuthenticationError)
        self.assertEqual(len(self.posts), 1)
        self.assertIn('Onbekende melding', '\n'.join(logs.output))

    async def test_unreachable_portal_is_retryable_and_logs_the_network_error(self):
        with self.assertRaises(PortalError) as raised, self.assertLogs('wise_library', 'WARNING') as logs:
            await self.run_portal(unreachable=True)
        self.assertNotIsInstance(raised.exception, AuthenticationError)
        self.assertIn('ERR_NAME_NOT_RESOLVED', str(raised.exception))
        self.assertIn('ERR_NAME_NOT_RESOLVED', '\n'.join(logs.output))

    async def test_hidden_copy_of_the_loan_list_is_ignored_after_sign_in(self):
        loans, holds, state = await self.run_portal(loans_page=HIDDEN_COPY)
        self.assertEqual(len(loans), 1)

    async def test_hidden_copy_of_the_loan_list_is_ignored_with_a_saved_session(self):
        loans, holds, state = await self.run_portal(signed_in=True, loans_page=HIDDEN_COPY)
        self.assertEqual(len(loans), 1)
        self.assertEqual(self.posts, [])

    async def test_unrecognised_reservation_list_is_retryable_and_logs_which_list_and_its_text(self):
        page = '<html><body><a>Uitloggen</a><main><h2>Reserveringen</h2><p>Onbekende melding</p></main></body></html>'
        with self.assertRaises(PortalError) as raised, self.assertLogs('wise_library', 'WARNING') as logs:
            await self.run_portal(signed_in=True, holds_page=page)
        self.assertNotIsInstance(raised.exception, AuthenticationError)
        output = '\n'.join(logs.output)
        self.assertIn('STANDARD', output)
        self.assertIn('Onbekende melding', output)

    async def test_reservation_list_that_renders_slowly_is_still_read(self):
        loans, holds, state = await self.run_portal(signed_in=True,
                                                    holds_page=SLOW_SPA.format(body=json.dumps(HOLDS)))
        self.assertEqual(holds, [])

    async def test_empty_reservation_list_wording_used_by_wise_reads_as_no_reservations(self):
        page = '<html><body><a>Uitloggen</a><h2>Mijn reserveringen</h2><p>Geen reserveringen gevonden</p></body></html>'
        loans, holds, state = await self.run_portal(signed_in=True, holds_page=page)
        self.assertEqual(holds, [])


class NavigatingPage:
    url = 'https://inloggen.kb.nl/u/login?state=secret-state'
    async def title(self):
        raise BrowserError('Execution context was destroyed, most likely because of a navigation')


class DescribeTests(unittest.IsolatedAsyncioTestCase):
    async def test_page_that_navigates_while_being_described_still_yields_a_description(self):
        reader = Portal('2709', Path('unused.json'))
        reader.trail, reader.failures, reader.script_errors = ['0.1s 200 inloggen.kb.nl/u/login'], [], []
        reader.pending = set()
        description = await reader._describe(NavigatingPage())
        self.assertIn('inloggen.kb.nl/u/login', description)
        self.assertIn('could not be described', description)
        self.assertNotIn('secret-state', description)
