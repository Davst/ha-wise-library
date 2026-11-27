import tempfile
import unittest
from pathlib import Path

from wise_library.app.covers import CoverError, CoverStore

PLACEHOLDER = b"\xff\xd8\xff" + b"generic placeholder"
REAL = b"\xff\xd8\xff" + b"a real cover"


class CoverStoreTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.requested = []
        self.tmp = tempfile.TemporaryDirectory()
        self.store = CoverStore(Path(self.tmp.name))

    def tearDown(self):
        self.tmp.cleanup()

    async def fetch(self, isbn):
        self.requested.append(isbn)
        if isbn == "9780306406157":
            return REAL
        if isbn == "9781111111113":
            raise CoverError("status 500")
        return PLACEHOLDER

    async def test_a_real_cover_is_kept_and_a_placeholder_is_not(self):
        await self.store.fetch_missing(["9780306406157", "9781234567897"], self.fetch)
        self.assertTrue(self.store.has("9780306406157"))
        self.assertFalse(self.store.has("9781234567897"))
        self.assertEqual(self.store.path("9780306406157").read_bytes(), REAL)

    async def test_covers_are_fetched_once_and_a_failed_one_is_tried_again(self):
        await self.store.fetch_missing(["9780306406157", "9781111111113"], self.fetch)
        await self.store.fetch_missing(["9780306406157", "9781111111113", "9781234567897"], self.fetch)
        self.assertEqual(self.requested.count("9780306406157"), 1)
        self.assertEqual(self.requested.count("9781111111113"), 2)
        self.assertEqual(self.requested.count("9781234567897"), 1)

    async def test_nothing_is_stored_when_the_placeholder_cannot_be_told_apart(self):
        async def broken(isbn):
            raise CoverError("offline")

        await self.store.fetch_missing(["9780306406157"], broken)
        self.assertFalse(self.store.has("9780306406157"))

    async def test_a_reply_that_is_not_an_image_is_not_kept(self):
        async def html(isbn):
            return b"<html>blocked</html>" if isbn != "9780000000002" else PLACEHOLDER

        await self.store.fetch_missing(["9780306406157"], html)
        self.assertFalse(self.store.has("9780306406157"))

    async def test_malformed_isbns_are_never_requested_or_stored(self):
        await self.store.fetch_missing(["../x", "12", ""], self.fetch)
        self.assertEqual(self.requested, [])
        self.assertIsNone(self.store.path("../x"))
