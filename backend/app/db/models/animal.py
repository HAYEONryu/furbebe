from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import TYPE_CHECKING, Any
from uuid import UUID

from sqlalchemy import (
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, CreatedAt, Timestamps, UUIDPrimaryKey, utc_now

if TYPE_CHECKING:
    from .shelter import Shelter
    from .tag import AnimalTag


class Animal(UUIDPrimaryKey, Timestamps, Base):
    __tablename__ = "animals"
    __table_args__ = (
        UniqueConstraint("source", "source_id", name="uq_animals_source_source_id"),
        CheckConstraint("btrim(source) <> ''", name="source_nonempty"),
        CheckConstraint("btrim(source_id) <> ''", name="source_id_nonempty"),
        CheckConstraint("birth_year BETWEEN 1 AND 9999", name="birth_year_range"),
        CheckConstraint(
            "weight_kg >= 0 AND weight_kg < 'Infinity'::numeric",
            name="weight_kg_finite_nonnegative",
        ),
        CheckConstraint("sex IN ('male', 'female', 'unknown')", name="sex_values"),
        CheckConstraint("neutered IN ('yes', 'no', 'unknown')", name="neutered_values"),
        CheckConstraint("jsonb_typeof(raw_payload) = 'object'", name="raw_payload_object"),
        # v1 exact filters and date/weight/age ordering; rationale in database-schema.md.
        Index("ix_animals_process_state", "process_state"),
        Index("ix_animals_found_date", "found_date"),
        Index("ix_animals_notice_end", "notice_end"),
        Index("ix_animals_shelter_id", "shelter_id"),
        Index("ix_animals_breed", "breed"),
        Index("ix_animals_sex", "sex"),
        Index("ix_animals_weight_kg", "weight_kg"),
        Index("ix_animals_birth_year", "birth_year"),
    )

    source: Mapped[str] = mapped_column(Text)
    source_id: Mapped[str] = mapped_column(Text)
    notice_no: Mapped[str | None] = mapped_column(Text)
    rfid_code: Mapped[str | None] = mapped_column(Text)
    species: Mapped[str | None] = mapped_column(Text)
    breed: Mapped[str | None] = mapped_column(Text)
    breed_full: Mapped[str | None] = mapped_column(Text)
    sex: Mapped[str | None] = mapped_column(Text)
    neutered: Mapped[str | None] = mapped_column(Text)
    age_text: Mapped[str | None] = mapped_column(Text)
    birth_year: Mapped[int | None] = mapped_column(Integer)
    weight_text: Mapped[str | None] = mapped_column(Text)
    weight_kg: Mapped[Decimal | None] = mapped_column(Numeric)
    color_text: Mapped[str | None] = mapped_column(Text)
    found_date: Mapped[date | None] = mapped_column(Date)
    found_place: Mapped[str | None] = mapped_column(Text)
    # Raw source vocabulary is intentionally open, including unknown future states.
    process_state: Mapped[str | None] = mapped_column(Text)
    end_reason: Mapped[str | None] = mapped_column(Text)
    notice_start: Mapped[date | None] = mapped_column(Date)
    notice_end: Mapped[date | None] = mapped_column(Date)
    special_mark: Mapped[str | None] = mapped_column(Text)
    social_text: Mapped[str | None] = mapped_column(Text)
    health_text: Mapped[str | None] = mapped_column(Text)
    etc_text: Mapped[str | None] = mapped_column(Text)
    vaccination_text: Mapped[str | None] = mapped_column(Text)
    health_check_text: Mapped[str | None] = mapped_column(Text)
    shelter_id: Mapped[UUID | None] = mapped_column(ForeignKey("shelters.id", ondelete="RESTRICT"))
    raw_payload: Mapped[dict[str, Any]] = mapped_column(JSONB(none_as_null=True))
    first_seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, server_default=func.now()
    )
    last_seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, server_default=func.now()
    )
    source_updated_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))

    shelter: Mapped[Shelter | None] = relationship(back_populates="animals")
    images: Mapped[list[AnimalImage]] = relationship(
        back_populates="animal",
        cascade="all, delete-orphan",
        passive_deletes=True,
        order_by=lambda: (AnimalImage.sort_order, AnimalImage.id),
    )
    tag_assignments: Mapped[list[AnimalTag]] = relationship(
        back_populates="animal", cascade="all, delete-orphan", passive_deletes=True
    )


class AnimalImage(UUIDPrimaryKey, CreatedAt, Base):
    __tablename__ = "animal_images"
    __table_args__ = (
        UniqueConstraint("animal_id", "image_url", name="uq_animal_images_animal_id_image_url"),
        CheckConstraint("btrim(image_url) <> ''", name="image_url_nonempty"),
        CheckConstraint("sort_order >= 0", name="sort_order_nonnegative"),
        # Detail/card images in display order; id provides a stable tie breaker.
        Index("ix_animal_images_animal_id_sort_order", "animal_id", "sort_order"),
    )

    animal_id: Mapped[UUID] = mapped_column(ForeignKey("animals.id", ondelete="CASCADE"))
    image_url: Mapped[str] = mapped_column(Text)
    sort_order: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    image_type: Mapped[str | None] = mapped_column(Text)

    animal: Mapped[Animal] = relationship(back_populates="images")
