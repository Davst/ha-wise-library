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

class UpgradeTests(unittest.IsolatedAsyncioTestCase):
    async def test_existing_cover_is_upgraded_only_once_and_only_if_larger(self):
        import io

        from PIL import Image

        def image(size):
            output = io.BytesIO()
            Image.new('RGB', size, 'red').save(output, format='PNG')
            return output.getvalue()

        with tempfile.TemporaryDirectory() as folder:
            store = CoverStore(folder)
            isbn = '9780306406157'
            store.path(isbn).write_bytes(image((100, 150)))
            calls = []

            async def secondary(value):
                calls.append(value)
                return image((600, 900))

            with self.assertLogs("wise_library", level="INFO") as logs:
                await store.upgrade([isbn], secondary)
            self.assertIn("100x150 -> 600x900", " ".join(logs.output))
            with Image.open(store.path(isbn)) as saved:
                self.assertEqual(saved.size, (600, 900))
            await store.upgrade([isbn], secondary)
            self.assertEqual(calls, [isbn])

    async def test_secondary_failure_preserves_cover_and_can_retry(self):
        with tempfile.TemporaryDirectory() as folder:
            store = CoverStore(folder)
            isbn = '9780306406157'
            store.path(isbn).write_bytes(REAL)

            async def broken(value):
                raise CoverError('offline')

            await store.upgrade([isbn], broken)
            self.assertEqual(store.path(isbn).read_bytes(), REAL)
            self.assertFalse((Path(folder) / f'{isbn}.openlibrary').exists())

    async def test_smaller_missing_and_invalid_secondary_covers_keep_original(self):
        import io

        from PIL import Image

        output = io.BytesIO()
        Image.new('RGB', (40, 60)).save(output, format='PNG')
        with tempfile.TemporaryDirectory() as folder:
            store = CoverStore(folder)
            isbn = '9780306406157'
            original = io.BytesIO()
            Image.new('RGB', (200, 300)).save(original, format='PNG')
            for reply in [output.getvalue(), None, b'not an image']:
                store.path(isbn).write_bytes(original.getvalue())
                marker = Path(folder) / f'{isbn}.openlibrary'
                marker.unlink(missing_ok=True)
                async def secondary(value, result=reply):
                    return result
                await store.upgrade([isbn], secondary)
                self.assertEqual(store.path(isbn).read_bytes(), original.getvalue())
                self.assertEqual(marker.exists(), reply != b'not an image')
