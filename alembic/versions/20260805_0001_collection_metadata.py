"""create collection metadata tables

Revision ID: 20260805_0001
Revises:
Create Date: 2026-08-05
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "20260805_0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")

    op.create_table(
        "data_source",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("code", sa.String(length=64), nullable=False, unique=True),
        sa.Column("name", sa.String(length=128), nullable=False),
        sa.Column("db_type", sa.String(length=32), nullable=False),
        sa.Column("env", sa.String(length=16), nullable=False),
        sa.Column("host", sa.String(length=255), nullable=False),
        sa.Column("port", sa.Integer(), nullable=False),
        sa.Column("default_db", sa.String(length=128)),
        sa.Column("username", sa.String(length=128), nullable=False),
        sa.Column("password_cipher", sa.Text(), nullable=False),
        sa.Column("include_rules", postgresql.JSONB(), server_default=sa.text("'[]'::jsonb")),
        sa.Column("exclude_rules", postgresql.JSONB(), server_default=sa.text("'[]'::jsonb")),
        sa.Column("sync_cron", sa.String(length=64), server_default="0 2 * * *"),
        sa.Column("group_name", sa.String(length=64)),
        sa.Column("enabled", sa.Boolean(), server_default=sa.text("true")),
        sa.Column("last_sync_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "table_meta",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("urn", sa.String(length=512), nullable=False, unique=True),
        sa.Column("source_id", sa.BigInteger(), sa.ForeignKey("data_source.id"), nullable=False),
        sa.Column("db_name", sa.String(length=128), nullable=False),
        sa.Column("table_name", sa.String(length=128), nullable=False),
        sa.Column("table_type", sa.String(length=32), server_default="TABLE"),
        sa.Column("table_comment", sa.Text()),
        sa.Column("engine", sa.String(length=32)),
        sa.Column("row_count", sa.BigInteger()),
        sa.Column("data_size", sa.BigInteger()),
        sa.Column("db_created_at", sa.DateTime(timezone=True)),
        sa.Column("dw_layer", sa.String(length=16)),
        sa.Column("partition_keys", postgresql.JSONB()),
        sa.Column("distribution_keys", postgresql.JSONB()),
        sa.Column("sort_keys", postgresql.JSONB()),
        sa.Column("storage_format", sa.String(length=32)),
        sa.Column("table_model", sa.String(length=32)),
        sa.Column("is_deleted", sa.Boolean(), server_default=sa.text("false")),
        sa.Column("deleted_at", sa.DateTime(timezone=True)),
        sa.Column("synced_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column(
            "search_text",
            sa.Text(),
            sa.Computed(
                "coalesce(table_name,'') || ' ' || coalesce(table_comment,'')", persisted=True
            ),
        ),
    )
    op.create_index("idx_table_meta_source", "table_meta", ["source_id", "db_name"])
    op.create_index("idx_table_meta_name", "table_meta", ["table_name"])
    op.create_index(
        "idx_table_meta_search_trgm",
        "table_meta",
        ["search_text"],
        postgresql_using="gin",
        postgresql_ops={"search_text": "gin_trgm_ops"},
    )

    op.create_table(
        "column_meta",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("urn", sa.String(length=768), nullable=False, unique=True),
        sa.Column("table_urn", sa.String(length=512), nullable=False),
        sa.Column("column_name", sa.String(length=128), nullable=False),
        sa.Column("ordinal", sa.Integer(), nullable=False),
        sa.Column("raw_type", sa.String(length=128), nullable=False),
        sa.Column("logical_type", sa.String(length=32), nullable=False),
        sa.Column("data_length", sa.Integer()),
        sa.Column("num_precision", sa.Integer()),
        sa.Column("num_scale", sa.Integer()),
        sa.Column("is_nullable", sa.Boolean(), server_default=sa.text("true")),
        sa.Column("default_value", sa.Text()),
        sa.Column("raw_comment", sa.Text()),
        sa.Column("is_primary_key", sa.Boolean(), server_default=sa.text("false")),
        sa.Column("is_auto_incr", sa.Boolean(), server_default=sa.text("false")),
        sa.Column("is_unique", sa.Boolean(), server_default=sa.text("false")),
        sa.Column("is_partition_key", sa.Boolean(), server_default=sa.text("false")),
        sa.Column("is_deleted", sa.Boolean(), server_default=sa.text("false")),
        sa.Column("deleted_at", sa.DateTime(timezone=True)),
        sa.Column("synced_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column(
            "search_text",
            sa.Text(),
            sa.Computed(
                "coalesce(column_name,'') || ' ' || coalesce(raw_comment,'')", persisted=True
            ),
        ),
    )
    op.create_index("idx_column_meta_table", "column_meta", ["table_urn"])
    op.create_index("idx_column_meta_name", "column_meta", ["column_name", "logical_type"])
    op.create_index(
        "idx_column_meta_search_trgm",
        "column_meta",
        ["search_text"],
        postgresql_using="gin",
        postgresql_ops={"search_text": "gin_trgm_ops"},
    )

    op.create_table(
        "index_meta",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("table_urn", sa.String(length=512), nullable=False),
        sa.Column("index_name", sa.String(length=128), nullable=False),
        sa.Column("index_type", sa.String(length=32)),
        sa.Column("columns", postgresql.JSONB(), nullable=False),
        sa.Column("synced_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("table_urn", "index_name", name="uq_index_meta_table_urn_index_name"),
    )


def downgrade() -> None:
    op.drop_table("index_meta")
    op.drop_index("idx_column_meta_search_trgm", table_name="column_meta")
    op.drop_index("idx_column_meta_name", table_name="column_meta")
    op.drop_index("idx_column_meta_table", table_name="column_meta")
    op.drop_table("column_meta")
    op.drop_index("idx_table_meta_search_trgm", table_name="table_meta")
    op.drop_index("idx_table_meta_name", table_name="table_meta")
    op.drop_index("idx_table_meta_source", table_name="table_meta")
    op.drop_table("table_meta")
    op.drop_table("data_source")
