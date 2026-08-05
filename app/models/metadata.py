"""采集层元数据模型（DEV-TASKS T1.1）。

这些表由同步任务写入，可被下一轮采集覆盖；人工业务语义不放在这里。
"""

from datetime import datetime
from typing import Any

from sqlalchemy import BigInteger, Boolean, Computed, DateTime, ForeignKey, Index, Integer, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import COLLECTION_TABLES, Base


class DataSource(Base):
    __tablename__ = "data_source"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    code: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    db_type: Mapped[str] = mapped_column(String(32), nullable=False)
    env: Mapped[str] = mapped_column(String(16), nullable=False)
    host: Mapped[str] = mapped_column(String(255), nullable=False)
    port: Mapped[int] = mapped_column(Integer, nullable=False)
    default_db: Mapped[str | None] = mapped_column(String(128))
    username: Mapped[str] = mapped_column(String(128), nullable=False)
    password_cipher: Mapped[str] = mapped_column(nullable=False)
    include_rules: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, default=list)
    exclude_rules: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, default=list)
    sync_cron: Mapped[str] = mapped_column(String(64), default="0 2 * * *")
    group_name: Mapped[str | None] = mapped_column(String(64))
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    last_sync_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class TableMeta(Base):
    __tablename__ = "table_meta"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    urn: Mapped[str] = mapped_column(String(512), unique=True, nullable=False)
    source_id: Mapped[int] = mapped_column(ForeignKey("data_source.id"), nullable=False)
    db_name: Mapped[str] = mapped_column(String(128), nullable=False)
    table_name: Mapped[str] = mapped_column(String(128), nullable=False)
    table_type: Mapped[str] = mapped_column(String(32), default="TABLE")
    table_comment: Mapped[str | None]
    engine: Mapped[str | None] = mapped_column(String(32))
    row_count: Mapped[int | None] = mapped_column(BigInteger)
    data_size: Mapped[int | None] = mapped_column(BigInteger)
    db_created_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    dw_layer: Mapped[str | None] = mapped_column(String(16))
    partition_keys: Mapped[list[str] | None] = mapped_column(JSONB)
    distribution_keys: Mapped[list[str] | None] = mapped_column(JSONB)
    sort_keys: Mapped[list[str] | None] = mapped_column(JSONB)
    storage_format: Mapped[str | None] = mapped_column(String(32))
    table_model: Mapped[str | None] = mapped_column(String(32))
    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    synced_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    search_text: Mapped[str] = mapped_column(
        Computed("coalesce(table_name,'') || ' ' || coalesce(table_comment,'')", persisted=True)
    )

    __table_args__ = (
        Index("idx_table_meta_source", "source_id", "db_name"),
        Index("idx_table_meta_name", "table_name"),
    )


class ColumnMeta(Base):
    __tablename__ = "column_meta"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    urn: Mapped[str] = mapped_column(String(768), unique=True, nullable=False)
    table_urn: Mapped[str] = mapped_column(String(512), nullable=False)
    column_name: Mapped[str] = mapped_column(String(128), nullable=False)
    ordinal: Mapped[int] = mapped_column(Integer, nullable=False)
    raw_type: Mapped[str] = mapped_column(String(128), nullable=False)
    logical_type: Mapped[str] = mapped_column(String(32), nullable=False)
    data_length: Mapped[int | None] = mapped_column(Integer)
    num_precision: Mapped[int | None] = mapped_column(Integer)
    num_scale: Mapped[int | None] = mapped_column(Integer)
    is_nullable: Mapped[bool] = mapped_column(Boolean, default=True)
    default_value: Mapped[str | None]
    raw_comment: Mapped[str | None]
    is_primary_key: Mapped[bool] = mapped_column(Boolean, default=False)
    is_auto_incr: Mapped[bool] = mapped_column(Boolean, default=False)
    is_unique: Mapped[bool] = mapped_column(Boolean, default=False)
    is_partition_key: Mapped[bool] = mapped_column(Boolean, default=False)
    is_deleted: Mapped[bool] = mapped_column(Boolean, default=False)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    synced_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    search_text: Mapped[str] = mapped_column(
        Computed("coalesce(column_name,'') || ' ' || coalesce(raw_comment,'')", persisted=True)
    )

    __table_args__ = (
        Index("idx_column_meta_table", "table_urn"),
        Index("idx_column_meta_name", "column_name", "logical_type"),
    )


class IndexMeta(Base):
    __tablename__ = "index_meta"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    table_urn: Mapped[str] = mapped_column(String(512), nullable=False)
    index_name: Mapped[str] = mapped_column(String(128), nullable=False)
    index_type: Mapped[str | None] = mapped_column(String(32))
    columns: Mapped[list[dict[str, Any]]] = mapped_column(JSONB, nullable=False)
    synced_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))

    __table_args__ = (
        Index("uq_index_meta_table_urn_index_name", "table_urn", "index_name", unique=True),
    )


COLLECTION_TABLES.update({"data_source", "table_meta", "column_meta", "index_meta"})
