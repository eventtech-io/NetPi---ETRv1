"""Backend registry."""
import uuid
from datetime import datetime, timezone
from netpi_core.models.cabletest import CableTestResult, CableStatus
from .base import CableTestBackend
from .ethtool_backend import EthtoolCableTestBackend

class CableTestRegistry:
    def __init__(self) -> None:
        self._backends: list[CableTestBackend] = [EthtoolCableTestBackend()]

    def register(self, backend: CableTestBackend) -> None:
        self._backends.append(backend)

    async def find_backend(self, port_id: str) -> CableTestBackend | None:
        for backend in self._backends:
            if await backend.is_available(port_id):
                return backend
        return None

    async def test(self, port_id: str) -> CableTestResult:
        backend = await self.find_backend(port_id)
        if backend is None:
            return CableTestResult(
                id=str(uuid.uuid4()),
                port_id=port_id,
                backend="none",
                timestamp=datetime.now(timezone.utc),
                status=CableStatus.UNKNOWN,
                pairs=[],
                duration_ms=0,
            )
        return await backend.test(port_id)

_registry: CableTestRegistry | None = None

def get_registry() -> CableTestRegistry:
    global _registry
    if _registry is None:
        _registry = CableTestRegistry()
    return _registry
