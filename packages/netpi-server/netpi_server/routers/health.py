"""Health and readiness probes."""
import logging
import os
from datetime import datetime, timezone

from fastapi import APIRouter

from netpi_core.config import get_settings

router = APIRouter(tags=["health"])
logger = logging.getLogger("netpi.health")


@router.get("/health")
async def health_check():
    """Liveness probe \u2014 returns 200 if the process is running."""
    return {
        "status": "ok",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "version": "0.3.0",
    }


@router.get("/ready")
async def readiness_check():
    """Readiness probe \u2014 checks critical dependencies."""
    settings = get_settings()
    checks = {
        "data_dir_writable": False,
        "capture_dir_writable": False,
    }

    try:
        checks["data_dir_writable"] = os.access(settings.data_dir, os.W_OK)
    except Exception as exc:
        logger.warning("Data dir check failed: %s", exc)

    try:
        checks["capture_dir_writable"] = os.access(settings.capture_dir, os.W_OK)
    except Exception as exc:
        logger.warning("Capture dir check failed: %s", exc)

    all_ready = all(checks.values())

    return {
        "status": "ready" if all_ready else "not_ready",
        "checks": checks,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }



