"""Keep each book's cover in the app's own data folder, fetched once from the library by ISBN."""

import hashlib
import logging
import re
from pathlib import Path

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
