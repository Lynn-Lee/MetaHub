from sqlalchemy import Computed

import app.models  # noqa: F401 - imports model modules into Base.metadata
from app.db.base import COLLECTION_TABLES, Base


def test_collection_tables_are_registered() -> None:
    expected = {"data_source", "table_meta", "column_meta", "index_meta"}

    assert expected.issubset(Base.metadata.tables)
    assert expected.issubset(COLLECTION_TABLES)


def test_table_meta_search_text_is_generated() -> None:
    column = Base.metadata.tables["table_meta"].c.search_text

    assert isinstance(column.computed, Computed)
    assert "table_name" in str(column.computed.sqltext)
    assert "table_comment" in str(column.computed.sqltext)


def test_column_meta_contract() -> None:
    table = Base.metadata.tables["column_meta"]

    assert table.c.urn.unique is True
    assert table.c.raw_type.nullable is False
    assert table.c.logical_type.nullable is False
    assert table.c.search_text.computed is not None
