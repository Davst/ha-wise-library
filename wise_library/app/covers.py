"""Cache library covers and optional higher-resolution Open Library images by exact ISBN."""

import hashlib
import io
import logging
import re
import warnings
from pathlib import Path

from PIL import Image

log = logging.getLogger("wise_library")
# An ISBN no book has: the library answers with its generic placeholder, which must not pass for a cover.
UNKNOWN_ISBN = "9780000000002"
ISBN = re.compile(r"[0-9]{9}[0-9X]|[0-9]{13}")
MAGIC = {b"\xff\xd8\xff": "image/jpeg", b"\x89PNG": "image/png", b"GIF8": "image/gif"}


class CoverError(Exception):
    """A cover could not be fetched; it is tried again at the next refresh."""


def image_type(data):
    return next((kind for magic, kind in MAGIC.items() if data.startswith(magic)), None)


class CoverStore:
    def __init__(self, folder):
        self.folder = Path(folder)
        self.folder.mkdir(parents=True, exist_ok=True)

    def path(self, isbn):
        return self.folder / f"{isbn}.img" if ISBN.fullmatch(isbn) else None

    def has(self, isbn):
        path = self.path(isbn)
        return bool(path and path.exists())

    def _none(self, isbn):
        return self.folder / f"{isbn}.none"

    async def fetch_missing(self, isbns, fetch):
        """Fetch covers not stored yet with `fetch(isbn)`, which returns the image bytes or raises CoverError."""
        wanted = sorted(
            {isbn for isbn in isbns if self.path(isbn) and not self.has(isbn) and not self._none(isbn).exists()}
        )
        if not wanted:
            return
        try:
            placeholder = hashlib.sha256(await fetch(UNKNOWN_ISBN)).digest()
        except CoverError as error:
            log.warning("Covers skipped; the library's placeholder could not be fetched: %s", error)
            return
        for isbn in wanted:
            try:
                data = await fetch(isbn)
            except CoverError as error:
                log.warning("Cover %s not fetched: %s", isbn, error)
                continue
            if hashlib.sha256(data).digest() == placeholder or not image_type(data):
                self._none(isbn).write_bytes(b"")
            else:
                self.path(isbn).write_bytes(data)

    async def upgrade(self, isbns, fetch):
        """Check each exact ISBN once; transient failures remain retryable."""
        for isbn in sorted(set(isbns)):
            if not self.path(isbn):
                continue
            checked = self.folder / f"{isbn}.openlibrary"
            if checked.exists():
                continue
            try:
                data = await fetch(isbn)
                if data is not None:
                    size = dimensions(data)
                    if size == (0, 0):
                        raise CoverError("invalid cover image")
                    current = dimensions(self.path(isbn).read_bytes()) if self.has(isbn) else (0, 0)
                    if size[0] > current[0] and size[1] > current[1]:
                        temporary = self.folder / f"{isbn}.tmp"
                        temporary.write_bytes(data)
                        temporary.replace(self.path(isbn))
                checked.touch()
            except CoverError as error:
                log.warning("Cover upgrade %s deferred: %s", isbn, error)


def dimensions(data):
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            with Image.open(io.BytesIO(data)) as image:
                image.verify()
                return image.size
    except (OSError, ValueError, Image.DecompressionBombError, Image.DecompressionBombWarning):
        return (0, 0)


async def openlibrary_cover(isbn):
    """Public ISBN lookup with no library credentials, bounded time and response size."""

    from aiohttp import ClientError, ClientSession, ClientTimeout

    try:
        async with ClientSession(timeout=ClientTimeout(total=12)) as session, session.get(
            f"https://covers.openlibrary.org/b/isbn/{isbn}-L.jpg?default=false",
            headers={"User-Agent": "WiseLibrary/0.2 (personal Home Assistant cover lookup)"},
        ) as response:
            if response.status == 404:
                return None
            if response.status != 200:
                raise CoverError(f"Open Library status {response.status}")
            data = bytearray()
            async for chunk in response.content.iter_chunked(65536):
                data.extend(chunk)
                if len(data) > 8 * 1024 * 1024:
                    raise CoverError("cover exceeds 8 MB")
            return bytes(data)
    except (TimeoutError, ClientError):
        raise CoverError("Open Library unavailable") from None
