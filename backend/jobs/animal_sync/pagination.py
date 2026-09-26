"""Complete pagination with conservative completeness checks and bounded failure."""

from dataclasses import dataclass, field
from time import perf_counter

from .client import ApiFailure
from .parsing import identifier


@dataclass
class PaginationProgress:
    page_no: int = 0
    total_count: int | None = None
    fetched_count: int = 0
    unique_count: int = 0
    page_count: int = 0
    failed_pages: list[int] = field(default_factory=list)
    fetch_seconds: float = 0


def iter_pages(
    client,
    progress: PaginationProgress,
    *,
    page_size=1000,
    max_pages=10000,
    max_animals=None,
    filters=None,
):
    seen = set()
    effective_size = None
    for number in range(1, max_pages + 1):
        progress.page_no = number
        started = perf_counter()
        try:
            page = client.fetch(number, page_size, filters=filters)
        except ApiFailure:
            progress.failed_pages.append(number)
            raise
        finally:
            progress.fetch_seconds += perf_counter() - started
        progress.page_count += 1
        progress.fetched_count += len(page.items)
        seen.update(key for row in page.items if (key := identifier(row)) is not None)
        progress.unique_count = len(seen)
        try:
            if page.number != number or page.total <= 0:
                raise ApiFailure("ABNORMAL_TOTAL_OR_PAGE")
            if max_animals is not None and page.total > max_animals:
                raise ApiFailure("SOURCE_TOTAL_EXCEEDS_LIMIT")
            if progress.total_count is None:
                progress.total_count = page.total
                effective_size = page.page_size or len(page.items)
            if page.total != progress.total_count:
                raise ApiFailure("TOTAL_COUNT_CHANGED")
            if not effective_size or page.page_size not in (None, effective_size):
                raise ApiFailure("PAGE_SIZE_CHANGED")
            before = progress.fetched_count - len(page.items)
            expected = min(effective_size, max(0, page.total - before))
            if len(page.items) != expected:
                raise ApiFailure("INCOMPLETE_OR_EXCESS_PAGE")
            if not page.items:
                if progress.unique_count != page.total:
                    raise ApiFailure("UNIQUE_COUNT_MISMATCH")
                yield page
                return
        except ApiFailure:
            progress.failed_pages.append(number)
            raise
        yield page
    progress.failed_pages.append(progress.page_no + 1)
    raise ApiFailure("PAGE_LIMIT_REACHED")
