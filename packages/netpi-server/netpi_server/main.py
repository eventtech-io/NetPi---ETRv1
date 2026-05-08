"""NetPi FastAPI application entrypoint."""
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware

from netpi_core.config import get_settings
from netpi_core.logging import configure_logging
from netpi_db.database import get_db
from netpi_db.migrations import MigrationManager
from netpi_db.repositories.capture import CaptureSessionRepository
from netpi_analyzer.capture.engine import get_engine as get_capture_engine
from netpi_server.scheduler import get_scheduler

from .auth import require_api_key, auth_enabled
from .middleware import RequestLoggingMiddleware
from .routers import (
    capture, discovery, tests, cabletest, system, dmx,
    health, metrics, scenes, scheduler, topology, osc, oca,
)
from .websocket.events import ws_router

logger = logging.getLogger("netpi.main")


def _register_default_schedules():
    """Register built-in scheduled tests on startup."""
    sched = get_scheduler()

    # Example: periodic ping sweep of default gateway
    async def _ping_gateway():
        from netpi_tests.ping import ping_host
        # Discover gateway via system info
        import socket
        gateway = "192.168.1.1"  # Simplified; real impl would parse routes
        return await ping_host(gateway, count=3, timeout=2.0)

    sched.register(
        test_id="ping_gateway",
        name="Gateway Ping",
        interval_sec=60,
        coro_factory=_ping_gateway,
        enabled=False,  # User must explicitly enable
    )

    # Example: periodic speedtest (expensive, disabled by default)
    async def _speedtest():
        from netpi_tests.speedtest import run_speedtest
        return await run_speedtest()

    sched.register(
        test_id="speedtest",
        name="Internet Speedtest",
        interval_sec=3600,
        coro_factory=_speedtest,
        enabled=False,
    )


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan - startup and shutdown hooks."""
    settings = get_settings()
    configure_logging(level=settings.log_level, json_format=False)
    logger.info("NetPi starting up - log level %s", settings.log_level)

    # 1. Initialize database and run migrations
    try:
        db = get_db()
        await db.connect()
        migrator = MigrationManager(db)
        await migrator.apply_all()
        logger.info("Database migrations complete")

        # 2. Attach persistence to capture engine
        capture_repo = CaptureSessionRepository(db)
        get_capture_engine().set_repository(capture_repo)
    except Exception:
        logger.exception("Database initialization failed")

    # 3. Auto-detect DMX backend
    try:
        from netpi_dmx.engine import get_engine as get_dmx_engine
        await get_dmx_engine().auto_detect_backend()
        logger.info("DMX backend auto-detected")
    except Exception:
        logger.warning("DMX backend auto-detection failed", exc_info=True)

    # 4. Register default scheduled tests
    try:
        _register_default_schedules()
        logger.info("Default scheduled tests registered")
    except Exception:
        logger.warning("Scheduler registration failed", exc_info=True)

    yield

    # Shutdown
    try:
        await get_scheduler().stop()
        logger.info("Scheduled tests stopped")
    except Exception:
        pass

    try:
        from netpi_dmx.engine import get_engine as get_dmx_engine
        engine = get_dmx_engine()
        for uni_id in list(engine._tx_tasks):
            await engine.stop_transmit(uni_id)
        logger.info("DMX transmission tasks stopped")
    except Exception:
        logger.warning("Error stopping DMX tasks", exc_info=True)

    try:
        from netpi_osc.engine import get_engine as get_osc_engine
        await get_osc_engine().stop_listener()
        logger.info("OSC listener stopped")
    except Exception:
        logger.warning("Error stopping OSC listener", exc_info=True)

    try:
        await get_db().close()
        logger.info("Database connection closed")
    except Exception:
        pass


settings = get_settings()

app = FastAPI(
    title="NetPi",
    description="Modern network analyzer for Raspberry Pi 4/5 with DMX512/RDM",
    version="0.3.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(RequestLoggingMiddleware)

_global_deps = [Depends(require_api_key)]

# Open endpoints (no auth required)
app.include_router(health.router, prefix="/api/v1")
app.include_router(metrics.router, prefix="/api/v1")

# Protected endpoints
app.include_router(system.router, prefix="/api/v1", dependencies=_global_deps)
app.include_router(capture.router, prefix="/api/v1", dependencies=_global_deps)
app.include_router(discovery.router, prefix="/api/v1", dependencies=_global_deps)
app.include_router(topology.router, prefix="/api/v1", dependencies=_global_deps)
app.include_router(tests.router, prefix="/api/v1", dependencies=_global_deps)
app.include_router(cabletest.router, prefix="/api/v1", dependencies=_global_deps)
app.include_router(dmx.router, prefix="/api/v1", dependencies=_global_deps)
app.include_router(scenes.router, prefix="/api/v1", dependencies=_global_deps)
app.include_router(scheduler.router, prefix="/api/v1", dependencies=_global_deps)
app.include_router(osc.router, prefix="/api/v1", dependencies=_global_deps)
app.include_router(oca.router, prefix="/api/v1", dependencies=_global_deps)
app.include_router(ws_router, prefix="/api/v1")


@app.get("/", tags=["system"])
async def root():
    return {
        "name": "NetPi",
        "version": "0.3.0",
        "status": "ok",
        "auth_enabled": auth_enabled(),
        "features": [
            "packet_capture",
            "cable_test",
            "network_discovery",
            "network_tests",
            "dmx512",
            "rdm",
            "dmx_scenes",
            "osc",
            "oca_aes70",
            "scheduled_tests",
            "topology_export",
        ],
    }


def main():
    import uvicorn
    uvicorn.run(
        "netpi_server.main:app",
        host="0.0.0.0",
        port=8080,
        reload=False,
        access_log=False,
    )


if __name__ == "__main__":
    main()



