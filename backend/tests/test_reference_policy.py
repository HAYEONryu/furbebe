from datetime import date, datetime, timezone

from backend.jobs.animal_sync.client import Page
from backend.jobs.animal_sync.reference_cache import ReferenceCache
from backend.jobs.animal_sync.status_policy import display_status


def test_protecting_status_becomes_adoptable_on_day_ten():
    row = {"processState": "보호중", "noticeSdt": "20260904"}

    result = display_status(row, today=date(2026, 9, 14))

    assert result["display_state"] == "입양 가능"
    assert result["elapsed_days"] == 10


def test_protecting_status_stays_protecting_before_day_ten():
    row = {"processState": "보호중", "noticeSdt": "20260905"}

    result = display_status(row, today=date(2026, 9, 14))

    assert result["display_state"] == "보호중"
    assert result["elapsed_days"] == 9


def test_reference_catalog_is_reused_for_known_codes(tmp_path):
    calls = []

    class Client:
        def fetch_reference(self, resource, page, size, *, filters):
            calls.append((resource, page, size, filters))
            return Page(
                number=page,
                total=1,
                items=[{"kindCd": "0001", "kindNm": "믹스견"}],
                shape="object",
                header={"resultCode": "00"},
                envelope={},
                page_size=size,
            )

    cache = ReferenceCache(
        tmp_path,
        Client(),
        clock=lambda: datetime(2026, 9, 14, tzinfo=timezone.utc),
    )
    filters = {"up_kind_cd": "417000"}

    cache.ensure("kind", filters, expected={"0001"})
    cache.ensure("kind", filters, expected={"0001"})

    assert len(calls) == 1


def test_missing_reference_is_not_refetched_within_cache_window(tmp_path):
    calls = []

    class Client:
        def fetch_reference(self, resource, page, size, *, filters):
            calls.append((resource, page, size, filters))
            return Page(
                number=page,
                total=1,
                items=[{"kindCd": "0001", "kindNm": "믹스견"}],
                shape="object",
                header={"resultCode": "00"},
                envelope={},
                page_size=size,
            )

    now = datetime(2026, 9, 14, tzinfo=timezone.utc)
    filters = {"up_kind_cd": "417000"}
    first = ReferenceCache(tmp_path, Client(), clock=lambda: now)
    first.ensure("kind", filters, expected={"missing"})

    second = ReferenceCache(tmp_path, Client(), clock=lambda: now)
    second.ensure("kind", filters, expected={"missing"})

    assert second.stats["cache_hits"] == 1
