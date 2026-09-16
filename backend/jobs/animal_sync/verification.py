"""Read-only PostgreSQL inspection; reports contain aggregates, never animal payloads."""

from datetime import UTC, datetime

from alembic.autogenerate import compare_metadata
from alembic.migration import MigrationContext
from sqlalchemy import func, inspect, select, text

from backend.app.db.models import Animal, AnimalImage, Base, Shelter

from .normalizer import normalize_animal
from .source_models import ValidatedAnimal
from .status_policy import korea_today

DOMAIN_TABLES = frozenset(Base.metadata.tables)


def preflight(connection):
    tables = set(inspect(connection).get_table_names(schema="public"))
    return {
        "postgres_version": connection.scalar(text("SHOW server_version")),
        "alembic_version_exists": "alembic_version" in tables,
        "alembic_revisions": connection.scalars(
            text("SELECT version_num FROM public.alembic_version ORDER BY version_num")
        ).all()
        if "alembic_version" in tables
        else [],
        "domain_tables_present": sorted(tables & DOMAIN_TABLES),
        "other_public_table_count": len(tables - DOMAIN_TABLES - {"alembic_version"}),
    }


def schema_manifest(connection):
    """Compare with the same migration on local PostgreSQL, including CHECK definitions."""
    inspector = inspect(connection)
    manifest = {}
    for name in sorted(DOMAIN_TABLES):
        manifest[name] = {
            "columns": {
                column["name"]: {
                    "type": str(column["type"]),
                    "nullable": column["nullable"],
                    "timezone": getattr(column["type"], "timezone", None),
                }
                for column in inspector.get_columns(name, schema="public")
            },
            "primary_key": inspector.get_pk_constraint(name, schema="public")[
                "constrained_columns"
            ],
            "unique": {
                constraint["name"]: constraint["column_names"]
                for constraint in inspector.get_unique_constraints(name, schema="public")
            },
            "foreign_keys": {
                constraint["name"]: {
                    "columns": constraint["constrained_columns"],
                    "table": constraint["referred_table"],
                    "schema": constraint["referred_schema"] or "public",
                    "referred_columns": constraint["referred_columns"],
                    "ondelete": constraint["options"].get("ondelete", "NO ACTION"),
                }
                for constraint in inspector.get_foreign_keys(name, schema="public")
            },
            "checks": {
                constraint["name"]: " ".join(constraint["sqltext"].split())
                for constraint in inspector.get_check_constraints(name, schema="public")
            },
            "indexes": {
                index["name"]: {"columns": index["column_names"], "unique": index["unique"]}
                for index in inspector.get_indexes(name, schema="public")
            },
        }
    return manifest


def metadata_difference_count(connection):
    # Supabase-owned tables are outside the application metadata and must be ignored.
    def include_object(obj, name, type_, reflected, compare_to):
        return type_ != "table" or name in DOMAIN_TABLES

    context = MigrationContext.configure(
        connection,
        opts={"compare_type": True, "include_object": include_object},
    )
    return len(compare_metadata(context, Base.metadata))


def data_integrity(connection):
    counts = {
        name: connection.scalar(select(func.count()).select_from(table))
        for name, table in Base.metadata.tables.items()
    }
    checks = {
        "orphan_animal_images": "SELECT count(*) FROM animal_images i LEFT JOIN animals a ON a.id=i.animal_id WHERE a.id IS NULL",
        "orphan_animal_tags": "SELECT count(*) FROM animal_tags t LEFT JOIN animals a ON a.id=t.animal_id WHERE a.id IS NULL",
        "invalid_shelter_fk": "SELECT count(*) FROM animals a LEFT JOIN shelters s ON s.id=a.shelter_id WHERE a.shelter_id IS NOT NULL AND s.id IS NULL",
        "duplicate_source_source_id": "SELECT count(*) FROM (SELECT source,source_id FROM animals GROUP BY source,source_id HAVING count(*)>1) d",
        "duplicate_animal_images": "SELECT count(*) FROM (SELECT animal_id,image_url FROM animal_images GROUP BY animal_id,image_url HAVING count(*)>1) d",
        "duplicate_animal_tags": "SELECT count(*) FROM (SELECT animal_id,tag_key,generator,generator_version FROM animal_tags GROUP BY animal_id,tag_key,generator,generator_version HAVING count(*)>1) d",
        "confidence_outside_range": "SELECT count(*) FROM animal_tags WHERE confidence < 0 OR confidence > 1 OR confidence IS NULL",
        "invalid_raw_payload": "SELECT count(*) FROM animals WHERE raw_payload IS NULL OR jsonb_typeof(raw_payload) <> 'object'",
        "invalid_observation_order": "SELECT count(*) FROM animals WHERE first_seen_at > last_seen_at",
    }
    return {
        "counts": counts,
        "unique_source_animals": connection.scalar(
            text("SELECT count(*) FROM (SELECT DISTINCT source,source_id FROM animals) a")
        ),
        "violations": {name: connection.scalar(text(query)) for name, query in checks.items()},
    }


def verify_sample(connection, *, limit=10):
    """Check source facts and child relations in SQL rows without returning those rows."""
    rows = (
        connection.execute(select(Animal.__table__).order_by(Animal.id).limit(limit))
        .mappings()
        .all()
    )
    failures = set()
    today = korea_today(datetime.now(UTC))
    for row in rows:
        expected = normalize_animal(ValidatedAnimal.model_validate(row["raw_payload"]), today=today)
        for name in ("source", "source_id", "notice_no", "breed", "weight_kg", "birth_year"):
            if row[name] != expected.values[name]:
                failures.add(name)
        if row["shelter_id"]:
            shelter = connection.execute(
                select(Shelter.source, Shelter.source_id).where(Shelter.id == row["shelter_id"])
            ).one_or_none()
            if (
                not expected.shelter
                or not shelter
                or shelter.source_id != expected.shelter["source_id"]
                or shelter.source != row["source"]
            ):
                failures.add("shelter_fk")
        elif expected.shelter:
            failures.add("shelter_fk")
        images = set(
            connection.scalars(
                select(AnimalImage.image_url).where(
                    AnimalImage.animal_id == row["id"], AnimalImage.image_type == "source"
                )
            )
        )
        if images != set(expected.images):
            failures.add("images")
        for name in ("first_seen_at", "last_seen_at"):
            if not row[name] or row[name].tzinfo is None:
                failures.add(name)
        if row["first_seen_at"] > row["last_seen_at"]:
            failures.add("observation_order")
    return {"checked": len(rows), "failed_fields": sorted(failures)}
