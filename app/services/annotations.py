"""字段标注服务（DEV-TASKS T5.1）。"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, Protocol, cast

from sqlalchemy import delete, select
from sqlalchemy.dialects.postgresql import insert

from app.core.exceptions import ErrorCode, NotFoundError
from app.models.knowledge import AnnotationHistory, AssetAnnotation
from app.schemas.annotations import FieldAnnotationOut, FieldAnnotationPayload


class AnnotationSession(Protocol):
    async def execute(self, statement: object, parameters: dict[str, Any] | None = None) -> Any: ...

    async def commit(self) -> None: ...


_ANNOTATION_FIELDS = (
    "urn",
    "asset_type",
    "domain_id",
    "business_meaning",
    "logical_type_override",
    "dict_id",
    "dict_inline",
    "sample_value",
    "source_desc",
    "usage_note",
    "owner_id",
    "lifecycle",
    "status",
    "source_type",
    "inherited_from",
    "created_by",
    "updated_by",
    "created_at",
    "updated_at",
)


class SQLAlchemyAnnotationService:
    async def get_field_annotation(
        self,
        session: AnnotationSession,
        *,
        urn: str,
    ) -> FieldAnnotationOut:
        annotation = await self._load_field_annotation(session, urn=urn)
        if annotation is None:
            raise NotFoundError(
                "字段标注不存在",
                detail={"urn": urn, "code": ErrorCode.ANNOTATION_NOT_FOUND},
            )
        return _annotation_out(annotation)

    async def upsert_field_annotation(
        self,
        session: AnnotationSession,
        *,
        urn: str,
        payload: FieldAnnotationPayload,
        operator_id: int | None = None,
    ) -> FieldAnnotationOut:
        now = datetime.now(UTC)
        existing = await self._load_field_annotation(session, urn=urn)
        before_data = _annotation_snapshot(existing) if existing is not None else None
        values = _annotation_values(
            urn=urn,
            payload=payload,
            operator_id=operator_id,
            now=now,
            is_create=existing is None,
        )
        update_values = {key: value for key, value in values.items() if key not in {"created_at"}}
        result = await session.execute(
            insert(AssetAnnotation)
            .values(values)
            .on_conflict_do_update(
                index_elements=[AssetAnnotation.urn],
                set_=update_values,
            )
            .returning(AssetAnnotation)
        )
        annotation = cast(AssetAnnotation, result.scalar_one())
        await _write_history(
            session,
            urn=urn,
            before_data=before_data,
            after_data=_annotation_snapshot(annotation),
            operator_id=operator_id,
            created_at=now,
        )
        await session.commit()
        return _annotation_out(annotation)

    async def delete_field_annotation(
        self,
        session: AnnotationSession,
        *,
        urn: str,
        operator_id: int | None = None,
    ) -> None:
        now = datetime.now(UTC)
        existing = await self._load_field_annotation(session, urn=urn)
        if existing is None:
            raise NotFoundError(
                "字段标注不存在",
                detail={"urn": urn, "code": ErrorCode.ANNOTATION_NOT_FOUND},
            )
        await session.execute(
            delete(AssetAnnotation).where(
                AssetAnnotation.urn == urn,
                AssetAnnotation.asset_type == "COLUMN",
            )
        )
        await _write_history(
            session,
            urn=urn,
            before_data=_annotation_snapshot(existing),
            after_data=None,
            operator_id=operator_id,
            created_at=now,
        )
        await session.commit()

    async def _load_field_annotation(
        self,
        session: AnnotationSession,
        *,
        urn: str,
    ) -> AssetAnnotation | None:
        result = await session.execute(
            select(AssetAnnotation).where(
                AssetAnnotation.urn == urn,
                AssetAnnotation.asset_type == "COLUMN",
            )
        )
        return cast(AssetAnnotation | None, result.scalar_one_or_none())


def _annotation_values(
    *,
    urn: str,
    payload: FieldAnnotationPayload,
    operator_id: int | None,
    now: datetime,
    is_create: bool,
) -> dict[str, Any]:
    values = {
        "urn": urn,
        "asset_type": "COLUMN",
        "domain_id": payload.domain_id,
        "business_meaning": payload.business_meaning,
        "logical_type_override": payload.logical_type_override,
        "dict_id": payload.dict_id,
        "dict_inline": payload.dict_inline,
        "sample_value": payload.sample_value,
        "source_desc": payload.source_desc,
        "usage_note": payload.usage_note,
        "owner_id": payload.owner_id,
        "lifecycle": "ACTIVE",
        "status": "CONFIRMED",
        "source_type": "MANUAL",
        "inherited_from": None,
        "updated_by": operator_id,
        "updated_at": now,
    }
    if is_create:
        values["created_by"] = operator_id
        values["created_at"] = now
    return values


async def _write_history(
    session: AnnotationSession,
    *,
    urn: str,
    before_data: dict[str, Any] | None,
    after_data: dict[str, Any] | None,
    operator_id: int | None,
    created_at: datetime,
) -> None:
    await session.execute(
        insert(AnnotationHistory).values(
            {
                "urn": urn,
                "before_data": before_data,
                "after_data": after_data,
                "operator_id": operator_id,
                "created_at": created_at,
            }
        )
    )


def _annotation_snapshot(annotation: object | None) -> dict[str, Any] | None:
    if annotation is None:
        return None
    return {field: getattr(annotation, field) for field in _ANNOTATION_FIELDS}


def _annotation_out(annotation: object) -> FieldAnnotationOut:
    snapshot = _annotation_snapshot(annotation)
    assert snapshot is not None
    return FieldAnnotationOut.model_validate(snapshot)
