"""Contract and SQL behavior against an isolated local PostgreSQL schema."""

from datetime import date, timedelta
from types import SimpleNamespace
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import event, insert, select, text, update
from sqlalchemy.exc import DBAPIError
from sqlalchemy.schema import CreateSchema, DropSchema

from backend.app.db.models import Animal, AnimalImage, Tag
from backend.app.db.session import create_database_engine, get_database
from backend.app.main import create_app
from backend.app.repositories.animals import ReadRepository
from backend.app.services.animals import read_today
from backend.jobs.animal_sync.retag import retag
from backend.tests.read_fixtures import NOW, SENTINEL, TODAY, seed

pytestmark = pytest.mark.postgres


@pytest.fixture
def env(postgres_settings):
    parent = create_database_engine(postgres_settings)
    schema = "phase5_test_" + uuid4().hex
    engine = parent.execution_options(schema_translate_map={None: schema})
    with parent.begin() as conn:
        conn.execute(CreateSchema(schema))
    try:
        from backend.app.db.models import Base

        Base.metadata.create_all(engine)
        with engine.begin() as conn:
            rows = seed(conn)
        app = create_app(postgres_settings)
        app.dependency_overrides[get_database] = lambda: SimpleNamespace(engine=engine)
        app.dependency_overrides[read_today] = lambda: TODAY
        with TestClient(app) as client:
            yield SimpleNamespace(client=client, engine=engine, rows=rows, app=app)
    finally:
        try:
            assert schema.startswith("phase5_test_") and len(schema) == 44
            with parent.begin() as conn:
                conn.execute(DropSchema(schema, cascade=True))
        finally:
            parent.dispose()


def listing(env, **params):
    response = env.client.get("/api/v1/animals", params=params)
    assert response.status_code == 200, response.text
    return response.json()


def detail(env, number):
    response = env.client.get("/api/v1/animals/" + str(UUID(int=number)))
    assert response.status_code == 200, response.text
    return response.json()


def test_v3_traits_v2_vibes_and_safety_survive_database_and_api(env):
    with env.engine.begin() as connection:
        connection.execute(update(Animal).where(Animal.id == UUID(int=1)).values(
            special_mark="온순. 사람을 좋아함. 방어적 입질.",
            color_text="흰색&회색", weight_kg=5, health_text="건강상태 양호",
        ))
    retag(env.engine)
    data = detail(env, 1)
    assert {tag["label"] for tag in data["tags"] if tag["category"]} == {
        "순딩이", "사람좋아", "품에쏙",
    }
    assert data["safety_badges"] == [{
        "key": "bite_caution", "label": "입질주의", "evidence": "special_mark: 방어적 입질",
    }]
    assert data["descriptions"]["health"] == "건강상태 양호"
    items = listing(env, tag="people_friendly")["items"]
    assert len(items) == 1
    assert items[0]["tags"] == data["tags"]
    assert items[0]["safety_badges"] == data["safety_badges"]
    catalog = env.client.get("/api/v1/tags").json()["items"]
    assert any(tag["key"] == "people_friendly" and tag["category"] == "relationship" for tag in catalog)
    assert any(tag["key"] == "puppy" for tag in catalog)


def test_defaults_exact_summary_contract_and_nulls(env):
    data = listing(env)
    assert len(data["items"]) == 24
    assert data["pagination"] == {
        "page": 1,
        "page_size": 24,
        "total": 40,
        "total_pages": 2,
        "has_next": True,
        "has_previous": False,
    }
    assert set(data["items"][0]) == {
        "id",
        "notice_no",
        "breed",
        "breed_full",
        "sex",
        "birth_year",
        "age_text",
        "age_group",
        "weight_kg",
        "weight_text",
        "size_group",
        "color_text",
        "process_state",
        "found_date",
        "notice_end",
        "region",
        "primary_image",
        "tags",
        "safety_badges",
    }
    first = detail(env, 1)
    assert first["animal"]["weight_kg"] == 0 and first["animal"]["size_group"] == "tiny"
    nulls = detail(env, 8)
    for name in ("weight_kg", "weight_text", "birth_year", "age_text", "sex", "neutered", "breed"):
        assert nulls["animal"][name] is None
    assert nulls["animal"]["size_group"] == nulls["animal"]["age_group"] == "unknown"
    assert nulls["shelter"] is None and nulls["images"] == []
    assert nulls["found"]["region"] == {
        "sido": None,
        "sigungu": None,
        "display": "미확인 지역 원문",
    }


