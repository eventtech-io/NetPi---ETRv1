"""Request logging and metrics middleware."""
import logging
import time
from typing import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

logger = logging.getLogger("netpi.request")
_metrics = {
    "requests_total": 0,
    "requests_by_path": {},
    "errors_total": 0,
}


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        start = time.perf_counter()
        _metrics["requests_total"] += 1
        path = request.url.path

        try:
            response = await call_next(request)
        except Exception:
            _metrics["errors_total"] += 1
            logger.exception("Unhandled exception", extra={"path": path})
            raise

        duration_ms = (time.perf_counter() - start) * 1000
        status = response.status_code
        _metrics["requests_by_path"][path] = _metrics["requests_by_path"].get(path, 0) + 1

        level = logging.WARNING if status >= 400 else logging.INFO
        logger.log(
            level,
            "%s %s -> %s in %.2fms",
            request.method,
            path,
            status,
            duration_ms,
            extra={
                "method": request.method,
                "path": path,
                "status_code": status,
                "duration_ms": duration_ms,
            },
        )
        return response


def get_metrics() -> dict:
    return _metrics.copy()



