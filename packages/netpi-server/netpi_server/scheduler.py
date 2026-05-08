"""Background task scheduler for periodic network tests."""
import asyncio
import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Callable

from netpi_core.config import get_settings

logger = logging.getLogger("netpi.scheduler")


@dataclass
class ScheduledTest:
    id: str
    name: str
    interval_sec: int
    coro_factory: Callable
    last_run: datetime | None = None
    last_result: dict | None = None
    last_error: str | None = None
    enabled: bool = True


class TestScheduler:
    """Lightweight asyncio scheduler for recurring network diagnostics."""

    def __init__(self) -> None:
        self._tasks: dict[str, asyncio.Task] = {}
        self._schedules: dict[str, ScheduledTest] = {}
        self._event_callbacks: list[Callable[[str, dict], None]] = []
        # signature: (test_id, result_dict)

    def register(
        self,
        test_id: str,
        name: str,
        interval_sec: int,
        coro_factory: Callable,
        enabled: bool = True,
    ) -> ScheduledTest:
        schedule = ScheduledTest(
            id=test_id,
            name=name,
            interval_sec=interval_sec,
            coro_factory=coro_factory,
            enabled=enabled,
        )
        self._schedules[test_id] = schedule
        logger.info("Registered scheduled test %s (%ds)", test_id, interval_sec)
        return schedule

    async def start(self, test_id: str | None = None) -> None:
        """Start scheduled tests. If test_id is None, starts all enabled."""
        ids = [test_id] if test_id else [s.id for s in self._schedules.values() if s.enabled]
        for tid in ids:
            if tid in self._tasks:
                continue
            self._tasks[tid] = asyncio.create_task(self._run_loop(tid))
            logger.info("Started scheduled test %s", tid)

    async def stop(self, test_id: str | None = None) -> None:
        ids = [test_id] if test_id else list(self._tasks.keys())
        for tid in ids:
            task = self._tasks.pop(tid, None)
            if task:
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass
                logger.info("Stopped scheduled test %s", tid)

    async def run_once(self, test_id: str) -> dict | None:
        """Execute a scheduled test immediately, outside its loop."""
        schedule = self._schedules.get(test_id)
        if not schedule:
            return None
        return await self._execute(schedule)

    async def _run_loop(self, test_id: str) -> None:
        schedule = self._schedules[test_id]
        while True:
            try:
                await asyncio.sleep(schedule.interval_sec)
                if not schedule.enabled:
                    continue
                await self._execute(schedule)
            except asyncio.CancelledError:
                break
            except Exception:
                logger.exception("Scheduler loop error for %s", test_id)
                await asyncio.sleep(5)

    async def _execute(self, schedule: ScheduledTest) -> dict:
        schedule.last_run = datetime.now(timezone.utc)
        try:
            result = await schedule.coro_factory()
            schedule.last_result = result
            schedule.last_error = None
            logger.info("Scheduled test %s completed: %s", schedule.id, result)
            for cb in self._event_callbacks:
                try:
                    cb(schedule.id, result)
                except Exception:
                    pass
            return result
        except Exception as exc:
            schedule.last_error = str(exc)
            logger.exception("Scheduled test %s failed", schedule.id)
            return {"error": str(exc)}

    def on_event(self, callback: Callable[[str, dict], None]) -> None:
        self._event_callbacks.append(callback)

    def list_schedules(self) -> list[dict]:
        return [
            {
                "id": s.id,
                "name": s.name,
                "interval_sec": s.interval_sec,
                "enabled": s.enabled,
                "last_run": s.last_run.isoformat() if s.last_run else None,
                "last_result": s.last_result,
                "last_error": s.last_error,
            }
            for s in self._schedules.values()
        ]


_scheduler: TestScheduler | None = None


def get_scheduler() -> TestScheduler:
    global _scheduler
    if _scheduler is None:
        _scheduler = TestScheduler()
    return _scheduler



