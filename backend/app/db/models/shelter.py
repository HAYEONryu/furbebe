from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import Base, Timestamps, UUIDPrimaryKey

if TYPE_CHECKING:
    from .animal import Animal


class Shelter(UUIDPrimaryKey, Timestamps, Base):
    __tablename__ = "shelters"
    __table_args__ = (
        UniqueConstraint("source", "source_id", name="uq_shelters_source_source_id"),
        CheckConstraint("btrim(source) <> ''", name="source_nonempty"),
        CheckConstraint("btrim(source_id) <> ''", name="source_id_nonempty"),
    )

    source: Mapped[str] = mapped_column(Text)
    source_id: Mapped[str] = mapped_column(Text)
    name: Mapped[str | None] = mapped_column(Text)
    phone: Mapped[str | None] = mapped_column(Text)
    address: Mapped[str | None] = mapped_column(Text)
    owner_name: Mapped[str | None] = mapped_column(Text)
    organization: Mapped[str | None] = mapped_column(Text)

    # Do not null out references when a loaded shelter is deleted: let RESTRICT act.
    animals: Mapped[list[Animal]] = relationship(back_populates="shelter", passive_deletes="all")
