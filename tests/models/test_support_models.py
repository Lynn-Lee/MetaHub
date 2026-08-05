from sqlalchemy import ForeignKeyConstraint, Index

import app.models  # noqa: F401 - imports model modules into Base.metadata
from app.db.base import SUPPORT_TABLES, Base


def test_support_tables_are_registered() -> None:
    expected = {
        "schema_change_log",
        "sync_job_log",
        "sync_fail_detail",
        "view_log",
        "search_log",
        "search_click",
        "annotation_todo",
        "sys_user",
        "user_role",
        "api_key",
        "user_favorite",
        "feedback",
    }

    assert expected.issubset(Base.metadata.tables)
    assert expected.issubset(SUPPORT_TABLES)


def test_annotation_todo_open_unique_index_contract() -> None:
    table = Base.metadata.tables["annotation_todo"]
    indexes = {index.name: index for index in table.indexes if isinstance(index, Index)}

    open_index = indexes["uq_todo_open"]

    assert open_index.unique is True
    assert tuple(open_index.columns.keys()) == ("urn", "todo_type")
    assert str(open_index.dialect_options["postgresql"]["where"]) == "status = 'OPEN'"


def test_sync_fail_detail_references_job_log() -> None:
    table = Base.metadata.tables["sync_fail_detail"]
    foreign_keys = [
        constraint
        for constraint in table.constraints
        if isinstance(constraint, ForeignKeyConstraint)
    ]

    assert any(fk.referred_table.name == "sync_job_log" for fk in foreign_keys)
    assert table.c.resolved.default is not None
    assert table.c.retry_count.default is not None


def test_search_click_references_search_log_and_keeps_rank() -> None:
    table = Base.metadata.tables["search_click"]
    foreign_keys = [
        constraint
        for constraint in table.constraints
        if isinstance(constraint, ForeignKeyConstraint)
    ]

    assert any(fk.referred_table.name == "search_log" for fk in foreign_keys)
    assert table.c.urn.nullable is False
    assert table.c.rank.nullable is False
