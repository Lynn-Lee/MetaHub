"""健康检查（PRD §M12-3）。

同时探测 **两个数据库角色**——只探 web 角色的话，采集角色的凭证或权限出问题时
要等到夜间同步任务才暴露。
"""

import asyncio
from typing import Any

import redis.asyncio as aioredis
from fastapi import APIRouter, Response, status
from loguru import logger
from sqlalchemy import text

from app.core.config import get_settings
from app.db.session import collector_session, web_session

router = APIRouter(tags=["system"])


async def _check_db(which: str) -> tuple[str, bool, str | None]:
    ctx = web_session if which == "db_web" else collector_session
    try:
        async with ctx() as session:
            await session.execute(text("SELECT 1"))
        return which, True, None
    except Exception as exc:  # noqa: BLE001 - 健康检查需要吞掉所有异常并如实上报
        logger.warning("健康检查失败 component={} error={}", which, exc)
        return which, False, str(exc)


async def _check_redis() -> tuple[str, bool, str | None]:
    settings = get_settings()
    client = aioredis.from_url(str(settings.REDIS_URL))
    try:
        await client.ping()
        return "redis", True, None
    except Exception as exc:  # noqa: BLE001
        logger.warning("健康检查失败 component=redis error={}", exc)
        return "redis", False, str(exc)
    finally:
        await client.aclose()


@router.get("/health", summary="健康检查")
async def health(response: Response) -> dict[str, Any]:
    results = await asyncio.gather(_check_db("db_web"), _check_db("db_collector"), _check_redis())

    components = {name: {"ok": ok, **({"error": err} if err else {})} for name, ok, err in results}
    healthy = all(ok for _, ok, _ in results)

    if not healthy:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE

    return {
        "status": "ok" if healthy else "degraded",
        "app": get_settings().APP_NAME,
        "env": get_settings().ENV,
        "components": components,
    }
