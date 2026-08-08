"""基础查询接口（DEV-TASKS T6.2）。"""

from typing import Annotated

from fastapi import APIRouter, Depends, Query

from app.db.session import get_web_session
from app.schemas.metadata_queries import (
    ColumnOut,
    DataSourceOut,
    MetadataPage,
    SearchOut,
    TableDdlOut,
    TableOut,
)
from app.schemas.urns import ColumnUrn, TableUrn
from app.services.metadata_queries import MetadataQuerySession, SQLAlchemyMetadataQueryService

router = APIRouter(tags=["metadata"])


def get_metadata_query_service() -> SQLAlchemyMetadataQueryService:
    return SQLAlchemyMetadataQueryService()


@router.get("/datasources", response_model=MetadataPage[DataSourceOut], summary="数据源列表")
async def list_data_sources(
    session: Annotated[MetadataQuerySession, Depends(get_web_session)],
    service: Annotated[SQLAlchemyMetadataQueryService, Depends(get_metadata_query_service)],
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
) -> MetadataPage[DataSourceOut]:
    return await service.list_data_sources(session, page=page, page_size=page_size)


@router.get("/tables", response_model=MetadataPage[TableOut], summary="表列表或表详情")
async def list_tables(
    session: Annotated[MetadataQuerySession, Depends(get_web_session)],
    service: Annotated[SQLAlchemyMetadataQueryService, Depends(get_metadata_query_service)],
    urn: Annotated[TableUrn | None, Query(description="表 URN")] = None,
    source_id: Annotated[int | None, Query(ge=1)] = None,
    db_name: str | None = None,
    keyword: str | None = None,
    include_deleted: bool = False,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
) -> MetadataPage[TableOut]:
    return await service.list_tables(
        session,
        urn=urn,
        source_id=source_id,
        db_name=db_name,
        keyword=keyword,
        include_deleted=include_deleted,
        page=page,
        page_size=page_size,
    )


@router.get("/columns", response_model=MetadataPage[ColumnOut], summary="字段列表或字段详情")
async def list_columns(
    session: Annotated[MetadataQuerySession, Depends(get_web_session)],
    service: Annotated[SQLAlchemyMetadataQueryService, Depends(get_metadata_query_service)],
    urn: Annotated[ColumnUrn | None, Query(description="字段 URN")] = None,
    table_urn: Annotated[TableUrn | None, Query(description="表 URN")] = None,
    keyword: str | None = None,
    include_deleted: bool = False,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
) -> MetadataPage[ColumnOut]:
    return await service.list_columns(
        session,
        urn=urn,
        table_urn=table_urn,
        keyword=keyword,
        include_deleted=include_deleted,
        page=page,
        page_size=page_size,
    )


@router.get("/tables/ddl", response_model=TableDdlOut, summary="表 DDL")
async def get_table_ddl(
    session: Annotated[MetadataQuerySession, Depends(get_web_session)],
    service: Annotated[SQLAlchemyMetadataQueryService, Depends(get_metadata_query_service)],
    urn: Annotated[TableUrn, Query(description="表 URN")],
) -> TableDdlOut:
    return await service.get_table_ddl(session, urn=urn)


@router.get("/search", response_model=SearchOut, summary="全文检索")
async def search(
    session: Annotated[MetadataQuerySession, Depends(get_web_session)],
    service: Annotated[SQLAlchemyMetadataQueryService, Depends(get_metadata_query_service)],
    q: Annotated[str, Query(min_length=2, max_length=128)],
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
) -> SearchOut:
    return await service.search(session, query=q, page=page, page_size=page_size)
