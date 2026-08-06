"""标注接口 schema（DEV-TASKS T5.1）。"""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class FieldAnnotationPayload(BaseModel):
    model_config = ConfigDict(extra="ignore")

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
    urn: str
    annotation: FieldAnnotationPayload


class TableFieldAnnotationsPayload(BaseModel):
    items: list[BatchFieldAnnotationPayload] = Field(min_length=1)


class FieldAnnotationOut(BaseModel):
    urn: str
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
    table_urn: str
    items: list[FieldAnnotationOut]
