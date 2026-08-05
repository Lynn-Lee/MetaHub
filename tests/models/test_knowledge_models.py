from sqlalchemy import Computed, UniqueConstraint

import app.models  # noqa: F401 - imports model modules into Base.metadata
from app.db.base import KNOWLEDGE_TABLES, Base


def test_knowledge_tables_are_registered() -> None:
    expected = {
        "business_domain",
        "domain_rule",
        "tag",
        "dict",
        "asset_annotation",
        "asset_tag_rel",
        "annotation_history",
        "common_column_blacklist",
    }

    assert expected.issubset(Base.metadata.tables)
    assert expected.issubset(KNOWLEDGE_TABLES)


def test_asset_annotation_search_text_is_generated() -> None:
    column = Base.metadata.tables["asset_annotation"].c.search_text

    assert isinstance(column.computed, Computed)
    sqltext = str(column.computed.sqltext)
    assert "business_meaning" in sqltext
    assert "usage_note" in sqltext
    assert "source_desc" in sqltext


def test_asset_annotation_contract() -> None:
    table = Base.metadata.tables["asset_annotation"]

    assert table.c.urn.unique is True
    assert table.c.asset_type.nullable is False
    assert table.c.lifecycle.default is not None
    assert table.c.status.default is not None
    assert table.c.source_type.default is not None


def test_tag_and_blacklist_uniqueness_contracts() -> None:
    tag = Base.metadata.tables["tag"]
    tag_constraints = {
        tuple(constraint.columns.keys())
        for constraint in tag.constraints
        if isinstance(constraint, UniqueConstraint)
    }

    assert ("category", "code") in tag_constraints
    assert Base.metadata.tables["common_column_blacklist"].c.column_name.unique is True
