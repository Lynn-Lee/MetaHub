"""基础查询接口 schema（DEV-TASKS T6.2）。"""

from typing import Generic, TypeVar

from pydantic import BaseModel, Field

from app.schemas.urns import ColumnUrn, TableUrn

T = TypeVar("T")


class MetadataPage(BaseModel, Generic[T]):
    total: int = Field(ge=0)
    page: int = Field(ge=1)
    page_size: int = Field(ge=1, le=100)
    items: list[T]


class DataSourceOut(BaseModel):
    id: int
    code: str
    name: str
    db_type: str
    env: str
    host: str
    port: int
    default_db: str | None
    group_name: str | None
    enabled: bool


class TableOut(BaseModel):
    urn: TableUrn
    source_id: int
    db_name: str
    table_name: str
    table_type: str
    table_comment: str | None
    row_count: int | None
    data_size: int | None
    dw_layer: str | None
    is_deleted: bool
    score: float | None = None


class ColumnOut(BaseModel):
    urn: ColumnUrn
    table_urn: TableUrn
    source_id: int | None = None
    db_name: str | None = None
    table_name: str | None = None
    column_name: str
    ordinal: int
    raw_type: str
    logical_type: str
    raw_comment: str | None
    is_nullable: bool
    is_primary_key: bool
    is_deleted: bool
    business_meaning: str | None
    effective_type: str | None
    effective_domain_id: int | None
    domain_name: str | None
    score: float | None = None


class TableDdlOut(BaseModel):
    urn: TableUrn
    ddl: str
    total: int = 1


class FieldSearchGroupOut(BaseModel):
    table_urn: TableUrn
    source_id: int
    db_name: str
    table_name: str
    max_score: float
    columns: list[ColumnOut]


class SearchOut(BaseModel):
    query: str
    total: int = Field(ge=0)
    page: int = Field(ge=1)
    page_size: int = Field(ge=1, le=100)
    tables: list[TableOut]
    field_groups: list[FieldSearchGroupOut]
