"""Schema contracts without opening a connection or substituting SQLite for JSONB."""

import io
from datetime import timedelta
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from alembic.script import ScriptDirectory
from sqlalchemy import CheckConstraint, DateTime, UniqueConstraint, create_mock_engine
from sqlalchemy.orm import configure_mappers

from backend.app.db.models import Animal, AnimalImage, AnimalTag, Base, Shelter, SyncRun, Tag
from backend.app.db.models.base import utc_now

TABLES = {"shelters", "animals", "animal_images", "tags", "animal_tags", "sync_runs"}
SOURCE_TEXTS = {
    "special_mark",
    "social_text",
    "health_text",
    "etc_text",
    "vaccination_text",
    "health_check_text",
}


def test_metadata_builds_postgresql_ddl_and_registers_all_mappers():
    configure_mappers()
    ddl = []
    engine = create_mock_engine(
        "postgresql+psycopg://",
        lambda sql, *args, **kwargs: ddl.append(str(sql.compile(dialect=engine.dialect))),
    )
    Base.metadata.create_all(engine)
    assert set(Base.metadata.tables) == TABLES
    assert len([sql for sql in ddl if "CREATE TABLE" in sql]) == 6
    assert "JSONB" in "\n".join(ddl)
    assert not {"size_group", "age_group", "estimated_age", "animals_active"} & set(
        Animal.__table__.columns.keys()
    )
    assert "animals_active" not in "\n".join(ddl)


@pytest.mark.parametrize(
    "model,required",
    [
        (
            Animal,
            {
                "id",
                "source",
                "source_id",
                "raw_payload",
                "first_seen_at",
                "last_seen_at",
                "created_at",
                "updated_at",
            },
        ),
        (Shelter, {"id", "source", "source_id", "created_at", "updated_at"}),
        (AnimalImage, {"id", "animal_id", "image_url", "sort_order", "created_at"}),
        (Tag, {"key", "type", "label", "is_active", "display_order", "created_at", "updated_at"}),
        (
            AnimalTag,
            {
                "id",
                "animal_id",
                "tag_key",
                "confidence",
                "generator",
                "generator_version",
                "created_at",
            },
        ),
        (
            SyncRun,
            {
                "id",
                "source",
                "started_at",
                "status",
                "page_count",
                "received_count",
                "inserted_count",
                "updated_count",
                "error_count",
                "created_at",
            },
        ),
    ],
)
def test_required_columns_and_nullable_source_fields(model, required):
    assert {column.name for column in model.__table__.columns if not column.nullable} == required
    if model is Animal:
        for name in SOURCE_TEXTS:
            column = model.__table__.c[name]
            assert column.nullable and column.default is None and column.server_default is None


def test_identity_and_assignment_uniqueness():
    expected = {
        "animals": {("source", "source_id")},
        "shelters": {("source", "source_id")},
        "animal_images": {("animal_id", "image_url")},
        "animal_tags": {("animal_id", "tag_key", "generator", "generator_version")},
        "tags": set(),
        "sync_runs": set(),
    }
    for table in Base.metadata.tables.values():
        assert {
            tuple(c.columns.keys()) for c in table.constraints if isinstance(c, UniqueConstraint)
        } == expected[table.name]
        assert tuple(table.primary_key.columns.keys()) == (
            ("key",) if table.name == "tags" else ("id",)
        )


def test_fk_delete_policies_match_orm_relationships():
    actual = {
        (table.name, fk.parent.name, fk.target_fullname, fk.ondelete)
        for table in Base.metadata.tables.values()
        for fk in table.foreign_keys
    }
    assert actual == {
        ("animals", "shelter_id", "shelters.id", "RESTRICT"),
        ("animal_images", "animal_id", "animals.id", "CASCADE"),
        ("animal_tags", "animal_id", "animals.id", "CASCADE"),
        ("animal_tags", "tag_key", "tags.key", "RESTRICT"),
    }
    assert Shelter.animals.property.passive_deletes == "all"
    assert Tag.animal_assignments.property.passive_deletes == "all"
    assert Animal.images.property.passive_deletes is True
    assert Animal.tag_assignments.property.passive_deletes is True


def test_all_operational_timestamps_are_timezone_aware():
    timestamps = [
        column
        for table in Base.metadata.tables.values()
        for column in table.columns
        if column.name.endswith("_at")
    ]
    assert len(timestamps) == 14
    assert all(isinstance(c.type, DateTime) and c.type.timezone for c in timestamps)
    assert utc_now().utcoffset() == timedelta(0)


def test_explicit_checks_keep_source_state_open():
    checks = {
        table.name: {str(c.sqltext) for c in table.constraints if isinstance(c, CheckConstraint)}
        for table in Base.metadata.tables.values()
    }
    assert "confidence >= 0 AND confidence <= 1" in checks["animal_tags"]
    assert "type IN ('fact', 'trait', 'vibe')" in checks["tags"]
    assert "status IN ('running', 'success', 'failed')" in checks["sync_runs"]
    assert not any("process_state" in expression for expression in checks["animals"])


def test_only_documented_query_indexes_exist():
    expected = {
        "animals": {
            ("process_state",),
            ("found_date",),
            ("notice_end",),
            ("shelter_id",),
            ("breed",),
            ("sex",),
            ("weight_kg",),
            ("birth_year",),
        },
        "animal_tags": {("tag_key", "animal_id")},
        "animal_images": {("animal_id", "sort_order")},
        "shelters": set(),
        "tags": set(),
        "sync_runs": set(),
    }
    for table in Base.metadata.tables.values():
        assert {tuple(index.columns.keys()) for index in table.indexes} == expected[table.name]


def test_initial_revision_graph_and_offline_sql():
    output = io.StringIO()
    config = Config(str(Path(__file__).resolve().parents[1] / "alembic.ini"), output_buffer=output)
    script = ScriptDirectory.from_config(config)
    assert script.get_heads() == ["20260915_0001"]
    revisions = list(script.walk_revisions())
    assert len(revisions) == 1 and revisions[0].down_revision is None
    command.upgrade(config, "head", sql=True)
    upgrade = output.getvalue()
    for table in TABLES:
        assert f"CREATE TABLE {table} (" in upgrade
    assert "JSONB" in upgrade and "TIMESTAMP WITH TIME ZONE" in upgrade
    assert "INSERT INTO tags" not in upgrade
    output.seek(0)
    output.truncate(0)
    command.downgrade(config, "20260915_0001:base", sql=True)
    assert sum(f"DROP TABLE {table};" in output.getvalue() for table in TABLES) == 6
