from abc import ABC, abstractmethod
from netpi_core.models.cabletest import CableTestResult
class CableTestBackend(ABC):
    name: str = "abstract"
    @abstractmethod
    async def test(self, port_id: str) -> CableTestResult: ...
    @abstractmethod
    async def is_available(self, port_id: str) -> bool: ...
