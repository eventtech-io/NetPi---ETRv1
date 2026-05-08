"""Simple API key authentication for NetPi."""
from fastapi import HTTPException, Security, status
from fastapi.security.api_key import APIKeyHeader

from netpi_core.config import get_settings

_api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


async def require_api_key(api_key: str | None = Security(_api_key_header)) -> None:
    """FastAPI dependency: enforce API key when NETPI_API_KEY is configured."""
    expected = get_settings().api_key
    if not expected:
        return  # Auth disabled
    if not api_key or api_key != expected:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API key. Set the X-API-Key header.",
        )


def auth_enabled() -> bool:
    return bool(get_settings().api_key)



