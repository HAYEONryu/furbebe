"""Bounded, parameterized PostgreSQL reads in a consistent read-only transaction."""

from contextlib import contextmanager
from datetime import datetime, time, timedelta

from sqlalchemy import and_, case, exists, func, literal, not_, or_, select

from backend.app.db.models import Animal, AnimalImage, AnimalTag, Shelter, SyncRun, Tag
from backend.app.db.session import DatabaseNotConfigured
from backend.jobs.animal_sync.status_policy import KST

SUMMARY_FIELDS = (
    "id",
    "notice_no",
    "breed",
    "breed_full",
    "sex",
    "birth_year",
    "age_text",
    "weight_kg",
    "weight_text",
    "color_text",
    "found_date",
    "notice_end",
)
PROMOTION_FIELDS = {
    "title": "adptnTitle",
    "start_date": "adptnSDate",
    "end_date": "adptnEDate",
    "condition_text": "adptnConditionLimitTxt",
    "description": "adptnTxt",
    "image_url": "adptnImg",
}
IMAGE_TYPES = ("source", "adoption")
AGE_RULE_TAGS = {
    "puppy": "puppy",
    "young": "young",
    "adult": "adult",
    "senior": "senior",
    "baby_dog": "puppy",
    "senior_dog": "senior",
}


class ReadRepository:
    def __init__(self, database):
        self.database = database

    @contextmanager
    def snapshot(self, today):
        if self.database.engine is None:
            raise DatabaseNotConfigured("Database unavailable")
        # SET characteristics are applied through psycopg, including READ ONLY.
        with (
            self.database.engine.connect().execution_options(
                isolation_level="REPEATABLE READ", postgresql_readonly=True
            ) as connection,
            connection.begin(),
        ):
            # Session poolers may ignore startup options (DEV reports 2min instead
            # of our 5s). Keep the configured bound local to this read transaction.
            timeout_ms = int(getattr(self.database, "statement_timeout_ms", 5000))
            connection.exec_driver_sql(f"SET LOCAL statement_timeout = {timeout_ms}")
            yield AnimalQueries(connection, today)


