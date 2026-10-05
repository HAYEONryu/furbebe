"""Use white (흰둥이) as the canonical white-color tag; archive cloud."""

import sqlalchemy as sa
from alembic import op

revision = "20261003_0003"
down_revision = "20261003_0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Ensure cloud-only installations also have a canonical dictionary entry.
    op.execute(
        sa.text("""
        INSERT INTO tags (key, type, label, emoji, description, display_order)
        SELECT 'white', 'fact', '흰둥이', '🤍', '등록된 털색이 흰색인 친구예요.', 8
        WHERE EXISTS (SELECT 1 FROM tags WHERE key IN ('white', 'cloud'))
        ON CONFLICT (key) DO UPDATE SET
            label = EXCLUDED.label, emoji = EXCLUDED.emoji,
            description = EXCLUDED.description, updated_at = now()
    """)
    )
    # Preserve cloud-only associations under white, retaining evidence and ownership.
    # Existing white associations win; no animal-tag history is deleted.
    op.execute(
        sa.text("""
        INSERT INTO animal_tags
            (id, animal_id, tag_key, confidence, evidence, rule_id,
             generator, generator_version, created_at)
        SELECT gen_random_uuid(), animal_id, 'white', confidence, evidence, rule_id,
               generator, generator_version, created_at
        FROM animal_tags WHERE tag_key = 'cloud'
        ON CONFLICT (animal_id, tag_key, generator, generator_version) DO NOTHING
    """)
    )
    op.execute(
        sa.text("""
        UPDATE tags SET label = '흰둥이', emoji = '🤍', is_active = false,
            description = '흰둥이(white)로 통합된 이전 태그', updated_at = now()
        WHERE key = 'cloud'
    """)
    )


def downgrade() -> None:
    # Data-preserving consolidation cannot infer which white assignments predated it.
    pass
