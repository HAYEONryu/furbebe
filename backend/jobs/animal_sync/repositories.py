"""PostgreSQL bulk writes; transaction ownership belongs to the sync service."""

from collections import Counter
from dataclasses import asdict, dataclass
from datetime import datetime
from uuid import uuid4

from sqlalchemy import and_, delete, func, or_, select, update
from sqlalchemy.dialects.postgresql import insert

from backend.app.db.models import Animal, AnimalImage, AnimalTag, Shelter, SyncRun, Tag

from .client import ApiFailure
from .normalizer import SOURCE
from .tagger import CATALOG, GENERATOR, OWNED_KEYS, VERSION, generate_tags
from .tagger.behavior import RELEASED_RULE_IDS, generate_behavior_tags
from .tagger.behavior import VERSION as BEHAVIOR_VERSION
from .tagger.catalog import TRAIT_CATALOG, TRAIT_KEYS, VIBE_KEYS


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


REPLACED_VERSIONS = ("1.0", "2.0", BEHAVIOR_VERSION)


def owned_assignments():
    return and_(
        AnimalTag.generator == GENERATOR,
        AnimalTag.generator_version.in_(REPLACED_VERSIONS),
        AnimalTag.tag_key.in_(TRAIT_KEYS),
        AnimalTag.tag_key.in_(select(Tag.key).where(Tag.type == "trait")),
        AnimalTag.animal_id.in_(select(Animal.id).where(Animal.source == SOURCE)),
    )


def reconcile_behavior(connection, rows, *, rule_ids):
    """Caller owns transaction/lock. Touch only known automatic TRAIT assignments."""
    matches = [
        (row["id"], tag) for row in rows for tag in generate_behavior_tags(row, rule_ids=rule_ids)
    ]
    wanted_keys = {tag.tag_key for _, tag in matches}
    existing_types = dict(
        connection.execute(
            select(Tag.key, Tag.type).where(Tag.key.in_(TRAIT_KEYS)),
        ).all()
    )
    if any(kind != "trait" for kind in existing_types.values()):
        raise ApiFailure("BEHAVIOR_CATALOG_TYPE_CONFLICT")
    additions = [row for row in TRAIT_CATALOG if row["key"] in wanted_keys]
    if additions:
        # Never change is_active, display metadata, or any FACT/VIBE catalog row.
        connection.execute(
            insert(Tag).values(additions).on_conflict_do_nothing(index_elements=[Tag.key])
        )
    active = set(
        connection.scalars(
            select(Tag.key).where(
                Tag.type == "trait",
                Tag.key.in_(TRAIT_KEYS),
                Tag.is_active.is_(True),
            )
        )
    )
    desired = []
    for animal_id, tag in matches:
        if tag.tag_key not in active:
            continue
        if not all((tag.evidence.strip(), tag.rule_id, tag.generator, tag.generator_version)):
            raise ApiFailure("BEHAVIOR_EVIDENCE_REQUIRED")
        desired.append({"id": uuid4(), "animal_id": animal_id, **asdict(tag)})
    wanted = {(row["animal_id"], row["tag_key"]) for row in desired}
    old = connection.execute(
        select(
            AnimalTag.id,
            AnimalTag.animal_id,
            AnimalTag.tag_key,
            AnimalTag.generator_version,
        ).where(owned_assignments(), AnimalTag.animal_id.in_([row["id"] for row in rows]))
    ).all()
    obsolete = [
        row.id
        for row in old
        if row.generator_version != BEHAVIOR_VERSION or (row.animal_id, row.tag_key) not in wanted
    ]
    for block in chunks(obsolete):
        connection.execute(delete(AnimalTag).where(AnimalTag.id.in_(block)))
    for block in chunks(desired):
        statement = insert(AnimalTag).values(block)
        connection.execute(
            statement.on_conflict_do_update(
                index_elements=[
                    AnimalTag.animal_id,
                    AnimalTag.tag_key,
                    AnimalTag.generator,
                    AnimalTag.generator_version,
                ],
                set_={
                    name: statement.excluded[name] for name in ("evidence", "rule_id", "confidence")
                },
            )
        )
    return Counter(row["tag_key"] for row in desired)


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
        # Existing v1 FACT/VIBE entries remain active; TRAIT migration has no
        # authority to retire them or remove their assignments.
        statement = insert(Tag).values(CATALOG)
        statement = statement.on_conflict_do_update(
            index_elements=[Tag.key],
            set_={
                name: statement.excluded[name]
                for name in ("label", "emoji", "description", "display_order")
            },
            # Refresh owned metadata when the catalog grows; preserve disabled tags
            # and let the type-conflict check below reject incompatible definitions.
            where=Tag.type == statement.excluded.type,
        )
        self.connection.execute(statement)
        existing = self.connection.execute(
            select(Tag.key, Tag.type, Tag.is_active).where(Tag.key.in_(OWNED_KEYS))
        ).all()
        expected = {row["key"]: row["type"] for row in CATALOG}
        if any(expected[row.key] != row.type for row in existing):
            raise ApiFailure("TAG_CATALOG_TYPE_CONFLICT")
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
        removed = []
        excluded = 0
        for animal in animals:
            old = existing.get(animal.values["source_id"])
            incoming = animal.values["source_updated_at"]
            if old and old.source_updated_at and incoming and incoming < old.source_updated_at:
                stale.append(old.id)
            elif animal.values.get("species") != "dog" or animal.values.get("process_state") not in {"보호중", "입양 가능"}:
                excluded += 1
                if old:
                    removed.append(old.id)
            else:
                current.append(animal)
        if removed:
            self.connection.execute(delete(Animal).where(Animal.id.in_(removed)))
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
        counts = BatchCounts(inserted, changed_count - inserted, len(stale), unchanged_count, excluded, len(removed))
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
            self.connection.execute(delete(AnimalImage).where(AnimalImage.id.in_(block)))
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
                    set_={"sort_order": statement.excluded.sort_order, "image_type": "source"},
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
            if tag.tag_key in active and tag.tag_key in VIBE_KEYS
        ]
        wanted = {(row["animal_id"], row["tag_key"]) for row in rows}
        ownership = and_(
            AnimalTag.animal_id.in_(list(ids.values())),
            AnimalTag.generator == GENERATOR,
            AnimalTag.generator_version == VERSION,
            AnimalTag.tag_key.in_(VIBE_KEYS),
        )
        existing = self.connection.execute(
            select(AnimalTag.id, AnimalTag.animal_id, AnimalTag.tag_key).where(ownership)
        ).all()
        obsolete = [row.id for row in existing if (row.animal_id, row.tag_key) not in wanted]
        for block in chunks(obsolete):
            self.connection.execute(delete(AnimalTag).where(AnimalTag.id.in_(block)))
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
                    },
                )
            )
        reconcile_behavior(
            self.connection,
            [{**animal.values, "id": ids[animal.values["source_id"]]} for animal in animals],
            rule_ids=RELEASED_RULE_IDS,
        )
