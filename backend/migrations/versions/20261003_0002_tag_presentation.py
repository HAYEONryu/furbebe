"""Backfill known tag display names and meaning-specific emojis.

This data-only revision preserves custom tags and animal assignments.
"""

import sqlalchemy as sa
from alembic import op

revision = "20261003_0002"
down_revision = "20260915_0001"
branch_labels = None
depends_on = None

# Frozen snapshot: migrations must not import the mutable generator catalog.
PRESENTATION = {
    "tiny": ("5kg 이하", "🐾"),
    "small": ("5kg 초과~10kg", "🐕"),
    "medium": ("10kg 초과~20kg", "🦮"),
    "large": ("20kg 초과", "🐕\u200d🦺"),
    "puppy": ("추정 1세 이하", "🐣"),
    "young": ("추정 2~4세", "🌱"),
    "adult": ("추정 5~9세", "🌳"),
    "senior": ("추정 10세 이상", "👴"),
    "white": ("흰둥이", "🤍"),
    "cream": ("크림이", "🍦"),
    "black": ("검둥이", "🖤"),
    "brown": ("브라운", "🤎"),
    "bean": ("콩만이", "🫘"),
    "cheese": ("치즈", "🧀"),
    "cloud": ("뭉개 구름이", "☁️"),
    "baby_dog": ("아가댕", "🐣"),
    "senior_dog": ("어르신댕", "👴"),
    "gentle": ("순딩이", "🙂"),
    "shy": ("소심요정", "🧚"),
    "playful": ("똥꼬발랄", "🤸"),
    "calm": ("차분선비댕", "🍵"),
    "people_friendly": ("사람좋아", "🥰"),
}


def upgrade() -> None:
    tags = sa.table(
        "tags", sa.column("key", sa.Text), sa.column("label", sa.Text), sa.column("emoji", sa.Text)
    )
    for key, (label, emoji) in PRESENTATION.items():
        op.execute(tags.update().where(tags.c.key == key).values(label=label, emoji=emoji))


def downgrade() -> None:
    # Previous installations can have different custom labels/emojis; do not erase them
    # with an assumed inverse. This revision changes no schema.
    pass
