import tempfile
import unittest
from pathlib import Path
from wise_library.app.server import Runtime, DEFAULTS
from wise_library.app.domain import AuthenticationError

class RuntimeAuthTests(unittest.IsolatedAsyncioTestCase):
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
