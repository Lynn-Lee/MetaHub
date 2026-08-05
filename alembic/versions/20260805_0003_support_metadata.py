"""create support metadata tables

Revision ID: 20260805_0003
Revises: 20260805_0002
Create Date: 2026-08-05
"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision: str = "20260805_0003"
down_revision: str | None = "20260805_0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "schema_change_log",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("urn", sa.String(length=768), nullable=False),
        sa.Column("table_urn", sa.String(length=512)),
        sa.Column("asset_type", sa.String(length=16)),
        sa.Column("change_type", sa.String(length=32), nullable=False),
        sa.Column("before_value", postgresql.JSONB()),
        sa.Column("after_value", postgresql.JSONB()),
        sa.Column("rename_candidate", sa.String(length=768)),
        sa.Column("rename_status", sa.String(length=16)),
        sa.Column("detected_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("idx_change_time", "schema_change_log", [sa.text("detected_at DESC")])
    op.create_index("idx_change_table", "schema_change_log", ["table_urn"])

    op.create_table(
        "sync_job_log",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("source_id", sa.BigInteger(), nullable=False),
        sa.Column("trigger_type", sa.String(length=16)),
        sa.Column("status", sa.String(length=16)),
        sa.Column("scanned_tables", sa.Integer(), server_default=sa.text("0")),
        sa.Column("changed_count", sa.Integer(), server_default=sa.text("0")),
        sa.Column("fail_count", sa.Integer(), server_default=sa.text("0")),
        sa.Column("comment_fill_rate", sa.Numeric(5, 2)),
        sa.Column("error_msg", sa.Text()),
        sa.Column("started_at", sa.DateTime(timezone=True)),
        sa.Column("finished_at", sa.DateTime(timezone=True)),
        sa.Column("duration_ms", sa.BigInteger()),
    )

    op.create_table(
        "sync_fail_detail",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("job_id", sa.BigInteger(), sa.ForeignKey("sync_job_log.id"), nullable=False),
        sa.Column("source_id", sa.BigInteger(), nullable=False),
        sa.Column("db_name", sa.String(length=128)),
        sa.Column("table_name", sa.String(length=128)),
        sa.Column("stage", sa.String(length=32)),
        sa.Column("error_type", sa.String(length=64)),
        sa.Column("error_msg", sa.Text()),
        sa.Column("retry_count", sa.Integer(), server_default=sa.text("0")),
        sa.Column("resolved", sa.Boolean(), server_default=sa.text("false")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("idx_fail_job", "sync_fail_detail", ["job_id", "resolved"])

    op.create_table(
        "view_log",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("user_id", sa.BigInteger()),
        sa.Column("urn", sa.String(length=768), nullable=False),
        sa.Column("asset_type", sa.String(length=16)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("idx_view_urn", "view_log", ["urn", sa.text("created_at DESC")])
    op.create_index("idx_view_user", "view_log", ["user_id", sa.text("created_at DESC")])

    op.create_table(
        "search_log",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("user_id", sa.BigInteger()),
        sa.Column("keyword", sa.String(length=255)),
        sa.Column("result_cnt", sa.Integer()),
        sa.Column("search_type", sa.String(length=16), server_default="KEYWORD"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("idx_search_kw", "search_log", ["keyword", sa.text("created_at DESC")])

    op.create_table(
        "search_click",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("search_id", sa.BigInteger(), sa.ForeignKey("search_log.id"), nullable=False),
        sa.Column("urn", sa.String(length=768), nullable=False),
        sa.Column("rank", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("idx_click_search", "search_click", ["search_id"])

    op.create_table(
        "annotation_todo",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("urn", sa.String(length=768), nullable=False),
        sa.Column("todo_type", sa.String(length=32), nullable=False),
        sa.Column("domain_id", sa.BigInteger()),
        sa.Column("assignee_id", sa.BigInteger()),
        sa.Column("priority", sa.Integer(), server_default=sa.text("0")),
        sa.Column("status", sa.String(length=16), server_default="OPEN"),
        sa.Column("payload", postgresql.JSONB()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("done_at", sa.DateTime(timezone=True)),
    )
    op.create_index(
        "uq_todo_open",
        "annotation_todo",
        ["urn", "todo_type"],
        unique=True,
        postgresql_where=sa.text("status = 'OPEN'"),
    )
    op.create_index("idx_todo_assignee", "annotation_todo", ["assignee_id", "status"])
    op.create_index("idx_todo_domain", "annotation_todo", ["domain_id", "status"])

    op.create_table(
        "sys_user",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("username", sa.String(length=64), nullable=False, unique=True),
        sa.Column("real_name", sa.String(length=64)),
        sa.Column("email", sa.String(length=128)),
        sa.Column("enabled", sa.Boolean(), server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "user_role",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("role", sa.String(length=32), nullable=False),
        sa.Column("domain_id", sa.BigInteger()),
        sa.UniqueConstraint("user_id", "role", "domain_id", name="uq_user_role_scope"),
    )

    op.create_table(
        "api_key",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("key_name", sa.String(length=128), nullable=False),
        sa.Column("key_hash", sa.String(length=128), nullable=False, unique=True),
        sa.Column("scopes", postgresql.JSONB(), server_default=sa.text("'[\"read\"]'::jsonb")),
        sa.Column("rate_limit", sa.Integer(), server_default=sa.text("1000")),
        sa.Column("enabled", sa.Boolean(), server_default=sa.text("true")),
        sa.Column("expires_at", sa.DateTime(timezone=True)),
        sa.Column("created_by", sa.BigInteger()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "user_favorite",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("urn", sa.String(length=768), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint("user_id", "urn", name="uq_user_favorite_user_id_urn"),
    )

    op.create_table(
        "feedback",
        sa.Column("id", sa.BigInteger(), primary_key=True),
        sa.Column("urn", sa.String(length=768), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=16), server_default="OPEN"),
        sa.Column("reporter_id", sa.BigInteger()),
        sa.Column("handler_id", sa.BigInteger()),
        sa.Column("handled_at", sa.DateTime(timezone=True)),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table("feedback")
    op.drop_table("user_favorite")
    op.drop_table("api_key")
    op.drop_table("user_role")
    op.drop_table("sys_user")
    op.drop_index("idx_todo_domain", table_name="annotation_todo")
    op.drop_index("idx_todo_assignee", table_name="annotation_todo")
    op.drop_index("uq_todo_open", table_name="annotation_todo")
    op.drop_table("annotation_todo")
    op.drop_index("idx_click_search", table_name="search_click")
    op.drop_table("search_click")
    op.drop_index("idx_search_kw", table_name="search_log")
    op.drop_table("search_log")
    op.drop_index("idx_view_user", table_name="view_log")
    op.drop_index("idx_view_urn", table_name="view_log")
    op.drop_table("view_log")
    op.drop_index("idx_fail_job", table_name="sync_fail_detail")
    op.drop_table("sync_fail_detail")
    op.drop_table("sync_job_log")
    op.drop_index("idx_change_table", table_name="schema_change_log")
    op.drop_index("idx_change_time", table_name="schema_change_log")
    op.drop_table("schema_change_log")
