import asyncio
from abc import ABC, abstractmethod
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, TypeVar

from app.collectors.type_mapper import normalize_column_type

T = TypeVar("T")


@dataclass(frozen=True, slots=True)
class DataSourceConfig:
    source_id: int
    code: str
    db_type: str
    host: str
    port: int
    username: str
    password: str
    default_db: str | None = None
    include_rules: list[dict[str, Any]] = field(default_factory=list)
    exclude_rules: list[dict[str, Any]] = field(default_factory=list)
    max_query_concurrency: int = 1
    min_query_interval_seconds: float = 0.1
    query_timeout_seconds: float = 60.0


@dataclass(frozen=True, slots=True)
class DatabaseInfo:
    name: str


@dataclass(frozen=True, slots=True)
class TableInfo:
    db_name: str
    table_name: str
    table_type: str
    table_comment: str | None = None
    engine: str | None = None
    row_count: int | None = None
    data_size: int | None = None
    db_created_at: datetime | None = None


@dataclass(frozen=True, slots=True)
class ColumnInfo:
    db_name: str
    table_name: str
    column_name: str
    ordinal: int
    raw_type: str
    logical_type: str
    is_nullable: bool
    raw_comment: str | None = None
    data_length: int | None = None
    num_precision: int | None = None
    num_scale: int | None = None
    default_value: str | None = None
    is_primary_key: bool = False
    is_auto_incr: bool = False
    is_unique: bool = False


@dataclass(frozen=True, slots=True)
class IndexInfo:
    db_name: str
    table_name: str
    index_name: str
    columns: list[str]
    index_type: str | None = None
    is_unique: bool = False


class BaseCollector(ABC):
    """所有采集器的只读抽象基类。"""

    def __init__(self, config: DataSourceConfig):
        self.config = config
        self._query_semaphore = asyncio.Semaphore(max(1, config.max_query_concurrency))
        self._query_rate_lock = asyncio.Lock()
        self._last_query_started_at = 0.0

    @abstractmethod
    async def test_connection(self) -> bool: ...

    @abstractmethod
    async def list_databases(self) -> list[DatabaseInfo]: ...

    @abstractmethod
    async def list_tables(self, db_name: str) -> list[TableInfo]:
        """必须包含 table_comment，取法见 PRD M2 注释对照表。"""

    @abstractmethod
    async def list_columns(self, db_name: str) -> list[ColumnInfo]:
        """一次拉取整库字段，禁止逐表查询；必须包含 raw_comment。"""

    @abstractmethod
    async def list_indexes(self, db_name: str) -> list[IndexInfo]: ...

    def normalize_type(self, raw_type: str) -> str:
        return normalize_column_type(self.config.db_type, raw_type)

    async def _run_limited_query(self, operation: Callable[[], Awaitable[T]]) -> T:
        async with self._query_semaphore:
            await self._wait_for_query_slot()
            return await asyncio.wait_for(operation(), timeout=self.config.query_timeout_seconds)

    async def _wait_for_query_slot(self) -> None:
        min_interval = max(0.0, self.config.min_query_interval_seconds)
        if min_interval == 0:
            return

        async with self._query_rate_lock:
            loop = asyncio.get_running_loop()
            now = loop.time()
            elapsed = now - self._last_query_started_at
            if elapsed < min_interval:
                await asyncio.sleep(min_interval - elapsed)
                now = loop.time()
            self._last_query_started_at = now
