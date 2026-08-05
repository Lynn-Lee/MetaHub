import re
from typing import Any

import asyncpg

from app.collectors.base import BaseCollector, ColumnInfo, DatabaseInfo, IndexInfo, TableInfo
from app.collectors.registry import register_collector

Row = dict[str, Any]
_TYPE_NUMBERS_RE = re.compile(r"\((\d+)(?:,(\d+))?\)")


class PostgreSQLCollector(BaseCollector):
    async def test_connection(self) -> bool:
        row = await self._fetch_one("SELECT 1 AS ok")
        return row is not None and row.get("ok") == 1

    async def list_databases(self) -> list[DatabaseInfo]:
        rows = await self._fetch_all(
            """
            SELECT datname AS name
            FROM pg_database
            WHERE datallowconn
              AND NOT datistemplate
              AND datname NOT IN ('postgres')
            ORDER BY datname
            """
        )
        return [DatabaseInfo(name=str(row["name"])) for row in rows]

    async def list_tables(self, db_name: str) -> list[TableInfo]:
        rows = await self._fetch_all(
            """
            SELECT
                n.nspname AS db_name,
                c.relname AS table_name,
                CASE c.relkind
                    WHEN 'r' THEN 'TABLE'
                    WHEN 'p' THEN 'TABLE'
                    WHEN 'v' THEN 'VIEW'
                    ELSE upper(c.relkind::text)
                END AS table_type,
                obj_description(c.oid, 'pg_class') AS table_comment,
                COALESCE(s.n_live_tup, 0) AS row_count,
                pg_total_relation_size(c.oid) AS data_size,
                NULL::timestamp AS db_created_at
            FROM pg_class c
            JOIN pg_namespace n ON n.oid = c.relnamespace
            LEFT JOIN pg_stat_user_tables s ON s.relid = c.oid
            WHERE c.relkind IN ('r', 'p', 'v')
              AND n.nspname = $1
            ORDER BY c.relname
            """,
            db_name,
        )
        return [
            TableInfo(
                db_name=str(row["db_name"]),
                table_name=str(row["table_name"]),
                table_type=str(row["table_type"]),
                table_comment=_optional_str(row["table_comment"]),
                row_count=_optional_int(row["row_count"]),
                data_size=_optional_int(row["data_size"]),
                db_created_at=row["db_created_at"],
            )
            for row in rows
        ]

    async def list_columns(self, db_name: str) -> list[ColumnInfo]:
        rows = await self._fetch_all(
            """
            SELECT
                n.nspname AS db_name,
                c.relname AS table_name,
                a.attname AS column_name,
                a.attnum AS ordinal,
                format_type(a.atttypid, a.atttypmod) AS raw_type,
                NULL::integer AS data_length,
                NULL::integer AS num_precision,
                NULL::integer AS num_scale,
                NOT a.attnotnull AS is_nullable,
                pg_get_expr(ad.adbin, ad.adrelid) AS default_value,
                col_description(c.oid, a.attnum) AS raw_comment,
                EXISTS (
                    SELECT 1
                    FROM pg_index i
                    WHERE i.indrelid = c.oid
                      AND i.indisprimary
                      AND a.attnum = ANY(i.indkey)
                ) AS is_primary_key,
                EXISTS (
                    SELECT 1
                    FROM pg_index i
                    WHERE i.indrelid = c.oid
                      AND i.indisunique
                      AND a.attnum = ANY(i.indkey)
                ) AS is_unique
            FROM pg_class c
            JOIN pg_namespace n ON n.oid = c.relnamespace
            JOIN pg_attribute a ON a.attrelid = c.oid
            LEFT JOIN pg_attrdef ad ON ad.adrelid = c.oid AND ad.adnum = a.attnum
            WHERE c.relkind IN ('r', 'p', 'v')
              AND a.attnum > 0
              AND NOT a.attisdropped
              AND n.nspname = $1
            ORDER BY c.relname, a.attnum
            """,
            db_name,
        )
        return [
            ColumnInfo(
                db_name=str(row["db_name"]),
                table_name=str(row["table_name"]),
                column_name=str(row["column_name"]),
                ordinal=int(row["ordinal"]),
                raw_type=str(row["raw_type"]),
                logical_type=self.normalize_type(str(row["raw_type"])),
                data_length=_optional_int(row["data_length"])
                or _parse_type_details(str(row["raw_type"]))[0],
                num_precision=_optional_int(row["num_precision"])
                or _parse_type_details(str(row["raw_type"]))[1],
                num_scale=_optional_int(row["num_scale"])
                or _parse_type_details(str(row["raw_type"]))[2],
                is_nullable=bool(row["is_nullable"]),
                default_value=_optional_str(row["default_value"]),
                raw_comment=_optional_str(row["raw_comment"]),
                is_primary_key=bool(row["is_primary_key"]),
                is_unique=bool(row["is_unique"]),
            )
            for row in rows
        ]

    async def list_indexes(self, db_name: str) -> list[IndexInfo]:
        rows = await self._fetch_all(
            """
            SELECT
                n.nspname AS db_name,
                tbl.relname AS table_name,
                idx.relname AS index_name,
                am.amname AS index_type,
                array_agg(a.attname ORDER BY key_ord.ordinality) AS columns,
                i.indisunique AS is_unique
            FROM pg_index i
            JOIN pg_class tbl ON tbl.oid = i.indrelid
            JOIN pg_namespace n ON n.oid = tbl.relnamespace
            JOIN pg_class idx ON idx.oid = i.indexrelid
            JOIN pg_am am ON am.oid = idx.relam
            JOIN unnest(i.indkey) WITH ORDINALITY AS key_ord(attnum, ordinality) ON true
            JOIN pg_attribute a ON a.attrelid = tbl.oid AND a.attnum = key_ord.attnum
            WHERE n.nspname = $1
            GROUP BY n.nspname, tbl.relname, idx.relname, am.amname, i.indisunique
            ORDER BY tbl.relname, idx.relname
            """,
            db_name,
        )
        return [
            IndexInfo(
                db_name=str(row["db_name"]),
                table_name=str(row["table_name"]),
                index_name=str(row["index_name"]),
                index_type=_optional_str(row["index_type"]),
                columns=list(row["columns"]),
                is_unique=bool(row["is_unique"]),
            )
            for row in rows
        ]

    async def _fetch_all(self, sql: str, *params: Any) -> list[Row]:
        connection = await self._connect()
        try:
            rows = await connection.fetch(sql, *params)
            return [dict(row) for row in rows]
        finally:
            await connection.close()

    async def _fetch_one(self, sql: str, *params: Any) -> Row | None:
        connection = await self._connect()
        try:
            row = await connection.fetchrow(sql, *params)
            return dict(row) if row is not None else None
        finally:
            await connection.close()

    async def _connect(self) -> Any:
        return await asyncpg.connect(
            host=self.config.host,
            port=self.config.port,
            user=self.config.username,
            password=self.config.password,
            database=self.config.default_db,
        )


def _optional_str(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value)
    return text if text else None


def _optional_int(value: Any) -> int | None:
    if value is None:
        return None
    return int(value)


def _parse_type_details(raw_type: str) -> tuple[int | None, int | None, int | None]:
    match = _TYPE_NUMBERS_RE.search(raw_type)
    if match is None:
        return None, None, None

    first = int(match.group(1))
    second = int(match.group(2)) if match.group(2) is not None else None
    normalized_raw_type = raw_type.lower()
    if normalized_raw_type.startswith(("numeric", "decimal")):
        return None, first, second
    return first, None, None


register_collector("postgresql", PostgreSQLCollector)
