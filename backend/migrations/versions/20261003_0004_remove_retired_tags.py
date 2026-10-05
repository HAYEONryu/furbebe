"""Deactivate retired tags without deleting assignments or evidence."""

import sqlalchemy as sa
from alembic import op

revision = "20261003_0004"
down_revision = "20261003_0003"
branch_labels = None
depends_on = None

RETIRED_KEYS = (
    "tiny", "small", "medium", "large", "puppy", "young", "adult", "senior",
    "bean", "cheese", "baby_dog", "senior_dog",
)


def upgrade() -> None:
    # Use the same advisory lock as sync to prevent concurrent tag recreation.
    op.execute(sa.text("SELECT pg_advisory_xact_lock(1179996738, 1)"))
    tags = sa.table("tags", sa.column("key", sa.Text), sa.column("is_active", sa.Boolean))
    op.execute(tags.update().where(tags.c.key.in_(RETIRED_KEYS)).values(is_active=False))


def downgrade() -> None:
    # Do not reactivate tags without knowing their previous activation state.
    pass
