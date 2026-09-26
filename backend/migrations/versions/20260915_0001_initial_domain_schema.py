"""initial domain schema

Revision ID: 20260915_0001
Revises: base

Reviewed initial schema. No seed data, extensions, triggers, or derived group columns.
Keep this revision independent of mutable ORM metadata.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260915_0001"
down_revision: str | Sequence[str] | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Create referenced tables before their children.
    op.create_table(
        "shelters",
        sa.Column("source", sa.Text(), nullable=False),
        sa.Column("source_id", sa.Text(), nullable=False),
        sa.Column("name", sa.Text(), nullable=True),
        sa.Column("phone", sa.Text(), nullable=True),
        sa.Column("address", sa.Text(), nullable=True),
        sa.Column("owner_name", sa.Text(), nullable=True),
        sa.Column("organization", sa.Text(), nullable=True),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint("btrim(source) <> ''", name=op.f("ck_shelters_source_nonempty")),
        sa.CheckConstraint("btrim(source_id) <> ''", name=op.f("ck_shelters_source_id_nonempty")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_shelters")),
        sa.UniqueConstraint("source", "source_id", name="uq_shelters_source_source_id"),
    )
    op.create_table(
        "sync_runs",
        sa.Column("source", sa.Text(), nullable=False),
        sa.Column(
            "started_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("status", sa.Text(), server_default="running", nullable=False),
        sa.Column("page_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("received_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("inserted_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("updated_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("error_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint("btrim(source) <> ''", name=op.f("ck_sync_runs_source_nonempty")),
        sa.CheckConstraint(
            "status IN ('running', 'success', 'failed')", name=op.f("ck_sync_runs_status_values")
        ),
        sa.CheckConstraint(
            "finished_at >= started_at", name=op.f("ck_sync_runs_finish_after_start")
        ),
        sa.CheckConstraint(
            "page_count >= 0 AND received_count >= 0 AND inserted_count >= 0 AND updated_count >= 0 AND error_count >= 0",
            name=op.f("ck_sync_runs_counts_nonnegative"),
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_sync_runs")),
    )
    op.create_table(
        "tags",
        sa.Column("key", sa.Text(), nullable=False),
        sa.Column("type", sa.Text(), nullable=False),
        sa.Column("label", sa.Text(), nullable=False),
        sa.Column("emoji", sa.Text(), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("display_order", sa.Integer(), server_default="0", nullable=False),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint("btrim(key) <> ''", name=op.f("ck_tags_key_nonempty")),
        sa.CheckConstraint("type IN ('fact', 'trait', 'vibe')", name=op.f("ck_tags_type_values")),
        sa.CheckConstraint("display_order >= 0", name=op.f("ck_tags_display_order_nonnegative")),
        sa.PrimaryKeyConstraint("key", name=op.f("pk_tags")),
    )
    op.create_table(
        "animals",
        sa.Column("source", sa.Text(), nullable=False),
        sa.Column("source_id", sa.Text(), nullable=False),
        sa.Column("notice_no", sa.Text(), nullable=True),
        sa.Column("rfid_code", sa.Text(), nullable=True),
        sa.Column("species", sa.Text(), nullable=True),
        sa.Column("breed", sa.Text(), nullable=True),
        sa.Column("breed_full", sa.Text(), nullable=True),
        sa.Column("sex", sa.Text(), nullable=True),
        sa.Column("neutered", sa.Text(), nullable=True),
        sa.Column("age_text", sa.Text(), nullable=True),
        sa.Column("birth_year", sa.Integer(), nullable=True),
        sa.Column("weight_text", sa.Text(), nullable=True),
        sa.Column("weight_kg", sa.Numeric(), nullable=True),
        sa.Column("color_text", sa.Text(), nullable=True),
        sa.Column("found_date", sa.Date(), nullable=True),
        sa.Column("found_place", sa.Text(), nullable=True),
        sa.Column("process_state", sa.Text(), nullable=True),
        sa.Column("end_reason", sa.Text(), nullable=True),
        sa.Column("notice_start", sa.Date(), nullable=True),
        sa.Column("notice_end", sa.Date(), nullable=True),
        sa.Column("special_mark", sa.Text(), nullable=True),
        sa.Column("social_text", sa.Text(), nullable=True),
        sa.Column("health_text", sa.Text(), nullable=True),
        sa.Column("etc_text", sa.Text(), nullable=True),
        sa.Column("vaccination_text", sa.Text(), nullable=True),
        sa.Column("health_check_text", sa.Text(), nullable=True),
        sa.Column("shelter_id", sa.Uuid(), nullable=True),
        sa.Column(
            "raw_payload",
            postgresql.JSONB(none_as_null=True, astext_type=sa.Text()),
            nullable=False,
        ),
        sa.Column(
            "first_seen_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "last_seen_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("source_updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint("btrim(source) <> ''", name=op.f("ck_animals_source_nonempty")),
        sa.CheckConstraint("btrim(source_id) <> ''", name=op.f("ck_animals_source_id_nonempty")),
        sa.CheckConstraint(
            "jsonb_typeof(raw_payload) = 'object'", name=op.f("ck_animals_raw_payload_object")
        ),
        sa.CheckConstraint(
            "neutered IN ('yes', 'no', 'unknown')", name=op.f("ck_animals_neutered_values")
        ),
        sa.CheckConstraint(
            "sex IN ('male', 'female', 'unknown')", name=op.f("ck_animals_sex_values")
        ),
        sa.CheckConstraint(
            "weight_kg >= 0 AND weight_kg < 'Infinity'::numeric",
            name=op.f("ck_animals_weight_kg_finite_nonnegative"),
        ),
        sa.CheckConstraint(
            "birth_year BETWEEN 1 AND 9999", name=op.f("ck_animals_birth_year_range")
        ),
        sa.ForeignKeyConstraint(
            ["shelter_id"],
            ["shelters.id"],
            name=op.f("fk_animals_shelter_id_shelters"),
            ondelete="RESTRICT",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_animals")),
        sa.UniqueConstraint("source", "source_id", name="uq_animals_source_source_id"),
    )
    op.create_index("ix_animals_birth_year", "animals", ["birth_year"], unique=False)
    op.create_index("ix_animals_breed", "animals", ["breed"], unique=False)
    op.create_index("ix_animals_found_date", "animals", ["found_date"], unique=False)
    op.create_index("ix_animals_notice_end", "animals", ["notice_end"], unique=False)
    op.create_index("ix_animals_process_state", "animals", ["process_state"], unique=False)
    op.create_index("ix_animals_sex", "animals", ["sex"], unique=False)
    op.create_index("ix_animals_shelter_id", "animals", ["shelter_id"], unique=False)
    op.create_index("ix_animals_weight_kg", "animals", ["weight_kg"], unique=False)
    op.create_table(
        "animal_images",
        sa.Column("animal_id", sa.Uuid(), nullable=False),
        sa.Column("image_url", sa.Text(), nullable=False),
        sa.Column("sort_order", sa.Integer(), server_default="0", nullable=False),
        sa.Column("image_type", sa.Text(), nullable=True),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "btrim(image_url) <> ''", name=op.f("ck_animal_images_image_url_nonempty")
        ),
        sa.CheckConstraint("sort_order >= 0", name=op.f("ck_animal_images_sort_order_nonnegative")),
        sa.ForeignKeyConstraint(
            ["animal_id"],
            ["animals.id"],
            name=op.f("fk_animal_images_animal_id_animals"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_animal_images")),
        sa.UniqueConstraint("animal_id", "image_url", name="uq_animal_images_animal_id_image_url"),
    )
    op.create_index(
        "ix_animal_images_animal_id_sort_order",
        "animal_images",
        ["animal_id", "sort_order"],
        unique=False,
    )
    op.create_table(
        "animal_tags",
        sa.Column("animal_id", sa.Uuid(), nullable=False),
        sa.Column("tag_key", sa.Text(), nullable=False),
        sa.Column("confidence", sa.Numeric(), nullable=False),
        sa.Column("evidence", sa.Text(), nullable=True),
        sa.Column("rule_id", sa.Text(), nullable=True),
        sa.Column("generator", sa.Text(), nullable=False),
        sa.Column("generator_version", sa.Text(), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "btrim(generator) <> ''", name=op.f("ck_animal_tags_generator_nonempty")
        ),
        sa.CheckConstraint(
            "btrim(generator_version) <> ''", name=op.f("ck_animal_tags_generator_version_nonempty")
        ),
        sa.CheckConstraint(
            "confidence >= 0 AND confidence <= 1", name=op.f("ck_animal_tags_confidence_range")
        ),
        sa.ForeignKeyConstraint(
            ["animal_id"],
            ["animals.id"],
            name=op.f("fk_animal_tags_animal_id_animals"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["tag_key"], ["tags.key"], name=op.f("fk_animal_tags_tag_key_tags"), ondelete="RESTRICT"
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_animal_tags")),
        sa.UniqueConstraint(
            "animal_id",
            "tag_key",
            "generator",
            "generator_version",
            name="uq_animal_tags_animal_tag_generator_version",
        ),
    )
    op.create_index(
        "ix_animal_tags_tag_key_animal_id", "animal_tags", ["tag_key", "animal_id"], unique=False
    )


def downgrade() -> None:
    # Destructive rollback: drop children first, then their referenced tables.
    op.drop_index("ix_animal_tags_tag_key_animal_id", table_name="animal_tags")
    op.drop_table("animal_tags")
    op.drop_index("ix_animal_images_animal_id_sort_order", table_name="animal_images")
    op.drop_table("animal_images")
    op.drop_index("ix_animals_weight_kg", table_name="animals")
    op.drop_index("ix_animals_shelter_id", table_name="animals")
    op.drop_index("ix_animals_sex", table_name="animals")
    op.drop_index("ix_animals_process_state", table_name="animals")
    op.drop_index("ix_animals_notice_end", table_name="animals")
    op.drop_index("ix_animals_found_date", table_name="animals")
    op.drop_index("ix_animals_breed", table_name="animals")
    op.drop_index("ix_animals_birth_year", table_name="animals")
    op.drop_table("animals")
    op.drop_table("tags")
    op.drop_table("sync_runs")
    op.drop_table("shelters")
