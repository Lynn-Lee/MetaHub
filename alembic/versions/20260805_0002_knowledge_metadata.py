"""create knowledge metadata tables

Revision ID: 20260805_0002
Revises: 20260805_0001
Create Date: 2026-08-05
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "20260805_0002"
down_revision: str | None = "20260805_0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "business_domain",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("parent_id", sa.BigInteger(), sa.ForeignKey("business_domain.id")),
        sa.Column("code", sa.String(length=64), nullable=False, unique=True),
        sa.Column("name", sa.String(length=128), nullable=False),
        sa.Column("description", sa.Text()),
        sa.Column("owner_id", sa.BigInteger()),
        sa.Column("sort_order", sa.Integer(), server_default=sa.text("0")),
        sa.Column("enabled", sa.Boolean(), server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "domain_rule",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column(
            "domain_id",
            sa.BigInteger(),
            sa.ForeignKey("business_domain.id"),
            nullable=False,
        ),
        sa.Column("source_id", sa.BigInteger()),
        sa.Column("db_pattern", sa.String(length=128)),
        sa.Column("table_pattern", sa.String(length=128)),
        sa.Column("priority", sa.Integer(), server_default=sa.text("0")),
        sa.Column("enabled", sa.Boolean(), server_default=sa.text("true")),
    )

    op.create_table(
        "tag",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("category", sa.String(length=64), nullable=False),
        sa.Column("code", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=128), nullable=False),
        sa.Column("description", sa.Text()),
        sa.Column("color", sa.String(length=16)),
        sa.Column("exclusive", sa.Boolean(), server_default=sa.text("false")),
        sa.Column("enabled", sa.Boolean(), server_default=sa.text("true")),
        sa.UniqueConstraint("category", "code", name="uq_tag_category_code"),
    )

    op.create_table(
        "dict",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("code", sa.String(length=64), nullable=False, unique=True),
        sa.Column("name", sa.String(length=128), nullable=False),
        sa.Column("description", sa.Text()),
        sa.Column("items", postgresql.JSONB(), nullable=False),
        sa.Column("source_type", sa.String(length=16), server_default="MANUAL"),
        sa.Column("version", sa.Integer(), server_default=sa.text("1")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "asset_annotation",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("urn", sa.String(length=768), nullable=False, unique=True),
        sa.Column("asset_type", sa.String(length=16), nullable=False),
        sa.Column("domain_id", sa.BigInteger(), sa.ForeignKey("business_domain.id")),
        sa.Column("business_meaning", sa.Text()),
        sa.Column("logical_type_override", sa.String(length=32)),
        sa.Column("dict_id", sa.BigInteger(), sa.ForeignKey("dict.id")),
        sa.Column("dict_inline", postgresql.JSONB()),
        sa.Column("sample_value", sa.Text()),
        sa.Column("source_desc", sa.Text()),
        sa.Column("usage_note", sa.Text()),
        sa.Column("owner_id", sa.BigInteger()),
        sa.Column("lifecycle", sa.String(length=16), server_default="ACTIVE"),
        sa.Column("status", sa.String(length=16), server_default="CONFIRMED"),
        sa.Column("source_type", sa.String(length=16), server_default="MANUAL"),
        sa.Column("inherited_from", sa.String(length=768)),
        sa.Column(
            "search_text",
            sa.Text(),
            sa.Computed(
                "coalesce(business_meaning,'') || ' ' || "
                "coalesce(usage_note,'') || ' ' || "
                "coalesce(source_desc,'')",
                persisted=True,
            ),
        ),
        sa.Column("created_by", sa.BigInteger()),
        sa.Column("updated_by", sa.BigInteger()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("idx_annotation_domain", "asset_annotation", ["domain_id"])
    op.create_index("idx_annotation_status", "asset_annotation", ["status", "source_type"])
    op.create_index(
        "idx_annotation_search_trgm",
        "asset_annotation",
        ["search_text"],
        postgresql_using="gin",
        postgresql_ops={"search_text": "gin_trgm_ops"},
    )

    op.create_table(
        "asset_tag_rel",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("urn", sa.String(length=768), nullable=False),
        sa.Column("tag_id", sa.BigInteger(), sa.ForeignKey("tag.id"), nullable=False),
        sa.Column("created_by", sa.BigInteger()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("urn", "tag_id", name="uq_asset_tag_rel_urn_tag_id"),
    )
    op.create_index("idx_asset_tag_tag", "asset_tag_rel", ["tag_id"])

    op.create_table(
        "annotation_history",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("urn", sa.String(length=768), nullable=False),
        sa.Column("before_data", postgresql.JSONB()),
        sa.Column("after_data", postgresql.JSONB()),
        sa.Column("operator_id", sa.BigInteger()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("idx_anno_hist_urn", "annotation_history", ["urn", "created_at"])

    op.create_table(
        "common_column_blacklist",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("column_name", sa.String(length=128), nullable=False, unique=True),
        sa.Column("reason", sa.Text()),
        sa.Column("is_whitelist", sa.Boolean(), server_default=sa.text("false")),
        sa.Column("created_by", sa.BigInteger()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table("common_column_blacklist")
    op.drop_index("idx_anno_hist_urn", table_name="annotation_history")
    op.drop_table("annotation_history")
    op.drop_index("idx_asset_tag_tag", table_name="asset_tag_rel")
    op.drop_table("asset_tag_rel")
    op.drop_index("idx_annotation_search_trgm", table_name="asset_annotation")
    op.drop_index("idx_annotation_status", table_name="asset_annotation")
    op.drop_index("idx_annotation_domain", table_name="asset_annotation")
    op.drop_table("asset_annotation")
    op.drop_table("dict")
    op.drop_table("tag")
    op.drop_table("domain_rule")
    op.drop_table("business_domain")
