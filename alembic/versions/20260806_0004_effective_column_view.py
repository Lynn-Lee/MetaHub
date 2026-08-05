"""create effective column view

Revision ID: 20260806_0004
Revises: 20260805_0003
Create Date: 2026-08-06
"""

from collections.abc import Sequence

from alembic import op

revision: str = "20260806_0004"
down_revision: str | None = "20260805_0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        """
        CREATE OR REPLACE VIEW v_column_effective AS
        SELECT
            c.urn,
            c.table_urn,
            c.column_name,
            c.ordinal,
            c.raw_type,
            c.logical_type,
            c.is_nullable,
            c.is_primary_key,
            c.raw_comment,
            c.is_deleted,
            t.db_name,
            t.table_name,
            t.table_comment,
            t.source_id,
            ca.business_meaning,
            ca.dict_id,
            ca.dict_inline,
            ca.sample_value,
            ca.usage_note,
            ca.status AS annotation_status,
            ca.source_type AS annotation_source,
            COALESCE(ca.logical_type_override, c.logical_type) AS effective_type,
            COALESCE(ca.domain_id, ta.domain_id) AS effective_domain_id,
            d.name AS domain_name,
            d.code AS domain_code,
            COALESCE(ca.owner_id, ta.owner_id) AS effective_owner_id
        FROM column_meta c
        JOIN table_meta t
            ON c.table_urn = t.urn
        LEFT JOIN asset_annotation ca
            ON ca.urn = c.urn
            AND ca.asset_type = 'COLUMN'
        LEFT JOIN asset_annotation ta
            ON ta.urn = c.table_urn
            AND ta.asset_type = 'TABLE'
        LEFT JOIN business_domain d
            ON d.id = COALESCE(ca.domain_id, ta.domain_id)
        """
    )


def downgrade() -> None:
    op.execute("DROP VIEW IF EXISTS v_column_effective")
