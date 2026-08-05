# V0.1 Collection Models Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement DEV-TASKS T1.1 collection-layer metadata tables as SQLAlchemy models with an Alembic bootstrap migration.

**Architecture:** Keep model definitions in small files under `app/models/`, registered through `app/models/__init__.py`. SQLAlchemy ORM models own table shape and layer registration; Alembic owns the database DDL including PostgreSQL generated search columns and trigram indexes.

**Tech Stack:** Python 3.11+, FastAPI, SQLAlchemy 2.0, Alembic, PostgreSQL 15+ with `pg_trgm`.

---

### File Structure

- Create `app/models/metadata.py`: collection-layer ORM models for `data_source`, `table_meta`, `column_meta`, and `index_meta`.
- Modify `app/models/__init__.py`: import model modules so `Base.metadata` sees all tables.
- Create `alembic.ini`: local Alembic configuration.
- Create `alembic/env.py`: migration environment wired to `app.db.base.Base.metadata`.
- Create `alembic/versions/20260805_0001_collection_metadata.py`: initial collection-layer migration with extensions, tables, generated columns, and indexes.
- Create `tests/models/test_collection_models.py`: metadata-level tests for table registration, column contracts, and generated search columns.

### Task 1: Red Test For Collection Models

**Files:**
- Create: `tests/models/test_collection_models.py`

- [ ] **Step 1: Write failing tests**

```python
from sqlalchemy import Computed

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
```

- [ ] **Step 2: Run test to verify it fails**

Run: `.venv/bin/pytest tests/models/test_collection_models.py -v`

Expected: FAIL because `data_source`, `table_meta`, `column_meta`, and `index_meta` are not defined yet.

### Task 2: Green Implementation For Collection Models

**Files:**
- Create: `app/models/metadata.py`
- Modify: `app/models/__init__.py`

- [ ] **Step 1: Implement minimal ORM models**

Define the four collection tables with SQLAlchemy typed columns, JSON fields for rules and index column lists, generated `search_text` columns on `table_meta` and `column_meta`, and add all four table names to `COLLECTION_TABLES`.

- [ ] **Step 2: Run focused tests**

Run: `.venv/bin/pytest tests/models/test_collection_models.py -v`

Expected: PASS.

### Task 3: Alembic Bootstrap

**Files:**
- Create: `alembic.ini`
- Create: `alembic/env.py`
- Create: `alembic/versions/20260805_0001_collection_metadata.py`

- [ ] **Step 1: Add Alembic environment**

Wire Alembic to `Base.metadata` and load `app.models` before autogenerate.

- [ ] **Step 2: Add initial migration**

Create `pg_trgm`, create collection tables, create normal indexes, add generated `search_text` columns, and create GIN trigram indexes.

- [ ] **Step 3: Verify migration syntax without a live database**

Run: `.venv/bin/alembic heads`

Expected: output includes `20260805_0001`.

### Task 4: Final Checks

- [ ] Run `.venv/bin/pytest -v`
- [ ] Run `.venv/bin/ruff check app tests`
- [ ] Run `.venv/bin/mypy app`
- [ ] Commit is skipped because `/Users/lynn/SynologyDrive/SynologyDrive/Code/DataDict` is not a Git repository.

### Self-Review

- Spec coverage: this plan covers DEV-TASKS T1.1 only. It intentionally does not implement T1.2 knowledge-layer tables, T1.3 support tables, grants, collectors, search, or APIs.
- Placeholder scan: no placeholder steps remain.
- Type consistency: model names and table names match DEV-TASKS T1.1 and PRD §5.2.
