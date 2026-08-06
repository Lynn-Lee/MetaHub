from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

import pytest
from sqlalchemy.dialects import postgresql

from app.core.exceptions import AnnotationBatchError
from app.schemas.annotations import BatchFieldAnnotationPayload, FieldAnnotationPayload
from app.services.annotations import SQLAlchemyAnnotationService


class AnnotationRow:
    def __init__(self, **values: Any) -> None:
        self.id = values.get("id", 1)
        self.urn = values["urn"]
        self.asset_type = values.get("asset_type", "COLUMN")
        self.domain_id = values.get("domain_id")
        self.business_meaning = values.get("business_meaning")
        self.logical_type_override = values.get("logical_type_override")
        self.dict_id = values.get("dict_id")
        self.dict_inline = values.get("dict_inline")
        self.sample_value = values.get("sample_value")
        self.source_desc = values.get("source_desc")
        self.usage_note = values.get("usage_note")
        self.owner_id = values.get("owner_id")
        self.lifecycle = values.get("lifecycle", "ACTIVE")
        self.status = values.get("status", "CONFIRMED")
        self.source_type = values.get("source_type", "MANUAL")
        self.inherited_from = values.get("inherited_from")
        self.created_by = values.get("created_by")
        self.updated_by = values.get("updated_by")
        self.created_at = values.get("created_at", datetime.now(UTC))
        self.updated_at = values.get("updated_at", datetime.now(UTC))


class ScalarResult:
    def __init__(self, value: AnnotationRow | None) -> None:
        self._value = value

    def scalar_one_or_none(self) -> AnnotationRow | None:
        return self._value

    def scalar_one(self) -> AnnotationRow:
        assert self._value is not None
        return self._value


class RecordingSession:
    def __init__(
        self,
        *,
        existing: AnnotationRow | None = None,
        saved: AnnotationRow | None = None,
        fail_on_urn: str | None = None,
    ) -> None:
        self.existing = existing
        self.saved = saved
        self.fail_on_urn = fail_on_urn
        self.statements: list[str] = []
        self.commits = 0
        self.rollbacks = 0

    async def execute(
        self,
        statement: object,
        parameters: dict[str, Any] | None = None,
    ) -> ScalarResult:
        del parameters
        compiled = str(statement.compile(dialect=postgresql.dialect())).replace("\n", " ")
        self.statements.append(compiled)
        if self.fail_on_urn is not None and self.fail_on_urn in str(statement.compile().params):
            raise ValueError("dictionary is invalid")
        if compiled.startswith("SELECT asset_annotation"):
            return ScalarResult(self.existing)
        if "INSERT INTO asset_annotation" in compiled and "RETURNING" in compiled:
            return ScalarResult(self.saved)
        return ScalarResult(None)

    async def commit(self) -> None:
        self.commits += 1

    async def rollback(self) -> None:
        self.rollbacks += 1


async def test_upsert_field_annotation_writes_annotation_and_history() -> None:
    urn = "mysql:crm:sales:orders:pay_amount"
    session = RecordingSession(
        saved=AnnotationRow(
            urn=urn,
            business_meaning="订单支付金额",
            logical_type_override="DECIMAL",
            owner_id=42,
            updated_by=1001,
        )
    )
    service = SQLAlchemyAnnotationService()

    result = await service.upsert_field_annotation(
        session,
        urn=urn,
        payload=FieldAnnotationPayload(
            business_meaning="订单支付金额",
            logical_type_override="DECIMAL",
            owner_id=42,
        ),
        operator_id=1001,
    )

    assert result.urn == urn
    assert result.business_meaning == "订单支付金额"
    assert any("INSERT INTO asset_annotation" in statement for statement in session.statements)
    assert any("ON CONFLICT" in statement for statement in session.statements)
    assert any("INSERT INTO annotation_history" in statement for statement in session.statements)
    assert session.commits == 1


async def test_delete_field_annotation_writes_history_before_deleting() -> None:
    urn = "mysql:crm:sales:orders:pay_amount"
    session = RecordingSession(
        existing=AnnotationRow(
            urn=urn,
            business_meaning="订单支付金额",
            logical_type_override="DECIMAL",
        )
    )
    service = SQLAlchemyAnnotationService()

    await service.delete_field_annotation(session, urn=urn, operator_id=1001)

    joined = " ".join(session.statements)
    assert "SELECT asset_annotation" in joined
    assert "DELETE FROM asset_annotation" in joined
    assert "INSERT INTO annotation_history" in joined
    assert session.commits == 1


async def test_batch_upsert_rolls_back_and_returns_field_errors_on_partial_failure() -> None:
    table_urn = "mysql:crm:sales:orders"
    bad_urn = f"{table_urn}:order_status"
    session = RecordingSession(
        saved=AnnotationRow(
            urn=f"{table_urn}:pay_amount",
            business_meaning="订单支付金额",
        ),
        fail_on_urn=bad_urn,
    )
    service = SQLAlchemyAnnotationService()

    with pytest.raises(AnnotationBatchError) as exc_info:
        await service.upsert_table_field_annotations(
            session,
            table_urn=table_urn,
            items=[
                BatchFieldAnnotationPayload(
                    urn=f"{table_urn}:pay_amount",
                    annotation=FieldAnnotationPayload(business_meaning="订单支付金额"),
                ),
                BatchFieldAnnotationPayload(
                    urn=bad_urn,
                    annotation=FieldAnnotationPayload(business_meaning="订单状态"),
                ),
            ],
            operator_id=1001,
        )

    assert session.commits == 0
    assert session.rollbacks == 1
    assert exc_info.value.detail["errors"] == [
        {
            "urn": bad_urn,
            "message": "dictionary is invalid",
        }
    ]