@pytest.mark.parametrize(
    "field,value,total",
    [
        ("sido", "6110000", 19),
        ("sigungu", "3220000", 19),
        ("sido", "6410000", 19),
        ("sido", "5690000", 1),
        ("breed", "말티즈", 19),
        ("sex", "female", 20),
        ("sex", "male", 19),
        ("neutered", "yes", 14),
        ("neutered", "unknown", 25),
        ("neutered", "no", 0),
        ("size_group", "tiny", 10),
        ("size_group", "small", 10),
        ("size_group", "medium", 10),
        ("size_group", "large", 5),
        ("size_group", "unknown", 5),
        ("age_group", "puppy", 10),
        ("age_group", "young", 10),
        ("age_group", "adult", 10),
        ("age_group", "senior", 5),
        ("age_group", "unknown", 5),
        ("process_state", "입양 가능", 19),
        ("process_state", "보호중", 19),
        ("process_state", "종료(반환)", 1),
        ("process_state", "신규 원문 상태", 1),
        ("q", "%", 1),
        ("q", "_", 20),
        ("q", "수원", 19),
        ("q", "보호소", 39),
        ("q", "' OR 1=1 --", 0),
        ("q", "일치없음", 0),
    ],
)
def test_every_filter_uses_actual_values_and_boundary_policy(env, field, value, total):
    data = listing(env, **{field: value, "page_size": 60})
    assert data["pagination"]["total"] == len(data["items"]) == total
    if (
        field in ("sex", "neutered", "size_group", "age_group", "process_state", "breed")
        and field != "neutered"
    ):
        assert all(row[field] == value for row in data["items"])


def test_region_parent_child_combination_and_meta_round_trip(env):
    assert listing(env, sido="6410000", sigungu="3220000")["pagination"]["total"] == 0
    response = env.client.get("/api/v1/meta/filters")
    assert response.status_code == 200, response.text
    for region in response.json()["regions"]:
        assert listing(env, sido=region["sido"])["items"]
        for child in region["sigungu"]:
            assert listing(env, sido=region["sido"], sigungu=child)["items"]


@pytest.mark.parametrize("match,total", [("any", 40), ("all", 2)])
def test_repeated_tags_any_all_and_no_duplicate_animals(env, match, total):
    response = env.client.get(
        "/api/v1/animals",
        params=[("tag", "white"), ("tag", "puppy"), ("tag_match", match), ("page_size", "60")],
    )
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["pagination"]["total"] == len(data["items"]) == total
    assert len({row["id"] for row in data["items"]}) == total
    assert data["applied_filters"]["tags"] == ["white", "puppy"]


def test_inactive_missing_and_duplicate_tags(env):
    assert listing(env, tag="inactive")["items"] == []
    response = env.client.get("/api/v1/animals?tag=unregistered")
    assert response.status_code == 404 and response.json()["error"]["code"] == "TAG_NOT_FOUND"
    response = env.client.get("/api/v1/animals?tag=white&tag=white&tag_match=all")
    assert response.json()["pagination"]["total"] == 40
    tags = detail(env, 1)["tags"]
    assert len([tag for tag in tags if tag["key"] == "white"]) == 1
    assert next(tag for tag in tags if tag["key"] == "white")["evidence"] == "최신 수동 근거"
    assert not any(tag["key"] == "inactive" for tag in tags)


