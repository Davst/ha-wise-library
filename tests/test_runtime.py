import json
import tempfile
import unittest
from pathlib import Path
from wise_library.app.server import Runtime, DEFAULTS
from wise_library.app.domain import AuthenticationError


class NullBridge:
    def update(self, state, attributes): pass
    def unavailable(self): pass


class RuntimeAuthTests(unittest.IsolatedAsyncioTestCase):
    async def test_sync_succeeds_and_saves_only_library_hosts_when_login_leaves_other_cookies(self):
        refreshed = {'cookies':[{'domain':'.wise.oclc.org','name':'session','value':'x'},
                                {'domain':'.bibliotheekaanzet.nl','name':'consent','value':'y'}],
                     'origins':[{'origin':'https://bibliotheek.wise.oclc.org','localStorage':[]},
                                {'origin':'https://www.kb.nl','localStorage':[]}]}
        class SignedInPortal:
            async def read(self):
                return [], [], json.loads(json.dumps(refreshed))
        with tempfile.TemporaryDirectory() as folder:
            runtime = Runtime(dict(DEFAULTS), Path(folder))
            runtime.portal = SignedInPortal()
            runtime.bridge = NullBridge()
            await runtime.refresh()
            self.assertIsNone(runtime.error)
            self.assertIsNotNone(runtime.last_success)
            saved = json.loads((Path(folder) / 'storage-state.json').read_text(encoding='utf-8'))
            self.assertEqual([c['domain'] for c in saved['cookies']], ['.wise.oclc.org'])
            self.assertEqual([o['origin'] for o in saved['origins']], ['https://bibliotheek.wise.oclc.org'])

    async def test_unexpected_failure_is_logged_by_type_without_its_message(self):
        class BrokenPortal:
            async def read(self):
                raise RuntimeError('https://inloggen.kb.nl/u/login?state=secret-token')
        with tempfile.TemporaryDirectory() as folder:
            runtime = Runtime(dict(DEFAULTS), Path(folder))
            runtime.portal = BrokenPortal()
            runtime.bridge = NullBridge()
            with self.assertLogs('wise_library', level='ERROR') as logs:
                await runtime.refresh()
            output = '\n'.join(logs.output)
            self.assertIn('RuntimeError', output)
            self.assertNotIn('secret-token', output)
            self.assertNotIn('secret-token', runtime.error)

    async def test_failed_login_pauses_automatic_retries(self):
        class RejectedPortal:
            async def read(self):
                raise AuthenticationError('Sign-in rejected. Automatic retries are paused.')
        class Bridge:
            def unavailable(self): pass
        with tempfile.TemporaryDirectory() as folder:
            runtime = Runtime(dict(DEFAULTS), Path(folder))
            runtime.portal = RejectedPortal()
            runtime.bridge = Bridge()
            await runtime.refresh()
            self.assertTrue(getattr(runtime, 'auth_blocked', False))
