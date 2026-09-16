"""HTTP contracts and errors without a database or external network."""

from datetime import date
from unittest.mock import MagicMock
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.exc import OperationalError

from backend.app.core.config import Settings
from backend.app.main import create_app
from backend.app.repositories.animals import ReadRepository
from backend.app.schemas.animals import AnimalFilters
from backend.app.services.animals import ReadService, get_read_service
from backend.app.services.errors import AnimalNotFound, TagNotFound


@pytest.fixture
def client():
    with TestClient(create_app(Settings(_env_file=None, app_env="test"))) as result:
        yield result


@pytest.mark.parametrize(
    "query",
    [
        {"page": 0},
        {"page": -1},
        {"page_size": 0},
        {"page_size": 61},
        {"page_size": "bad"},
        {"sex": "M"},
        {"neutered": "U"},
        {"size_group": "huge"},
        {"age_group": "old"},
        {"tag_match": "every"},
        {"sort": "id desc; DROP TABLE animals"},
        {"q": "x" * 51},
        {"region": "서울"},
        {"size": "small"},
        {"tag": " "},
        {"tag": ""},
        {"breed": "\x00"},
    ],
)
def test_invalid_queries_use_safe_422_before_database_access(client, query):
    response = client.get("/api/v1/animals", params=query)
    assert response.status_code == 422
    error = response.json()["error"]
    assert error["code"] == "VALIDATION_ERROR" and error["details"]
    assert error["request_id"] == response.headers["x-request-id"]
    assert "DROP TABLE" not in response.text


@pytest.mark.parametrize(
    "path",
    [
        "/api/v1/animals",
        "/api/v1/tags",
        "/api/v1/meta/filters",
        "/api/v1/stats/overview",
        "/api/v1/animals/" + str(UUID(int=1)),
        "/api/v1/animals/" + str(UUID(int=1)) + "/similar",
    ],
)
def test_missing_database_503_request_id_cors_and_no_cache(client, path):
    request_id = str(uuid4())
    response = client.get(
        path, headers={"X-Request-ID": request_id, "Origin": "http://localhost:5173"}
    )
    assert response.status_code == 503
    assert response.json()["error"]["code"] == "SERVICE_UNAVAILABLE"
    assert response.headers["x-request-id"] == request_id
    assert response.headers["access-control-allow-origin"] == "http://localhost:5173"
    assert "cache-control" not in response.headers


@pytest.mark.parametrize(
    "path",
    [
        "/api/v1/animals/not-a-uuid",
        "/api/v1/animals/not-a-uuid/similar",
        "/api/v1/animals/" + str(UUID(int=1)) + "/similar?limit=0",
        "/api/v1/animals/" + str(UUID(int=1)) + "/similar?limit=13",
        "/api/v1/tags?type=invalid",
        "/api/v1/tags?active_only=invalid",
    ],
)
def test_path_and_discovery_validation(client, path):
    assert client.get(path).status_code == 422


@pytest.mark.parametrize(
    "error,code", [(AnimalNotFound, "ANIMAL_NOT_FOUND"), (TagNotFound, "TAG_NOT_FOUND")]
)
def test_domain_errors_have_fixed_envelope(client, error, code):
    service = MagicMock()
    service.animals.side_effect = error()
    client.app.dependency_overrides[get_read_service] = lambda: service
    response = client.get("/api/v1/animals")
    assert response.status_code == 404
    assert response.json()["error"]["code"] == code


def test_repeated_tag_query_is_a_get_query_and_is_deduplicated(client):
    service = MagicMock()
    service.animals.side_effect = AnimalNotFound()
    client.app.dependency_overrides[get_read_service] = lambda: service
    client.get("/api/v1/animals?tag=white&tag=puppy&tag=white&tag_match=all")
    filters = service.animals.call_args.args[0]
    assert filters.tag == ["white", "puppy"] and filters.tag_match == "all"
    spec = client.app.openapi()["paths"]["/api/v1/animals"]["get"]
    assert "requestBody" not in spec
    parameters = {p["name"]: p for p in spec["parameters"]}
    assert parameters["tag"]["schema"]["type"] == "array"
    assert "region" not in parameters and "size" not in parameters
    assert parameters["page_size"]["schema"]["maximum"] == 60
    assert spec["responses"]["422"]["content"]["application/json; charset=utf-8"]["schema"][
        "$ref"
    ].endswith("ApiErrorResponse")


def test_database_exception_details_are_never_public(client, monkeypatch, caplog):
    def fail(*args):
        raise OperationalError("SECRET SQL", {"private": "password"}, Exception("private-host"))

    monkeypatch.setattr(ReadRepository, "snapshot", fail)
    response = client.get("/api/v1/animals")
    assert response.status_code == 503
    for secret in ("SECRET SQL", "password", "private-host"):
        assert secret not in response.text + caplog.text


def test_unexpected_service_exception_uses_safe_500(client, caplog):
    service = MagicMock()
    service.animals.side_effect = RuntimeError("private-host password")
    client.app.dependency_overrides[get_read_service] = lambda: service
    response = client.get("/api/v1/animals")
    assert response.status_code == 500 and response.json()["error"]["code"] == "INTERNAL_ERROR"
    assert "private-host" not in response.text + caplog.text


def test_service_pagination_empty_contract_with_mock_repository():
    repository = MagicMock()
    repository.snapshot.return_value.__enter__.return_value.list_animals.return_value = ([], 0)
    response = ReadService(repository, today=date(2026, 9, 16)).animals(AnimalFilters())
    assert response.model_dump()["pagination"] == {
        "page": 1,
        "page_size": 24,
        "total": 0,
        "total_pages": 0,
        "has_next": False,
        "has_previous": False,
    }