@pytest.mark.parametrize(
    "sort,field,descending",
    [
        ("recent", "found_date", True),
        ("notice_end", "notice_end", False),
        ("weight_asc", "weight_kg", False),
        ("weight_desc", "weight_kg", True),
        ("age_youngest", "birth_year", True),
        ("age_oldest", "birth_year", False),
    ],
)
def test_all_sort_values_nulls_last_and_stable_pagination(env, sort, field, descending):
    def key(row):
        value = row[field]
        if isinstance(value, date):
            value = value.toordinal()
        order_value = 0 if value is None else -value if descending else value
        stamp = row["source_updated_at"]
        return (
            value is None,
            order_value,
            stamp is None,
            -stamp.timestamp() if stamp else 0,
            row["id"].int,
        )

    expected = [str(row["id"]) for row in sorted(env.rows, key=key)]
    first = listing(env, sort=sort, page=1, page_size=24)
    second = listing(env, sort=sort, page=2, page_size=24)
    assert [row["id"] for row in first["items"] + second["items"]] == expected
    assert second["pagination"]["has_previous"] and not second["pagination"]["has_next"]
    beyond = listing(env, page=10**30, page_size=24)
    assert beyond["items"] == [] and beyond["pagination"]["total"] == 40


def test_detail_shape_promotion_and_only_source_descriptions(env):
    data = detail(env, 1)
    assert set(data) == {
        "id",
        "source",
        "notice",
        "animal",
        "found",
        "images",
        "tags",
        "safety_badges",
        "descriptions",
        "shelter",
        "adoption_promotion",
        "first_seen_at",
        "last_seen_at",
    }
    assert data["descriptions"] == {
        "special_mark": None,
        "social": "관찰 원문",
        "health": None,
        "etc": None,
        "vaccination": None,
        "health_check": None,
    }
    assert [image["order"] for image in data["images"]] == [1, 2]
    assert data["adoption_promotion"] == {
        "title": "합성 입양 안내",
        "start_date": "2026-09-10",
        "end_date": None,
        "condition_text": None,
        "description": None,
        "image_url": "https://example.invalid/adoption.jpg",
    }
    assert detail(env, 2)["adoption_promotion"] is None
    for path in (
        "/api/v1/animals",
        "/api/v1/animals/" + str(UUID(int=1)),
        "/api/v1/animals/" + str(UUID(int=1)) + "/similar",
    ):
        response = env.client.get(path)
        assert response.status_code == 200, response.text
        assert (
            SENTINEL not in response.text
            and "raw_payload" not in response.text
            and "is_favorite" not in response.text
        )


def test_detail_and_similar_not_found(env):
    for suffix in ("", "/similar"):
        response = env.client.get("/api/v1/animals/" + str(UUID(int=99999)) + suffix)
        assert response.status_code == 404
        assert response.json()["error"]["code"] == "ANIMAL_NOT_FOUND"


def test_similar_score_order_limits_and_exclusion(env):
    response = env.client.get("/api/v1/animals/" + str(UUID(int=1)) + "/similar")
    assert response.status_code == 200, response.text
    data = response.json()
    assert data["source_animal_id"] == str(UUID(int=1))
    assert [row["id"] for row in data["items"]] == [str(UUID(int=i)) for i in (9, 17, 25, 33)]
    assert all("score" not in row for row in data["items"])
    for count in (1, 12):
        items = env.client.get(
            "/api/v1/animals/" + str(UUID(int=1)) + "/similar", params={"limit": count}
        ).json()["items"]
        assert len(items) == count and all(row["id"] != str(UUID(int=1)) for row in items)


def test_tags_are_database_catalog_and_type_filter(env):
    assert len(env.client.get("/api/v1/tags").json()["items"]) == 3
    assert len(env.client.get("/api/v1/tags?active_only=false").json()["items"]) == 4
    assert {row["key"] for row in env.client.get("/api/v1/tags?type=trait").json()["items"]} == {
        "manual"
    }


