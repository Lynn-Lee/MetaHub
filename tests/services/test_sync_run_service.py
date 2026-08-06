from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy.dialects import postgresql

from app.services.sync_run import (
    SQLAlchemySyncRunRecorder,
    SyncFailure,
    calculate_comment_fill_rate,
)


class ScalarResult:
    def __init__(self, value: Decimal | int | None):
        self._value = value

    def scalar_one_or_none(self) -> Decimal | None:
        if isinstance(self._value, Decimal):
            return self._value
        return None

    def scalar_one(self) -> int:
        assert isinstance(self._value, int)
        return self._value


class RecordingSession:
    def __init__(self, previous_rate: Decimal | None = None):
        self.previous_rate = previous_rate
        self.statements: list[str] = []

    async def execute(
        self,
        statement: object,
        parameters: dict[str, Any] | None = None,
    ) -> ScalarResult:
        del parameters
        compiled = str(statement.compile(dialect=postgresql.dialect())).replace("\n", " ")
        self.statements.append(compiled)
        if "INSERT INTO sync_job_log" in compiled:
            return ScalarResult(123)
        return ScalarResult(self.previous_rate)


class RecordingAlertSink:
    def __init__(self) -> None:
        self.alerts: list[dict[str, Any]] = []

    async def notify_comment_rate_drop(
        self,
        *,
        source_id: int,
        previous_rate: Decimal,
        current_rate: Decimal,
    ) -> None:
        self.alerts.append(
            {
                "source_id": source_id,
                "previous_rate": previous_rate,
                "current_rate": current_rate,
            }
        )


def test_calculate_comment_fill_rate_uses_collected_columns() -> None:
    assert calculate_comment_fill_rate(
        [
            {"raw_comment": "支付金额"},
            {"raw_comment": ""},
            {"raw_comment": None},
            {"raw_comment": "订单编号"},
        ]
    ) == Decimal("50.00")
    assert calculate_comment_fill_rate([]) == Decimal("0.00")


async def test_sync_run_recorder_writes_job_summary_and_fail_details() -> None:
    session = RecordingSession()
    recorder = SQLAlchemySyncRunRecorder(alert_sink=RecordingAlertSink())
    started_at = datetime.now(UTC)
    finished_at = datetime.now(UTC)

    await recorder.record_run(
        session,
        source_id=7,
        trigger_type="MANUAL",
        status="PARTIAL",
        scanned_tables=3,
        changed_count=2,
        comment_fill_rate=Decimal("66.67"),
        started_at=started_at,
        finished_at=finished_at,
        failures=[
            SyncFailure(
                source_id=7,
                db_name="sales",
                table_name="orders",
                stage="columns",
                error_type="TimeoutError",
                error_msg="query timed out",
            )
        ],
    )

    assert len(session.statements) == 3
    assert "SELECT sync_job_log.comment_fill_rate" in session.statements[0]
    assert "INSERT INTO sync_job_log" in session.statements[1]
    assert "INSERT INTO sync_fail_detail" in session.statements[2]


async def test_sync_run_recorder_alerts_when_comment_fill_rate_drops_more_than_half() -> None:
    alerts = RecordingAlertSink()
    session = RecordingSession(previous_rate=Decimal("80.00"))
    recorder = SQLAlchemySyncRunRecorder(alert_sink=alerts)

    await recorder.record_run(
        session,
        source_id=7,
        trigger_type="CRON",
        status="SUCCESS",
        scanned_tables=1,
        changed_count=0,
        comment_fill_rate=Decimal("30.00"),
        started_at=datetime.now(UTC),
        finished_at=datetime.now(UTC),
        failures=[],
    )

    assert alerts.alerts == [
        {
            "source_id": 7,
            "previous_rate": Decimal("80.00"),
            "current_rate": Decimal("30.00"),
        }
    ]
