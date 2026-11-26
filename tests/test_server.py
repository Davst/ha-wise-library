import tempfile
import unittest
from pathlib import Path
from aiohttp.test_utils import TestClient, TestServer
from wise_library.app.server import create_app


class FakeRuntime:
    def __init__(self, path):
        self.data_dir = path
        self.csrf = 'test-csrf'
        self.options = {'branch_id':'2709'}
        self.last_success = None
        self.error = None
        self.snapshot = None
        self.busy = False
        self.bridge = type('Bridge', (), {'connected':False})()


class WebTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.runtime = FakeRuntime(Path(self.tmp.name))
        self.client = TestClient(TestServer(create_app(self.runtime, local=True)))
        await self.client.start_server()

    async def asyncTearDown(self):
        await self.client.close()
        self.tmp.cleanup()

    async def test_status_is_explicitly_disconnected_without_session(self):
        response = await self.client.get('/api/status')
        self.assertEqual(response.status, 200)
        result = await response.json()
        self.assertFalse(result['session_present'])
        self.assertIsNone(result['snapshot'])

    async def test_session_upload_requires_csrf(self):
        response = await self.client.post('/api/session', json={'cookies':[], 'origins':[]})
        self.assertEqual(response.status, 403)

    async def test_unrelated_session_is_rejected_without_writing_it(self):
        response = await self.client.post('/api/session', json={'cookies':[{'domain':'google.com'}], 'origins':[]}, headers={'X-CSRF-Token':'test-csrf'})
        self.assertEqual(response.status, 400)
        self.assertFalse((self.runtime.data_dir / 'storage-state.json').exists())

    async def test_ingress_mode_rejects_direct_clients(self):
        other = TestClient(TestServer(create_app(self.runtime, local=False)))
        await other.start_server()
        try:
            response = await other.get('/')
            self.assertEqual(response.status, 403)
        finally:
            await other.close()
