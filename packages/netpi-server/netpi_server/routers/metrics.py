"""Internal metrics endpoint."""
from fastapi import APIRouter

from netpi_server.middleware import get_metrics

router = APIRouter(tags=["metrics"])


@router.get("/metrics")
async def metrics():
    """Return application metrics in Prometheus-like JSON format."""
    m = get_metrics()
    return {
        "netpi_requests_total": m["requests_total"],
        "netpi_errors_total": m["errors_total"],
        "netpi_requests_by_path": m["requests_by_path"],
    }



