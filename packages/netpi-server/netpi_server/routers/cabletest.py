"""Cable test endpoints."""
from fastapi import APIRouter, HTTPException

import netpi_cabletester.registry as cable_registry
from netpi_core.models.cabletest import CableTestResult
from netpi_db.database import get_db
from netpi_db.repositories.cabletest import CableTestRepository

router = APIRouter(tags=["cabletest"])


@router.get("/cabletest/ports")
async def list_testable_ports():
    """List interfaces that support cable testing."""
    from netpi_server.routers.system import _get_interfaces
    interfaces = await _get_interfaces()
    return [iface for iface in interfaces if iface.supports_cable_test]


@router.post("/cabletest/ports/{port}/test", response_model=CableTestResult)
async def run_cable_test(port: str):
    """Run a cable test on the specified port and persist the result."""
    registry = cable_registry.get_registry()
    backend = await registry.find_backend(port)
    if backend is None:
        raise HTTPException(
            status_code=422,
            detail=f"No cable test backend available for interface '{port}'. "
                   "Only Pi 4/5 onboard Ethernet (eth0) is supported.",
        )
    result = await backend.test(port)

    # Persist result
    try:
        db = get_db()
        repo = CableTestRepository(db)
        await repo.save(result)
    except Exception:
        import logging
        logging.getLogger("netpi.cabletest").exception("Failed to persist cable test result")

    return result


@router.get("/cabletest/results/{result_id}")
async def get_cable_test_result(result_id: str):
    """Retrieve a persisted cable test result by ID."""
    try:
        db = get_db()
        repo = CableTestRepository(db)
        result = await repo.get(result_id)
        if result is None:
            raise HTTPException(status_code=404, detail="Cable test result not found")
        return result
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Database error: {exc}")


@router.get("/cabletest/ports/{port}/results")
async def list_cable_test_results(port: str, limit: int = 50):
    """List historical cable test results for a port."""
    try:
        db = get_db()
        repo = CableTestRepository(db)
        return await repo.list_by_port(port, limit=limit)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Database error: {exc}")