class AnimalQueries:
    def __init__(self, connection, today):
        self.connection = connection
        self.today = today
        self.organization = func.nullif(
            func.btrim(func.regexp_replace(Animal.raw_payload["orgNm"].astext, r"\s+", " ", "g")),
            "",
        )
        self.size = case(
            (Animal.weight_kg.is_(None), "unknown"),
            (Animal.weight_kg <= 5, "tiny"),
            (Animal.weight_kg <= 10, "small"),
            (Animal.weight_kg <= 20, "medium"),
            else_="large",
        )
        age = today.year - Animal.birth_year
        self.age = case(
            (Animal.birth_year.is_(None), "unknown"),
            (age <= 1, "puppy"),
            (age <= 4, "young"),
            (age <= 8, "adult"),
            else_="senior",
        )
        self.state = case(
            (
                and_(
                    Animal.process_state == "보호중",
                    Animal.notice_start <= today - timedelta(days=10),
                ),
                "입양 가능",
            ),
            else_=Animal.process_state,
        )
        self.tags_view = self._effective_tags()

    def _effective_tags(self):
        # Do not expose known stale year-derived rule assignments as current facts.
        # This suppresses stale assignments only; it creates no new tags or rules.
        age_rule = and_(
            AnimalTag.generator == "rules",
            AnimalTag.generator_version == "1.0",
            AnimalTag.tag_key.in_(list(AGE_RULE_TAGS)),
        )
        fresh = and_(
            Animal.species == "dog",
            case(AGE_RULE_TAGS, value=AnimalTag.tag_key) == self.age,
        )
        ranked = (
            select(
                AnimalTag.animal_id,
                Tag.key,
                Tag.type,
                Tag.label,
                Tag.emoji,
                AnimalTag.confidence,
                AnimalTag.evidence,
                Tag.display_order,
                func.row_number()
                .over(
                    partition_by=(AnimalTag.animal_id, AnimalTag.tag_key),
                    order_by=(AnimalTag.created_at.desc(), AnimalTag.id.asc()),
                )
                .label("position"),
            )
            .join(Tag, Tag.key == AnimalTag.tag_key)
            .join(Animal, Animal.id == AnimalTag.animal_id)
            .where(Tag.is_active.is_(True), or_(not_(age_rule), fresh))
            .cte("ranked_tags")
        )
        return select(ranked).where(ranked.c.position == 1).cte("visible_tags")

    def projection(self, *, detail=False):
        columns = (
            [c for c in Animal.__table__.columns if c.name not in {"raw_payload", "process_state"}]
            if detail
            else [Animal.__table__.c[name] for name in SUMMARY_FIELDS]
        )
        if not detail:
            columns += [Animal.special_mark, Animal.social_text, Animal.health_text]
        statement = select(
            *columns,
            self.size.label("size_group"),
            self.age.label("age_group"),
            self.state.label("process_state"),
            self.organization.label("organization"),
        ).select_from(Animal)
        if detail:
            statement = statement.add_columns(
                *[
                    Animal.raw_payload[source].label("promotion_" + field)
                    for field, source in PROMOTION_FIELDS.items()
                ],
                Shelter.name.label("shelter_name"),
                Shelter.phone.label("shelter_phone"),
                Shelter.address.label("shelter_address"),
                Shelter.organization.label("shelter_organization"),
            ).outerjoin(Shelter, Shelter.id == Animal.shelter_id)
        return statement

    def known_tags(self, keys):
        return set(self.connection.scalars(select(Tag.key).where(Tag.key.in_(keys))))

    def predicates(self, filters, *, organizations=None):
        conditions = []
        if organizations is not None:
            conditions.append(self.organization.in_(organizations))
        for name in ("breed", "sex", "neutered"):
            value = getattr(filters, name)
            if value is not None:
                conditions.append(getattr(Animal, name) == value)
        for name, column in (
            ("size_group", self.size),
            ("age_group", self.age),
            ("process_state", self.state),
        ):
            if (value := getattr(filters, name)) is not None:
                conditions.append(column == value)
        if filters.q:
            # Search literal substrings: %, _ and backslash are not user wildcards.
            escaped = filters.q.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
            pattern = "%" + escaped + "%"
            shelter_match = exists(
                select(Shelter.id).where(
                    Shelter.id == Animal.shelter_id, Shelter.name.ilike(pattern, escape="\\")
                )
            )
            conditions.append(
                or_(
                    Animal.breed.ilike(pattern, escape="\\"),
                    self.organization.ilike(pattern, escape="\\"),
                    shelter_match,
                )
            )
        if filters.tag:
            matching_ids = select(self.tags_view.c.animal_id).where(
                self.tags_view.c.key.in_(filters.tag)
            )
            if filters.tag_match == "all":
                # The visible view has one row per animal/key. Group once rather
                # than repeating a correlated scan for every requested tag.
                matching_ids = matching_ids.group_by(self.tags_view.c.animal_id).having(
                    func.count() == len(filters.tag)
                )
            conditions.append(Animal.id.in_(matching_ids))
        return conditions

    def sort_columns(self, sort):
        primary = {
            "recent": Animal.found_date.desc(),
            "notice_end": Animal.notice_end.asc(),
            "weight_asc": Animal.weight_kg.asc(),
            "weight_desc": Animal.weight_kg.desc(),
            "age_youngest": Animal.birth_year.desc(),
            "age_oldest": Animal.birth_year.asc(),
        }[sort]
        return (primary.nulls_last(), Animal.source_updated_at.desc().nulls_last(), Animal.id.asc())

    def list_animals(self, filters, *, organizations=None):
        conditions = self.predicates(filters, organizations=organizations)
        total = self.connection.scalar(select(func.count()).select_from(Animal).where(*conditions))
        offset = (filters.page - 1) * filters.page_size
        if offset >= total:
            return [], total
        rows = (
            self.connection.execute(
                self.projection()
                .where(*conditions)
                .order_by(*self.sort_columns(filters.sort))
                .offset(offset)
                .limit(filters.page_size)
            )
            .mappings()
            .all()
        )
        return self.attach_children(rows), total

    def animal(self, animal_id):
        return (
            self.connection.execute(self.projection(detail=True).where(Animal.id == animal_id))
            .mappings()
            .one_or_none()
        )

    def attach_children(self, rows):
        if not rows:
            return []
        animals = {row["id"]: dict(row, images=[], tags=[]) for row in rows}
        images = self.connection.execute(
            select(
                AnimalImage.animal_id,
                AnimalImage.image_url,
                AnimalImage.image_type,
            )
            .where(AnimalImage.animal_id.in_(animals), AnimalImage.image_type.in_(IMAGE_TYPES))
            .order_by(
                AnimalImage.animal_id,
                AnimalImage.sort_order,
                AnimalImage.id,
            )
        )
        for row in images:
            target = animals[row.animal_id]["images"]
            target.append({"url": row.image_url, "order": len(target) + 1, "type": row.image_type})
        tags = self.connection.execute(
            select(self.tags_view)
            .where(self.tags_view.c.animal_id.in_(animals))
            .order_by(self.tags_view.c.display_order, self.tags_view.c.key)
        ).mappings()
        for row in tags:
            animals[row["animal_id"]]["tags"].append(
                {
                    name: row[name]
                    for name in ("key", "type", "label", "emoji", "confidence", "evidence")
                }
            )
        return list(animals.values())

    def similar(self, source, *, region_organizations, limit):
        score = literal(0)
        for condition, points in (
            (self.organization.in_(region_organizations), 3),
            (
                self.size == source["size_group"]
                if source["size_group"] != "unknown"
                else literal(False),
                2,
            ),
            (Animal.breed == source["breed"] if source["breed"] else literal(False), 2),
            (
                Animal.sex == source["sex"]
                if source["sex"] not in (None, "unknown")
                else literal(False),
                1,
            ),
            (
                self.age == source["age_group"]
                if source["age_group"] != "unknown"
                else literal(False),
                1,
            ),
        ):
            score += case((condition, points), else_=0)
        source_tags = select(self.tags_view.c.key).where(self.tags_view.c.animal_id == source["id"])
        # Aggregate once, then join once. A correlated scan of the ranked-tag CTE
        # for every candidate timed out on the 7,290-animal DEV dataset.
        shared_counts = (
            select(self.tags_view.c.animal_id, func.count().label("tag_count"))
            .where(self.tags_view.c.key.in_(source_tags))
            .group_by(self.tags_view.c.animal_id)
            .subquery("shared_tag_counts")
        )
        score += func.coalesce(shared_counts.c.tag_count, 0) * 2
        rows = (
            self.connection.execute(
                self.projection()
                .outerjoin(shared_counts, shared_counts.c.animal_id == Animal.id)
                .where(Animal.id != source["id"])
                .order_by(score.desc(), *self.sort_columns("recent"))
                .limit(limit)
            )
            .mappings()
            .all()
        )
        return self.attach_children(rows)

    def tag_catalog(self, *, type=None, active_only=True):
        statement = select(Tag.key, Tag.type, Tag.label, Tag.emoji, Tag.description)
        if type is not None:
            statement = statement.where(Tag.type == type)
        if active_only:
            statement = statement.where(Tag.is_active.is_(True))
        return (
            self.connection.execute(statement.order_by(Tag.display_order, Tag.key)).mappings().all()
        )

    def filter_facets(self):
        columns = {
            "organizations": self.organization,
            "breeds": Animal.breed,
            "sexes": Animal.sex,
            "neutered": Animal.neutered,
            "size_groups": self.size,
            "age_groups": self.age,
            "process_states": self.state,
        }
        # One grouped query computes all scalar facets; no per-animal lookups.
        grouped = select(
            *[column.label(name) for name, column in columns.items()], func.count().label("count")
        ).group_by(*columns.values())
        return self.connection.execute(grouped).mappings().all()

    def overview(self):
        start = datetime.combine(self.today, time.min, KST)
        has_image = exists(
            select(AnimalImage.id).where(
                AnimalImage.animal_id == Animal.id, AnimalImage.image_type.in_(IMAGE_TYPES)
            )
        )
        last_sync = (
            select(func.max(SyncRun.finished_at))
            .where(SyncRun.status == "success")
            .scalar_subquery()
        )
        return (
            self.connection.execute(
                select(
                    func.count().label("animals_total"),
                    func.count()
                    .filter(
                        and_(
                            Animal.first_seen_at >= start,
                            Animal.first_seen_at < start + timedelta(days=1),
                        )
                    )
                    .label("new_today"),
                    func.count().filter(has_image).label("with_primary_image"),
                    last_sync.label("last_synced_at"),
                ).select_from(Animal)
            )
            .mappings()
            .one()
        )
