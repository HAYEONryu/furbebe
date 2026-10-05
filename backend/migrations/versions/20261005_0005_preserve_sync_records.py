"""Preserve obsolete sync records with explicit visibility flags."""

import sqlalchemy as sa
from alembic import op

revision = "20261005_0005"
down_revision = "20261003_0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    for table in ("animals", "animal_images", "animal_tags"):
        op.add_column(table, sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()))
    # Also enforce retirement on installations where the original 0004 ran.
    op.execute(sa.text("""
        UPDATE tags SET is_active = false WHERE key IN
        ('tiny', 'small', 'medium', 'large', 'puppy', 'young', 'adult', 'senior',
         'bean', 'cheese', 'baby_dog', 'senior_dog')
    """))


def downgrade() -> None:
    # Preserve activation state and evidence. Recovery uses a verified backup
    # or a reviewed roll-forward; never silently erase visibility metadata.
    raise RuntimeError("Data-preserving migration requires reviewed roll-forward recovery")
