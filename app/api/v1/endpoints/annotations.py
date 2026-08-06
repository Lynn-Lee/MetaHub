"""字段标注接口（DEV-TASKS T5.1）。"""

from typing import Annotated, Any

from fastapi import APIRouter, Body, Depends, Response, status
from pydantic import ValidationError

from app.core.exceptions import AnnotationBatchError, AnnotationReadonlyFieldError, MetaHubError
from app.db.session import get_web_session
from app.schemas.annotations import (
    FieldAnnotationOut,
    FieldAnnotationPayload,
    TableFieldAnnotationsOut,
    TableFieldAnnotationsPayload,
)
from app.services.annotations import AnnotationSession, SQLAlchemyAnnotationService

router = APIRouter(prefix="/annotations", tags=["annotations"])

_COLLECTION_FIELDS = {
    "id",
    "table_urn",
    "column_name",
    "ordinal",
    "raw_type",
    "logical_type",
    "data_length",
    "num_precision",
    "num_scale",
    "is_nullable",
    "default_value",
    "raw_comment",
    "is_primary_key",
    "is_auto_incr",
    "is_unique",
    "is_partition_key",
    "is_deleted",
    "deleted_at",
    "synced_at",
    "search_text",
}


@router.get("/field", response_model=FieldAnnotationOut, summary="读取单字段标注")
async def get_field_annotation(
    urn: str,
    session: Annotated[AnnotationSession, Depends(get_web_session)],
) -> FieldAnnotationOut:
    service = SQLAlchemyAnnotationService()
    return await service.get_field_annotation(session, urn=urn)


@router.put("/field", response_model=FieldAnnotationOut, summary="创建或更新单字段标注")
async def upsert_field_annotation(
    urn: str,
    raw_payload: Annotated[dict[str, Any], Body(...)],
    session: Annotated[AnnotationSession, Depends(get_web_session)],
) -> FieldAnnotationOut:
    _reject_collection_fields(raw_payload)
    try:
        payload = FieldAnnotationPayload.model_validate(raw_payload)
    except ValidationError as exc:
        raise MetaHubError("请求参数校验失败", detail={"errors": exc.errors()}) from exc
    service = SQLAlchemyAnnotationService()
    return await service.upsert_field_annotation(session, urn=urn, payload=payload)


@router.put(
    "/table/fields",
    response_model=TableFieldAnnotationsOut,
    summary="表内批量标注字段",
)
async def upsert_table_field_annotations(
    table_urn: str,
    raw_payload: Annotated[dict[str, Any], Body(...)],
    session: Annotated[AnnotationSession, Depends(get_web_session)],
) -> TableFieldAnnotationsOut:
    payload = _parse_table_field_annotations_payload(raw_payload)
    service = SQLAlchemyAnnotationService()
    return await service.upsert_table_field_annotations(
        session,
        table_urn=table_urn,
        items=payload.items,
    )


@router.delete("/field", status_code=status.HTTP_204_NO_CONTENT, summary="删除单字段标注")
async def delete_field_annotation(
    urn: str,
    session: Annotated[AnnotationSession, Depends(get_web_session)],
) -> Response:
    service = SQLAlchemyAnnotationService()
    await service.delete_field_annotation(session, urn=urn)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


def _reject_collection_fields(payload: dict[str, Any]) -> None:
    fields = sorted(_COLLECTION_FIELDS.intersection(payload))
    if fields:
        raise AnnotationReadonlyFieldError(
            "标注接口不允许写入采集层字段",
            detail={"fields": fields},
        )


def _parse_table_field_annotations_payload(
    raw_payload: dict[str, Any],
) -> TableFieldAnnotationsPayload:
    errors = _collect_batch_payload_errors(raw_payload)
    if errors:
        raise AnnotationBatchError("表内批量标注失败", detail={"errors": errors})
    try:
        return TableFieldAnnotationsPayload.model_validate(raw_payload)
    except ValidationError as exc:
        raise AnnotationBatchError(
            "表内批量标注失败",
            detail={"errors": [{"urn": "", "message": str(exc)}]},
        ) from exc


def _collect_batch_payload_errors(raw_payload: dict[str, Any]) -> list[dict[str, Any]]:
    errors: list[dict[str, Any]] = []
    raw_items = raw_payload.get("items")
    if not isinstance(raw_items, list):
        return [{"urn": "", "message": "items 必须是数组"}]
    for raw_item in raw_items:
        if not isinstance(raw_item, dict):
            errors.append({"urn": "", "message": "批量项必须是对象"})
            continue
        urn = raw_item.get("urn")
        raw_annotation = raw_item.get("annotation")
        if not isinstance(raw_annotation, dict):
            errors.append({"urn": str(urn or ""), "message": "annotation 必须是对象"})
            continue
        fields = sorted(_COLLECTION_FIELDS.intersection(raw_annotation))
        if fields:
            errors.append(
                {
                    "urn": str(urn or ""),
                    "fields": fields,
                    "message": "标注接口不允许写入采集层字段",
                }
            )
    return errors
