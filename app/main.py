"""FastAPI 应用入口。"""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from loguru import logger

from app.api.v1.router import api_router
from app.core.config import get_settings
from app.core.exceptions import register_exception_handlers
from app.core.logging import setup_logging
from app.db.session import close_pools, init_pools
from app.services.sync_scheduler import MetadataSyncScheduler


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    # get_settings() 放在最前：配置缺失或非法时在这里就抛，不会带病启动
    settings = get_settings()
    setup_logging(settings)
    logger.info("启动 {} env={} debug={}", settings.APP_NAME, settings.ENV, settings.DEBUG)

    sync_scheduler: MetadataSyncScheduler | None = None
    init_pools(settings)
    try:
        sync_scheduler = MetadataSyncScheduler()
        await sync_scheduler.start()
        yield
    finally:
        if sync_scheduler is not None:
            sync_scheduler.shutdown()
        await close_pools()
        logger.info("已停止 {}", settings.APP_NAME)


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(
        title="MetaHub 元数据知识库",
        description="数据库元数据知识库 —— 表/字段元数据采集与业务语义标注平台",
        version="0.1.0",
        openapi_url=f"{settings.API_V1_PREFIX}/openapi.json",
        docs_url="/docs",
        redoc_url=None,
        lifespan=lifespan,
    )

    register_exception_handlers(app)
    app.include_router(api_router, prefix=settings.API_V1_PREFIX)
    return app


app = create_app()
