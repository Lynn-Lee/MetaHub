import asyncio
from collections.abc import Awaitable, Callable
from pathlib import Path
from typing import TypeVar

import pytest

from app.collectors import BaseCollector, DataSourceConfig

T = TypeVar("T")


class GuardedCollector(BaseCollector):
    async def test_connection(self) -> bool:
        return True

    async def list_databases(self) -> list[object]:
        return []

    async def list_tables(self, db_name: str) -> list[object]:
        return []

    async def list_columns(self, db_name: str) -> list[object]:
        return []

    async def list_indexes(self, db_name: str) -> list[object]:
        return []

    async def guarded(self, operation: Callable[[], Awaitable[T]]) -> T:
        return await self._run_limited_query(operation)


def _config(**overrides: object) -> DataSourceConfig:
    values = {
        "source_id": 1,
        "code": "limited_source",
        "db_type": "mysql",
        "host": "127.0.0.1",
        "port": 3306,
        "username": "readonly",
        "password": "secret",
        "min_query_interval_seconds": 0.0,
        "query_timeout_seconds": 1.0,
    }
    values.update(overrides)
    return DataSourceConfig(**values)


def test_mysql_and_postgresql_fetch_paths_use_query_guard() -> None:
    for collector_path in (
        Path("app/collectors/mysql.py"),
        Path("app/collectors/postgresql.py"),
    ):
        source = collector_path.read_text(encoding="utf-8")
        assert "_run_limited_query" in source


async def test_query_guard_limits_concurrency() -> None:
    collector = GuardedCollector(_config(max_query_concurrency=1))
    active = 0
    max_active = 0

    async def operation() -> str:
        nonlocal active, max_active
        active += 1
        max_active = max(max_active, active)
        await asyncio.sleep(0.01)
        active -= 1
        return "ok"

    results = await asyncio.gather(collector.guarded(operation), collector.guarded(operation))

    assert results == ["ok", "ok"]
    assert max_active == 1


async def test_query_guard_enforces_min_interval() -> None:
    collector = GuardedCollector(_config(min_query_interval_seconds=0.02))
    starts: list[float] = []

    async def operation() -> str:
        starts.append(asyncio.get_running_loop().time())
        return "ok"

    await collector.guarded(operation)
    await collector.guarded(operation)

    assert len(starts) == 2
    assert starts[1] - starts[0] >= 0.018


async def test_query_guard_times_out_slow_query() -> None:
    collector = GuardedCollector(_config(query_timeout_seconds=0.01))

    async def operation() -> str:
        await asyncio.sleep(1)
        return "too slow"

    with pytest.raises(TimeoutError):
        await collector.guarded(operation)
