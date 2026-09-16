from __future__ import annotations

from decimal import Decimal
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    Text,
    UniqueConstraint,
    true,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, CreatedAt, Timestamps, UUIDPrimaryKey

if TYPE_CHECKING:
    from .animal import Animal


class Tag(Timestamps, Base):
    __tablename__ = "tags"
    __table_args__ = (
        CheckConstraint("btrim(key) <> ''", name="key_nonempty"),
        CheckConstraint("type IN ('fact', 'trait', 'vibe')", name="type_values"),
        CheckConstraint("display_order >= 0", name="display_order_nonnegative"),
    )

    key: Mapped[str] = mapped_column(Text, primary_key=True)
    type: Mapped[str] = mapped_column(Text)
    label: Mapped[str] = mapped_column(Text)
    emoji: Mapped[str | None] = mapped_column(Text)
    description: Mapped[str | None] = mapped_column(Text)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, server_default=true())
    display_order: Mapped[int] = mapped_column(Integer, default=0, server_default="0")

    animal_assignments: Mapped[list[AnimalTag]] = relationship(
        back_populates="tag", passive_deletes="all"
    )


class AnimalTag(UUIDPrimaryKey, CreatedAt, Base):
    __tablename__ = "animal_tags"
    __table_args__ = (
        UniqueConstraint(
            "animal_id",
            "tag_key",
            "generator",
            "generator_version",
            name="uq_animal_tags_animal_tag_generator_version",
        ),
        CheckConstraint("confidence >= 0 AND confidence <= 1", name="confidence_range"),
        CheckConstraint("btrim(generator) <> ''", name="generator_nonempty"),
        CheckConstraint("btrim(generator_version) <> ''", name="generator_version_nonempty"),
        # v1 tag= filters (any/all); reverse lookup beyond the unique animal-first index.
        Index("ix_animal_tags_tag_key_animal_id", "tag_key", "animal_id"),
    )

    animal_id: Mapped[UUID] = mapped_column(ForeignKey("animals.id", ondelete="CASCADE"))
    tag_key: Mapped[str] = mapped_column(ForeignKey("tags.key", ondelete="RESTRICT"))
    confidence: Mapped[Decimal] = mapped_column(Numeric)
    evidence: Mapped[str | None] = mapped_column(Text)
    rule_id: Mapped[str | None] = mapped_column(Text)
    generator: Mapped[str] = mapped_column(Text)
    generator_version: Mapped[str] = mapped_column(Text)

    animal: Mapped[Animal] = relationship(back_populates="tag_assignments")
    tag: Mapped[Tag] = relationship(back_populates="animal_assignments")
