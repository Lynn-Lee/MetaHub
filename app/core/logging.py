"""Loguru 日志配置，并接管标准库 logging（uvicorn / sqlalchemy 都走 stdlib）。"""

import logging
import sys
from types import FrameType
from typing import Any

from loguru import logger

from app.core.config import Settings

_STDLIB_LOGGERS = (
    "uvicorn",
    "uvicorn.error",
    "uvicorn.access",
    "sqlalchemy.engine",
    "alembic",
    "apscheduler",
)


class _InterceptHandler(logging.Handler):
    """把标准库 logging 的记录转发给 Loguru，保证日志格式统一。"""

    def emit(self, record: logging.LogRecord) -> None:
        try:
            level: str | int = logger.level(record.levelname).name
        except ValueError:
            level = record.levelno

        # 回溯到真正的调用点，否则所有日志的来源都会显示成本文件
        frame: FrameType | None = logging.currentframe()
        depth = 2
        while frame and frame.f_code.co_filename == logging.__file__:
            frame = frame.f_back
            depth += 1

        logger.opt(depth=depth, exception=record.exc_info).log(level, record.getMessage())


def setup_logging(settings: Settings) -> None:
    logger.remove()

    level = "DEBUG" if settings.DEBUG else "INFO"
    common: dict[str, Any] = {"level": level, "backtrace": not settings.is_prod, "diagnose": False}

    if settings.is_prod:
        # 生产走结构化日志，便于 ELK 解析
        logger.add(sys.stdout, serialize=True, **common)
    else:
        logger.add(
            sys.stdout,
            format=(
                "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
                "<level>{level: <8}</level> | "
                "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - "
                "<level>{message}</level>"
            ),
            **common,
        )

    logging.basicConfig(handlers=[_InterceptHandler()], level=0, force=True)
    for name in _STDLIB_LOGGERS:
        std_logger = logging.getLogger(name)
        std_logger.handlers = [_InterceptHandler()]
        std_logger.propagate = False
