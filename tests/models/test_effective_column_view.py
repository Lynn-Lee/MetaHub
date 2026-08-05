from pathlib import Path

MIGRATION = Path("alembic/versions/20260806_0004_effective_column_view.py")


def test_effective_column_view_migration_contract() -> None:
    assert MIGRATION.exists()

    migration_sql = MIGRATION.read_text(encoding="utf-8").lower()

    assert "create or replace view v_column_effective as" in migration_sql
    assert "coalesce(ca.domain_id, ta.domain_id)" in migration_sql
    assert "coalesce(ca.owner_id, ta.owner_id)" in migration_sql
    assert "c.is_deleted" in migration_sql
    assert "where c.is_deleted" not in migration_sql
    assert "where not c.is_deleted" not in migration_sql
