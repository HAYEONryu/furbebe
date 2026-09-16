"""Local redacted page capture and exact replay, independent of profiling reports."""

import hashlib
import json
from datetime import datetime
from pathlib import Path

from .client import AnimalApiClient, ApiFailure
from .pagination import PaginationProgress, iter_pages


def capture_digest(path: Path) -> str:
    with path.open("rb") as handle:
        return hashlib.file_digest(handle, "sha256").hexdigest()


class RecordingClient:
    def __init__(self, client, path: Path):
        self.client = client
        self.path = path
        self.handle = path.open("x", encoding="utf-8")

    @property
    def attempts(self):
        return self.client.attempts

    @property
    def retries(self):
        return self.client.retries

    def fetch(self, page, size, *, filters=None):
        result = self.client.fetch(page, size, filters=filters)
        self.handle.write(
            json.dumps(
                {
                    "page_no": page,
                    "page_size": size,
                    "filters": filters or {},
                    "response": result.envelope,
                },
                ensure_ascii=False,
            )
            + "\n"
        )
        self.handle.flush()
        return result

    def close(self):
        if self.handle.closed:
            return
        self.handle.close()
        self.path.with_suffix(".sha256").write_text(
            capture_digest(self.path) + "\n", encoding="ascii"
        )


class ReplayClient:
    """Requires our complete, hash-verified capture including its empty terminal page."""

    attempts = 0
    retries = 0

    def __init__(self, path: Path, *, max_pages=10000):
        self.handle = self.parser = None
        try:
            expected = path.with_suffix(".sha256").read_text(encoding="ascii").strip()
            if capture_digest(path) != expected:
                raise ApiFailure("REPLAY_HASH_MISMATCH")
            self.handle = path.open(encoding="utf-8")
            first = json.loads(self.handle.readline())
            self.handle.seek(0)
            if not isinstance(first, dict):
                raise ApiFailure("INVALID_REPLAY_CAPTURE")
            self.filters = first["filters"]
            self.page_size = first["page_size"]
            if (
                type(self.page_size) is not int
                or not 1 <= self.page_size <= 1000
                or not isinstance(self.filters, dict)
                or set(self.filters) not in (set(), {"bgnde", "endde"})
            ):
                raise ApiFailure("INVALID_REPLAY_REQUEST")
            if self.filters:
                dates = []
                for name in ("bgnde", "endde"):
                    value = self.filters[name]
                    if (
                        not isinstance(value, str)
                        or len(value) != 8
                        or not value.isascii()
                        or not value.isdecimal()
                    ):
                        raise ApiFailure("INVALID_REPLAY_REQUEST")
                    dates.append(datetime.strptime(value, "%Y%m%d"))
                if dates[0] > dates[1]:
                    raise ApiFailure("INVALID_REPLAY_REQUEST")
            self.parser = AnimalApiClient("", interval=0)
            # Verify completeness before any database writes. The replay itself stays streaming.
            for _ in iter_pages(
                self,
                PaginationProgress(),
                page_size=self.page_size,
                max_pages=max_pages,
                filters=self.filters,
            ):
                pass
            if self.handle.read(1):
                raise ApiFailure("REPLAY_TRAILING_DATA")
            self.handle.seek(0)
        except ApiFailure:
            self.close()
            raise
        except (OSError, ValueError, KeyError):
            self.close()
            raise ApiFailure("INVALID_REPLAY_CAPTURE") from None

    def fetch(self, page, size, *, filters=None):
        try:
            record = json.loads(self.handle.readline())
            if not isinstance(record, dict):
                raise ApiFailure("INVALID_REPLAY_CAPTURE")
            if (
                type(record["page_no"]) is not int
                or type(record["page_size"]) is not int
                or record["page_no"] != page
                or record["page_size"] != size
                or record["filters"] != (filters or {})
            ):
                raise ApiFailure("REPLAY_REQUEST_MISMATCH")
            return self.parser._parse(record["response"], page)
        except (ValueError, KeyError):
            raise ApiFailure("REPLAY_INCOMPLETE") from None

    def close(self):
        if self.handle is not None:
            self.handle.close()
        if self.parser is not None:
            self.parser.http.close()
