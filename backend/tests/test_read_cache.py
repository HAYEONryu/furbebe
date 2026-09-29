"""Cache expiration follows the data's KST date across slow reads and New Year."""

from datetime import date, datetime
from unittest.mock import MagicMock, patch

import pytest
from fastapi import Response
from fastapi.testclient import TestClient

from backend.app.api.animals import cache
from backend.app.core.config import Settings
from backend.app.main import create_app
from backend.app.services.animals import ReadService, get_read_service
from backend.jobs.animal_sync.status_policy import KST


@pytest.mark.parametrize(
    "today,finished,expected",
    [
        (date(2026, 9, 29), datetime(2026, 9, 29, 12, tzinfo=KST), 600),
        (date(2026, 9, 29), datetime(2026, 9, 29, 23, 59, 59, tzinfo=KST), 1),
        (date(2026, 9, 29), datetime(2026, 9, 30, tzinfo=KST), 0),
        (date(2026, 9, 29), datetime(2026, 9, 30, 0, 0, 1, tzinfo=KST), 0),
        (date(2026, 12, 31), datetime(2027, 1, 1, 0, 0, 1, tzinfo=KST), 0),
        (date(2027, 1, 1), datetime(2027, 1, 1, 0, 0, 1, tzinfo=KST), 600),
    ],
)
def test_cache_ttl_is_bounded_by_the_query_date(today, finished, expected):
    with patch("backend.app.api.animals.datetime") as clock:
        clock.now.return_value = finished
        clock.combine.side_effect = datetime.combine
        response = Response()
        cache(response, 600, today=today)
    assert response.headers["cache-control"] == f"public, max-age={expected}"


@pytest.mark.parametrize("path", ["meta/filters", "stats/overview", "animals", "tags"])
@pytest.mark.parametrize("today", [date(2026, 12, 31), date(2027, 1, 1)])
def test_http_cache_uses_service_date_when_query_crosses_new_year(path, today):
    repository = MagicMock()
    queries = repository.snapshot.return_value.__enter__.return_value
    queries.filter_facets.return_value = []
    queries.overview.return_value = {
        "animals_total": 0,
        "new_today": 0,
        "with_primary_image": 0,
        "last_synced_at": None,
    }
    queries.list_animals.return_value = ([], 0)
    queries.tag_catalog.return_value = []
    service = ReadService(repository, today=today)
    app = create_app(Settings(_env_file=None, app_env="test"))
    app.dependency_overrides[get_read_service] = lambda: service
    with TestClient(app) as client, patch("backend.app.api.animals.datetime") as clock:
        clock.now.return_value = datetime(2027, 1, 1, 0, 0, 1, tzinfo=KST)
        clock.combine.side_effect = datetime.combine
        response = client.get("/api/v1/" + path)
    assert response.status_code == 200
    repository.snapshot.assert_called_once_with(today)
    expected = 0 if today.year == 2026 else 600 if path in {"meta/filters", "tags"} else 60
    assert response.headers["cache-control"] == f"public, max-age={expected}"
