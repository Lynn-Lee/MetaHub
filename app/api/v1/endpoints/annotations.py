"""字段标注接口（DEV-TASKS T5.1）。"""

from typing import Annotated, Any

from fastapi import APIRouter, Body, Depends, Response, status
from pydantic import ValidationError

from app.core.exceptions import AnnotationReadonlyFieldError, MetaHubError
from app.db.session import get_web_session
from app.schemas.annotations import FieldAnnotationOut, FieldAnnotationPayload
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
