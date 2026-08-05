from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

from app.collectors.type_mapper import normalize_column_type


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


@dataclass(frozen=True, slots=True)
class DatabaseInfo:
    name: str


@dataclass(frozen=True, slots=True)
class TableInfo:
    db_name: str
    table_name: str
    table_type: str
    table_comment: str | None = None


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


class BaseCollector(ABC):
    """所有采集器的只读抽象基类。"""

    def __init__(self, config: DataSourceConfig):
        self.config = config

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
