from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, Integer, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from .base import Base, CreatedAt, UUIDPrimaryKey, utc_now


class SyncRun(UUIDPrimaryKey, CreatedAt, Base):
    __tablename__ = "sync_runs"
    __table_args__ = (
        CheckConstraint("btrim(source) <> ''", name="source_nonempty"),
        CheckConstraint("status IN ('running', 'success', 'failed')", name="status_values"),
        CheckConstraint(
            "page_count >= 0 AND received_count >= 0 AND inserted_count >= 0 "
            "AND updated_count >= 0 AND error_count >= 0",
            name="counts_nonnegative",
        ),
        CheckConstraint("finished_at >= started_at", name="finish_after_start"),
    )

    source: Mapped[str] = mapped_column(Text)
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, server_default=func.now()
    )
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    status: Mapped[str] = mapped_column(Text, default="running", server_default="running")
    page_count: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    received_count: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    inserted_count: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    updated_count: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    error_count: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    error_message: Mapped[str | None] = mapped_column(Text)
