import asyncio
import tempfile
import unittest
from pathlib import Path

from aiohttp.test_utils import TestClient, TestServer

from wise_library.app.covers import CoverStore
from wise_library.app.server import create_app


class FakeRuntime:
    def __init__(self, path):
        self.data_dir = path
        self.csrf = "test-csrf"
        self.options = {"branch_id": "2709"}
        self.last_success = None
        self.error = None
        self.snapshot = None
        self.busy = False
        self.renewal = None
        self.renewed = []
        self.tasks = set()
        self.covers = CoverStore(path / "covers")
        self.last_requested = 0
        self.wake = asyncio.Event()
        self.auth_blocked = False
        self.bridge = type("Bridge", (), {"connected": False})()

    async def renew(self, ids):
        self.renewed.append(ids)
        self.busy = False


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
        response = await self.client.get("/api/status")
        self.assertEqual(response.status, 200)
        result = await response.json()
        self.assertFalse(result["session_present"])
        self.assertIsNone(result["snapshot"])

    async def test_status_reports_credentials_without_exposing_them(self):
        self.runtime.options.update({"library_username": "private-reader", "library_password": "private-password"})
        response = await self.client.get("/api/status")
        text = await response.text()
        self.assertNotIn("private-reader", text)
        self.assertNotIn("private-password", text)
        self.assertTrue((await response.json()).get("credentials_configured", False))

    async def test_manual_retry_works_without_session_and_clears_auth_pause(self):
        self.runtime.options.update({"library_username": "private-reader", "library_password": "private-password"})
        self.runtime.auth_blocked = True
        response = await self.client.post("/api/refresh", json={}, headers={"X-CSRF-Token": "test-csrf"})
        self.assertEqual(response.status, 200)
        self.assertFalse(self.runtime.auth_blocked)
        self.assertTrue(self.runtime.wake.is_set())

    async def test_session_upload_requires_csrf(self):
        response = await self.client.post("/api/session", json={"cookies": [], "origins": []})
        self.assertEqual(response.status, 403)

    async def test_unrelated_session_is_rejected_without_writing_it(self):
        response = await self.client.post(
            "/api/session",
            json={"cookies": [{"domain": "google.com"}], "origins": []},
            headers={"X-CSRF-Token": "test-csrf"},
        )
        self.assertEqual(response.status, 400)
        self.assertFalse((self.runtime.data_dir / "storage-state.json").exists())

    async def test_cover_is_served_from_the_apps_own_store_and_cached(self):
        isbn = "9780306406157"
        (Path(self.tmp.name) / "covers" / f"{isbn}.img").write_bytes(b"\xff\xd8\xff" + b"jpeg bytes")
        response = await self.client.get(f"/api/cover/{isbn}")
        self.assertEqual(response.status, 200)
        self.assertEqual(response.content_type, "image/jpeg")
        self.assertIn("max-age", response.headers["Cache-Control"])
        self.assertEqual((await self.client.get("/api/cover/9780000000002")).status, 404)
        self.assertEqual((await self.client.get("/api/cover/..%2Fstorage-state")).status, 404)

    async def test_renew_needs_csrf_and_only_renews_loans_the_library_offers(self):
        self.runtime.snapshot = {
            "loans": [
                {"id": "A1", "renew_id": "7000001", "title": "A", "renew_until": "2026-12-28"},
                {"id": "B1", "renew_id": "14642373", "title": "B", "renew_until": None},
            ]
        }
        headers = {"X-CSRF-Token": "test-csrf"}
        self.assertEqual((await self.client.post("/api/renew", json={"ids": ["A1"]})).status, 403)
        self.assertEqual((await self.client.post("/api/renew", json={"ids": ["B1"]}, headers=headers)).status, 409)
        self.assertEqual((await self.client.post("/api/renew", json={"ids": ["999"]}, headers=headers)).status, 409)
        self.assertEqual((await self.client.post("/api/renew", json={"ids": []}, headers=headers)).status, 400)
        self.assertEqual((await self.client.post("/api/renew", json={"nope": 1}, headers=headers)).status, 400)
        self.assertEqual(self.runtime.renewed, [])
        response = await self.client.post("/api/renew", json={"ids": ["A1"]}, headers=headers)
        self.assertEqual(response.status, 202)
        await asyncio.sleep(0.05)
        self.assertEqual(self.runtime.renewed, [["7000001"]])  # the portal's own loan number, not the app's id

    async def test_renew_is_refused_while_a_refresh_is_running(self):
        self.runtime.snapshot = {"loans": [{"id": "1", "renew_id": "9", "title": "A", "renew_until": "2026-12-28"}]}
        self.runtime.busy = True
        response = await self.client.post("/api/renew", json={"ids": ["1"]}, headers={"X-CSRF-Token": "test-csrf"})
        self.assertEqual(response.status, 409)
        self.assertEqual(self.runtime.renewed, [])

    async def test_ingress_mode_rejects_direct_clients(self):
        other = TestClient(TestServer(create_app(self.runtime, local=False)))
        await other.start_server()
        try:
            response = await other.get("/")
            self.assertEqual(response.status, 403)
        finally:
            await other.close()