def test_meta_and_stats_counts_kst_boundary_and_successful_sync(env):
    response = env.client.get("/api/v1/meta/filters")
    assert response.status_code == 200, response.text
    meta = response.json()
    assert meta["breeds"] == [
        {"value": "말티즈", "count": 19},
        {"value": "믹스견", "count": 19},
        {"value": "100% 친구", "count": 1},
    ]
    assert {x["value"]: x["count"] for x in meta["process_states"]} == {
        "입양 가능": 19,
        "보호중": 19,
        "종료(반환)": 1,
        "신규 원문 상태": 1,
    }
    assert {x["value"] for x in meta["sexes"]} == {"male", "female"}
    response = env.client.get("/api/v1/stats/overview")
    assert response.status_code == 200, response.text
    stats = response.json()
    assert stats == {
        "animals_total": 40,
        "new_today": 1,
        "with_primary_image": 39,
        "last_synced_at": (NOW - timedelta(minutes=1)).isoformat().replace("+00:00", "Z"),
    }


def test_year_rollover_recomputes_groups_and_suppresses_stale_tags(env):
    assert detail(env, 2)["animal"]["age_group"] == "puppy"
    env.app.dependency_overrides[read_today] = lambda: date(2027, 1, 1)
    data = detail(env, 2)
    assert data["animal"]["age_group"] == "young"
    assert "puppy" not in {row["key"] for row in data["tags"]}
    assert "young" not in {row["key"] for row in data["tags"]}  # Read API creates no tags.
    data = listing(env, tag="puppy", page_size=60)
    assert [row["id"] for row in data["items"]] == [str(UUID(int=1))]


@pytest.mark.parametrize(
    "days,expected", [(9, "보호중"), (10, "입양 가능"), (-1, "보호중"), (None, "보호중")]
)
def test_notice_display_boundary_keeps_database_source_state(env, days, expected):
    with env.engine.begin() as conn:
        conn.execute(
            update(Animal)
            .where(Animal.id == UUID(int=1))
            .values(notice_start=TODAY - timedelta(days=days) if days is not None else None)
        )
    assert detail(env, 1)["notice"]["process_state"] == expected
    with env.engine.connect() as conn:
        assert conn.scalar(select(Animal.process_state).where(Animal.id == UUID(int=1))) == "보호중"


def test_query_count_is_constant_for_one_and_24_cards(env):
    statements = []

    def observe(conn, cursor, statement, parameters, context, executemany):
        if statement.lstrip().upper().startswith(("SELECT", "WITH")):
            statements.append(statement)

    event.listen(env.engine, "before_cursor_execute", observe)
    try:
        listing(env, page_size=1)
        one = len(statements)
        statements.clear()
        listing(env, page_size=24)
        assert one == len(statements) == 4
        statements.clear()
        detail(env, 1)
        assert len(statements) == 3
    finally:
        event.remove(env.engine, "before_cursor_execute", observe)


def test_read_repository_rejects_writes_and_leaves_data_unchanged(env):
    repository = ReadRepository(SimpleNamespace(engine=env.engine))
    with repository.snapshot(TODAY) as queries:
        assert queries.connection.scalar(text("SHOW transaction_read_only")) == "on"
        assert queries.connection.scalar(text("SHOW transaction_isolation")) == "repeatable read"
        assert queries.connection.scalar(text("SHOW statement_timeout")) == "5s"
        with pytest.raises(DBAPIError) as failure:
            queries.connection.execute(
                insert(Tag).values(key="forbidden", type="fact", label="should not write")
            )
        assert failure.value.orig.sqlstate == "25006"
    assert listing(env)["pagination"]["total"] == 40


def test_unsupported_images_are_not_given_an_invented_type(env):
    with env.engine.begin() as conn:
        conn.execute(
            insert(AnimalImage).values(
                animal_id=UUID(int=8),
                image_url="https://example.invalid/unknown.jpg",
                image_type=None,
            )
        )
    assert detail(env, 8)["images"] == []
    assert env.client.get("/api/v1/stats/overview").json()["with_primary_image"] == 39


def test_transaction_timeout_uses_configuration_and_cancels_slow_sql(env):
    repository = ReadRepository(SimpleNamespace(engine=env.engine, statement_timeout_ms=100))
    with repository.snapshot(TODAY) as queries:
        assert queries.connection.scalar(text("SHOW statement_timeout")) == "100ms"
        with pytest.raises(DBAPIError) as failure:
            queries.connection.execute(text("SELECT pg_sleep(0.2)"))
        assert failure.value.orig.sqlstate == "57014"
