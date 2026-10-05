"""PostgreSQL bulk writes; transaction ownership belongs to the sync service."""

from dataclasses import dataclass
from datetime import datetime
from uuid import uuid4

from sqlalchemy import and_, func, or_, select, update
from sqlalchemy.dialects.postgresql import insert

from backend.app.db.models import Animal, AnimalImage, AnimalTag, Shelter, SyncRun, Tag

from .client import ApiFailure
from .normalizer import SOURCE
from .status_policy import is_listed_dog
from .tagger import CATALOG, GENERATOR, OWNED_KEYS, generate_tags


@dataclass(frozen=True)
class BatchCounts:
    inserted: int
    updated: int
    stale: int = 0
    unchanged: int = 0
    excluded: int = 0
    deleted: int = 0


def chunks(rows, size=1000):
    # Child rows can exceed the PostgreSQL bind parameter limit even for 500 animals.
    for offset in range(0, len(rows), size):
        yield rows[offset : offset + size]


class SyncRepository:
    def __init__(self, connection):
        self.connection = connection

    def start_run(self, sync_id, now):
        self.connection.execute(insert(SyncRun).values(id=sync_id, source=SOURCE, started_at=now))

    def progress(self, sync_id, *, page_count, received_count, error_count):
        self.connection.execute(
            update(SyncRun)
            .where(SyncRun.id == sync_id)
            .values(page_count=page_count, received_count=received_count, error_count=error_count)
        )

    def finish_run(self, sync_id, *, status, now, error_message):
        self.connection.execute(
            update(SyncRun)
            .where(SyncRun.id == sync_id)
            .values(status=status, finished_at=now, error_message=error_message)
        )

    def counts(self, sync_id):
        return self.connection.execute(
            select(SyncRun.inserted_count, SyncRun.updated_count).where(SyncRun.id == sync_id)
        ).one()

    def catalog(self):
        statement = insert(Tag).values(CATALOG).on_conflict_do_nothing(index_elements=[Tag.key])
        self.connection.execute(statement)
        existing = self.connection.execute(
            select(Tag.key, Tag.type, Tag.is_active).where(Tag.key.in_(OWNED_KEYS))
        ).all()
        expected = {row["key"]: row["type"] for row in CATALOG}
        if any(expected[row.key] != row.type for row in existing):
            raise ApiFailure("TAG_CATALOG_TYPE_CONFLICT")
        # Keep generated presentation fields current without changing activation or ownership.
        presentation = insert(Tag).values(CATALOG)
        self.connection.execute(
            presentation.on_conflict_do_update(
                index_elements=[Tag.key],
                set_={
                    "label": presentation.excluded.label, "emoji": presentation.excluded.emoji,
                    "description": presentation.excluded.description,
                    "display_order": presentation.excluded.display_order,
                },
            )
        )
        return {row.key for row in existing if row.is_active}

    def upsert_shelters(self, animals, now):
        shelters = {}
        for animal in animals:
            if animal.shelter:
                key = animal.shelter["source_id"]
                if key not in shelters:
                    shelters[key] = dict(animal.shelter)
                else:
                    for name, value in animal.shelter.items():
                        if shelters[key][name] is None:
                            shelters[key][name] = value
        if not shelters:
            return {}
        rows = [
            dict(shelters[key], id=uuid4(), created_at=now, updated_at=now)
            for key in sorted(shelters)
        ]
        statement = insert(Shelter).values(rows)
        statement = statement.on_conflict_do_update(
            index_elements=[Shelter.source, Shelter.source_id],
            set_={
                **{
                    name: func.coalesce(statement.excluded[name], Shelter.__table__.c[name])
                    for name in ("name", "phone", "address", "owner_name", "organization")
                },
                "updated_at": now,
            },
        ).returning(Shelter.source_id, Shelter.id)
        return dict(self.connection.execute(statement).all())

    def upsert_batch(self, sync_id, animals, *, now: datetime, today) -> BatchCounts:
        # A single source-wide advisory lock is held by the service across all batches.
        # It makes pre-read insert/update accounting exact for cooperating sync writers.
        animals = sorted(animals, key=lambda item: item.values["source_id"])
        keys = [animal.values["source_id"] for animal in animals]
        if len(keys) != len(set(keys)):
            raise ApiFailure("DUPLICATE_BATCH_ID")
        existing = {
            row.source_id: row
            for row in self.connection.execute(
                select(Animal.__table__).where(Animal.source == SOURCE, Animal.source_id.in_(keys))
            )
        }
        stale = []
        current = []
        archived = []
        excluded = 0
        for animal in animals:
            old = existing.get(animal.values["source_id"])
            incoming = animal.values["source_updated_at"]
            if old and old.source_updated_at and incoming and incoming < old.source_updated_at:
                stale.append(old.id)
            elif not is_listed_dog(animal.values, today=today):
                excluded += 1
                if old:
                    archived.append(animal)
            else:
                current.append(animal)
        archived_changed = 0
        for animal in archived:
            values = dict(animal.values)
            values["source_updated_at"] = values["source_updated_at"] or existing[animal.values["source_id"]].source_updated_at
            old = existing[animal.values["source_id"]]
            changed = old.is_active or any(values[name] != old._mapping[name] for name in values)
            archived_changed += int(changed)
            self.connection.execute(
                update(Animal).where(Animal.id == old.id)
                .values(**values, is_active=False, last_seen_at=now, updated_at=now if changed else old.updated_at)
            )
        if stale:
            self.connection.execute(
                update(Animal)
                .where(Animal.id.in_(stale))
                .values(last_seen_at=now, updated_at=Animal.updated_at)
            )
        changed_count = unchanged_count = 0
        if current:
            shelters = self.upsert_shelters(current, now)
            rows = [
                dict(
                    animal.values,
                    is_active=True,
                    id=uuid4(),
                    shelter_id=shelters.get(animal.shelter["source_id"])
                    if animal.shelter
                    else None,
                    first_seen_at=now,
                    last_seen_at=now,
                    created_at=now,
                    updated_at=now,
                )
                for animal in current
            ]
            immutable = {"id", "source", "source_id", "first_seen_at", "created_at"}
            content = set(rows[0]) - immutable - {"last_seen_at", "updated_at"}
            changed_rows, unchanged_ids, ids = [], [], {}
            for row in rows:
                old = existing.get(row["source_id"])
                if old is not None:
                    # Preserve the latest known aware timestamp, as in the existing UPSERT.
                    row["source_updated_at"] = row["source_updated_at"] or old.source_updated_at
                if old is not None and all(row[name] == old._mapping[name] for name in content):
                    unchanged_ids.append(old.id)
                    ids[row["source_id"]] = old.id
                else:
                    changed_rows.append(row)
            unchanged_count = len(unchanged_ids)
            changed_count = len(changed_rows)
            if unchanged_ids:
                self.connection.execute(
                    update(Animal)
                    .where(Animal.id.in_(unchanged_ids))
                    .values(last_seen_at=now, updated_at=Animal.updated_at)
                )
            if changed_rows:
                statement = insert(Animal).values(changed_rows)
                statement = statement.on_conflict_do_update(
                    index_elements=[Animal.source, Animal.source_id],
                    set_={
                        c.name: statement.excluded[c.name]
                        for c in Animal.__table__.columns
                        if c.name not in immutable
                    },
                ).returning(Animal.source_id, Animal.id)
                ids.update(self.connection.execute(statement).all())
            self.reconcile_images(current, ids)
            active = self.catalog()
            self.reconcile_tags(current, ids, active=active, today=today)
        inserted = sum(animal.values["source_id"] not in existing for animal in current)
        counts = BatchCounts(
            inserted, changed_count - inserted + archived_changed, len(stale), unchanged_count, excluded, 0
        )
        # Domain changes and durable counters commit together.
        self.connection.execute(
            update(SyncRun)
            .where(SyncRun.id == sync_id)
            .values(
                inserted_count=SyncRun.inserted_count + counts.inserted,
                updated_count=SyncRun.updated_count + counts.updated,
            )
        )
        return counts

    def reconcile_images(self, animals, ids):
        wanted = {(ids[a.values["source_id"]], url) for a in animals for url in a.images}
        existing = self.connection.execute(
            select(
                AnimalImage.id, AnimalImage.animal_id, AnimalImage.image_url, AnimalImage.image_type
            ).where(AnimalImage.animal_id.in_(list(ids.values())))
        ).all()
        obsolete = [
            row.id
            for row in existing
            if row.image_type == "source" and (row.animal_id, row.image_url) not in wanted
        ]
        for block in chunks(obsolete):
            self.connection.execute(update(AnimalImage).where(AnimalImage.id.in_(block)).values(is_active=False))
        rows = [
            dict(
                id=uuid4(),
                animal_id=ids[a.values["source_id"]],
                image_url=url,
                sort_order=order,
                image_type="source",
            )
            for a in animals
            for order, url in enumerate(a.images, start=1)
        ]
        for block in chunks(rows):
            statement = insert(AnimalImage).values(block)
            self.connection.execute(
                statement.on_conflict_do_update(
                    index_elements=[AnimalImage.animal_id, AnimalImage.image_url],
                    set_={"sort_order": statement.excluded.sort_order, "image_type": "source", "is_active": True},
                    # Preserve an independently owned image if its URL happens to match.
                    where=or_(AnimalImage.image_type == "source", AnimalImage.image_type.is_(None)),
                )
            )

    def reconcile_tags(self, animals, ids, *, active, today):
        rows = [
            dict(
                id=uuid4(),
                animal_id=ids[animal.values["source_id"]],
                tag_key=tag.tag_key,
                confidence=tag.confidence,
                evidence=tag.evidence,
                rule_id=tag.rule_id,
                generator=tag.generator,
                generator_version=tag.generator_version,
            )
            for animal in animals
            for tag in generate_tags(animal, today=today)
            if tag.tag_key in active
        ]
        wanted = {(row["animal_id"], row["tag_key"]) for row in rows}
        versions = {(row["animal_id"], row["tag_key"]): row["generator_version"] for row in rows}
        ownership = and_(
            AnimalTag.animal_id.in_(list(ids.values())),
            AnimalTag.generator == GENERATOR,
            AnimalTag.tag_key.in_(OWNED_KEYS),
        )
        existing = self.connection.execute(
            select(AnimalTag.id, AnimalTag.animal_id, AnimalTag.tag_key, AnimalTag.generator_version).where(ownership)
        ).all()
        obsolete = [
            row.id
            for row in existing
            if row.generator_version != versions.get((row.animal_id, row.tag_key))
            or (row.animal_id, row.tag_key) not in wanted
        ]
        for block in chunks(obsolete):
            self.connection.execute(update(AnimalTag).where(AnimalTag.id.in_(block)).values(is_active=False))
        for block in chunks(rows):
            statement = insert(AnimalTag).values(block)
            self.connection.execute(
                statement.on_conflict_do_update(
                    index_elements=[
                        AnimalTag.animal_id,
                        AnimalTag.tag_key,
                        AnimalTag.generator,
                        AnimalTag.generator_version,
                    ],
                    set_={
                        name: statement.excluded[name]
                        for name in ("confidence", "evidence", "rule_id")
                    } | {"is_active": True},
                )
            )
