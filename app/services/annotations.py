"""字段标注服务（DEV-TASKS T5.1 / T5.2）。"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, Protocol, cast

from sqlalchemy import delete, select
from sqlalchemy.dialects.postgresql import insert

from app.core.exceptions import AnnotationBatchError, ErrorCode, NotFoundError
from app.models.knowledge import AnnotationHistory, AssetAnnotation
from app.schemas.annotations import (
    BatchFieldAnnotationPayload,
    FieldAnnotationOut,
    FieldAnnotationPayload,
    TableFieldAnnotationsOut,
)


class AnnotationSession(Protocol):
    async def execute(self, statement: object, parameters: dict[str, Any] | None = None) -> Any: ...

    async def commit(self) -> None: ...

    async def rollback(self) -> None: ...


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
        annotation = await self._upsert_field_annotation_without_commit(
            session,
            urn=urn,
            payload=payload,
            operator_id=operator_id,
            now=now,
        )
        await session.commit()
        return _annotation_out(annotation)

    async def upsert_table_field_annotations(
        self,
        session: AnnotationSession,
        *,
        table_urn: str,
        items: list[BatchFieldAnnotationPayload],
        operator_id: int | None = None,
    ) -> TableFieldAnnotationsOut:
        now = datetime.now(UTC)
        saved: list[AssetAnnotation] = []
        errors: list[dict[str, str]] = []
        try:
            for item in items:
                if not _belongs_to_table(item.urn, table_urn):
                    errors.append({"urn": item.urn, "message": "字段 URN 不属于当前表"})
                    continue
                try:
                    saved.append(
                        await self._upsert_field_annotation_without_commit(
                            session,
                            urn=item.urn,
                            payload=item.annotation,
                            operator_id=operator_id,
                            now=now,
                        )
                    )
                except Exception as exc:  # noqa: BLE001 - 批量接口必须逐字段收集错误
                    errors.append({"urn": item.urn, "message": str(exc)})
            if errors:
                await session.rollback()
                raise AnnotationBatchError("表内批量标注失败", detail={"errors": errors})
            await session.commit()
        except AnnotationBatchError:
            raise
        except Exception:
            await session.rollback()
            raise
        return TableFieldAnnotationsOut(
            table_urn=table_urn,
            items=[_annotation_out(annotation) for annotation in saved],
        )

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

    async def _upsert_field_annotation_without_commit(
        self,
        session: AnnotationSession,
        *,
        urn: str,
        payload: FieldAnnotationPayload,
        operator_id: int | None,
        now: datetime,
    ) -> AssetAnnotation:
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
        return annotation

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


def _belongs_to_table(urn: str, table_urn: str) -> bool:
    return urn.startswith(f"{table_urn}:") and urn != table_urn
