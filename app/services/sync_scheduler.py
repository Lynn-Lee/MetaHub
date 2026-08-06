"""同步调度服务（DEV-TASKS T3.5）。"""

from __future__ import annotations

from collections.abc import Callable
from contextlib import AbstractAsyncContextManager
from typing import Protocol, cast

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from sqlalchemy import select

from app.db.session import collector_session
from app.models.metadata import DataSource
from app.services.metadata_sync import MetadataSyncService, SyncSession


class SyncService(Protocol):
    async def sync_source(
        self,
        source_id: int,
        *,
        trigger_type: str,
        db_name: str | None = None,
        table_name: str | None = None,
    ) -> object: ...


class SchedulerBackend(Protocol):
    def add_job(
        self,
        func: Callable[..., object],
        trigger: object,
        *,
        id: str,
        args: list[object],
        replace_existing: bool,
        coalesce: bool,
        max_instances: int,
    ) -> None: ...

    def start(self) -> None: ...

    def shutdown(self, *, wait: bool) -> None: ...


SessionFactory = Callable[[], AbstractAsyncContextManager[SyncSession]]


class MetadataSyncScheduler:
    def __init__(
        self,
        *,
        session_factory: SessionFactory | None = None,
        sync_service: SyncService | None = None,
        scheduler: SchedulerBackend | None = None,
    ) -> None:
        self._session_factory = session_factory or cast(SessionFactory, collector_session)
        self._sync_service = sync_service or MetadataSyncService()
        self._scheduler = scheduler or cast(SchedulerBackend, AsyncIOScheduler(timezone="UTC"))

    async def start(self) -> None:
        await self.refresh_jobs()
        self._scheduler.start()

    def shutdown(self) -> None:
        self._scheduler.shutdown(wait=False)

    async def refresh_jobs(self) -> None:
        async with self._session_factory() as session:
            result = await session.execute(
                select(DataSource).where(
                    DataSource.enabled.is_(True),
                    DataSource.sync_cron.is_not(None),
                )
            )
            sources = result.scalars().all()

        for source in sources:
            self._scheduler.add_job(
                self.run_source,
                CronTrigger.from_crontab(source.sync_cron, timezone="UTC"),
                id=_job_id(source.id),
                args=[source.id],
                replace_existing=True,
                coalesce=True,
                max_instances=1,
            )

    async def run_source(self, source_id: int) -> object:
        return await self._sync_service.sync_source(source_id, trigger_type="CRON")

    async def trigger_manual(
        self,
        source_id: int,
        *,
        db_name: str | None = None,
        table_name: str | None = None,
    ) -> object:
        return await self._sync_service.sync_source(
            source_id,
            trigger_type="MANUAL",
            db_name=db_name,
            table_name=table_name,
        )


def _job_id(source_id: int) -> str:
    return f"sync-source-{source_id}"
