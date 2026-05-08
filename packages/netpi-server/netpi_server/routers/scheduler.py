"""Scheduled test management endpoints."""
import logging

from fastapi import APIRouter, HTTPException

from netpi_server.scheduler import get_scheduler

router = APIRouter(tags=["scheduler"])
logger = logging.getLogger("netpi.scheduler.api")


@router.get("/scheduler")
async def list_schedules():
    """List all registered scheduled tests and their last results."""
    return get_scheduler().list_schedules()


@router.post("/scheduler/{test_id}/start")
async def start_schedule(test_id: str):
    """Start a scheduled test loop."""
    await get_scheduler().start(test_id)
    return {"status": "started", "test_id": test_id}


@router.post("/scheduler/{test_id}/stop")
async def stop_schedule(test_id: str):
    """Stop a scheduled test loop."""
    await get_scheduler().stop(test_id)
    return {"status": "stopped", "test_id": test_id}


@router.post("/scheduler/{test_id}/run")
async def run_once(test_id: str):
    """Execute a scheduled test immediately."""
    result = await get_scheduler().run_once(test_id)
    if result is None:
        raise HTTPException(status_code=404, detail="Scheduled test not found")
    return result



