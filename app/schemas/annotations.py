"""标注接口 schema（DEV-TASKS T5.1）。"""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field
from pydantic.json_schema import JsonSchemaValue

from app.schemas.urns import ColumnUrn, TableUrn

FIELD_ANNOTATION_PAYLOAD_EXAMPLE: JsonSchemaValue = {
    "business_meaning": "订单支付金额",
    "domain_id": 10,
    "logical_type_override": "decimal",
    "sample_value": "99.90",
    "source_desc": "来自订单支付链路",
    "usage_note": "用于订单金额统计与对账",
    "owner_id": 1001,
}


class FieldAnnotationPayload(BaseModel):
    model_config = ConfigDict(
        extra="ignore",
        json_schema_extra={"example": FIELD_ANNOTATION_PAYLOAD_EXAMPLE},
    )

    business_meaning: str = Field(min_length=1, max_length=4000)
    domain_id: int | None = None
    logical_type_override: str | None = Field(default=None, max_length=32)
    dict_id: int | None = None
    dict_inline: list[dict[str, Any]] | None = None
    sample_value: str | None = None
    source_desc: str | None = None
    usage_note: str | None = None
    owner_id: int | None = None


class BatchFieldAnnotationPayload(BaseModel):
    urn: ColumnUrn
    annotation: FieldAnnotationPayload


class TableFieldAnnotationsPayload(BaseModel):
    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "items": [
                    {
                        "urn": "mysql:crm:sales:orders:pay_amount",
                        "annotation": FIELD_ANNOTATION_PAYLOAD_EXAMPLE,
                    }
                ]
            }
        }
    )

    items: list[BatchFieldAnnotationPayload] = Field(min_length=1)


class FieldAnnotationOut(BaseModel):
    urn: ColumnUrn
    asset_type: str
    domain_id: int | None
    business_meaning: str | None
    logical_type_override: str | None
    dict_id: int | None
    dict_inline: list[dict[str, Any]] | None
    sample_value: str | None
    source_desc: str | None
    usage_note: str | None
    owner_id: int | None
    lifecycle: str
    status: str
    source_type: str
    inherited_from: str | None
    created_by: int | None
    updated_by: int | None
    created_at: datetime | None
    updated_at: datetime | None


class TableFieldAnnotationsOut(BaseModel):
    table_urn: TableUrn
    items: list[FieldAnnotationOut]
