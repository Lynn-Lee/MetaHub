"""同步执行记录与注释非空率告警（DEV-TASKS T3.4）。"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from decimal import ROUND_HALF_UP, Decimal
from typing import Any, Protocol, cast

from sqlalchemy import desc, select
from sqlalchemy.dialects.postgresql import insert

from app.models.support import SyncFailDetail, SyncJobLog


class RunSession(Protocol):
    async def execute(self, statement: object, parameters: dict[str, Any] | None = None) -> Any: ...


class AlertSink(Protocol):
    async def notify_comment_rate_drop(
        self,
        *,
        source_id: int,
        previous_rate: Decimal,
        current_rate: Decimal,
    ) -> None: ...


class NoopAlertSink:
    async def notify_comment_rate_drop(
        self,
        *,
        source_id: int,
        previous_rate: Decimal,
        current_rate: Decimal,
    ) -> None:
        del source_id, previous_rate, current_rate


@dataclass(frozen=True, slots=True)
class SyncFailure:
    source_id: int
    db_name: str | None
    table_name: str | None
    stage: str
    error_type: str
    error_msg: str


class SQLAlchemySyncRunRecorder:
    def __init__(self, *, alert_sink: AlertSink | None = None):
        self._alert_sink = alert_sink or NoopAlertSink()

    async def record_run(
        self,
        session: RunSession,
        *,
        source_id: int,
        trigger_type: str,
        status: str,
        scanned_tables: int,
        changed_count: int,
        comment_fill_rate: Decimal,
        started_at: datetime,
        finished_at: datetime,
        failures: list[SyncFailure],
    ) -> None:
        previous_rate = await self._load_previous_comment_rate(session, source_id)
        duration_ms = int((finished_at - started_at).total_seconds() * 1000)
        job_result = await session.execute(
            insert(SyncJobLog)
            .values(
                {
                    "source_id": source_id,
                    "trigger_type": trigger_type,
                    "status": status,
                    "scanned_tables": scanned_tables,
                    "changed_count": changed_count,
                    "fail_count": len(failures),
                    "comment_fill_rate": comment_fill_rate,
                    "error_msg": _join_errors(failures),
                    "started_at": started_at,
                    "finished_at": finished_at,
                    "duration_ms": duration_ms,
                }
            )
            .returning(SyncJobLog.id)
        )
        job_id = int(job_result.scalar_one())
        if failures:
            await session.execute(
                insert(SyncFailDetail).values(
                    [
                        {
                            "job_id": job_id,
                            "source_id": failure.source_id,
                            "db_name": failure.db_name,
                            "table_name": failure.table_name,
                            "stage": failure.stage,
                            "error_type": failure.error_type,
                            "error_msg": failure.error_msg,
                            "retry_count": 0,
                            "resolved": False,
                            "created_at": finished_at,
                        }
                        for failure in failures
                    ]
                )
            )
        if previous_rate is not None and comment_fill_rate < previous_rate / Decimal("2"):
            await self._alert_sink.notify_comment_rate_drop(
                source_id=source_id,
                previous_rate=previous_rate,
                current_rate=comment_fill_rate,
            )

    async def _load_previous_comment_rate(
        self,
        session: RunSession,
        source_id: int,
    ) -> Decimal | None:
        result = await session.execute(
            select(SyncJobLog.comment_fill_rate)
            .where(
                SyncJobLog.source_id == source_id,
                SyncJobLog.comment_fill_rate.is_not(None),
            )
            .order_by(desc(SyncJobLog.finished_at))
            .limit(1)
        )
        return cast(Decimal | None, result.scalar_one_or_none())


def calculate_comment_fill_rate(columns: list[dict[str, Any]]) -> Decimal:
    if not columns:
        return Decimal("0.00")
    filled = sum(1 for column in columns if _has_comment(column.get("raw_comment")))
    value = Decimal(filled * 100) / Decimal(len(columns))
    return value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def _has_comment(value: object) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _join_errors(failures: list[SyncFailure]) -> str | None:
    if not failures:
        return None
    return "; ".join(f"{failure.stage}: {failure.error_msg}" for failure in failures)
