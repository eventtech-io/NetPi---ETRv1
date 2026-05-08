"""Dummy DMX backend for testing without hardware."""
import asyncio
from datetime import datetime, timezone
from typing import Callable
from netpi_core.models.dmx import DMXPacket, DMXPacketTiming, DMXUniverse
from .base import DMXBackend

class DummyDMXBackend(DMXBackend):
    name = "dummy"
    def __init__(self) -> None:
        self._open = False
        self._rx_task: asyncio.Task | None = None
        self._rx_callback: Callable[[DMXPacket], None] | None = None
        self._rx_running = False
    async def open(self) -> bool:
        self._open = True; return True
    async def close(self) -> None:
        self._open = False; await self.stop_receiver()
    async def is_available(self) -> bool:
        return True
    async def send_universe(self, universe: DMXUniverse) -> bool:
        if not self._open: return False
        await asyncio.sleep(0.001); return True
    async def start_receiver(self, callback: Callable[[DMXPacket], None]) -> None:
        self._rx_callback = callback; self._rx_running = True
        self._rx_task = asyncio.create_task(self._rx_loop())
    async def stop_receiver(self) -> None:
        self._rx_running = False
        if self._rx_task:
            self._rx_task.cancel()
            try: await self._rx_task
            except asyncio.CancelledError: pass
            self._rx_task = None
    async def _rx_loop(self) -> None:
        while self._rx_running:
            await asyncio.sleep(0.025)
            packet = DMXPacket(
                timestamp=datetime.now(timezone.utc), start_code=0x00,
                slots=[0] * 512,
                timing=DMXPacketTiming(break_us=176.0, mab_us=12.0, slot_count=512, packet_rate_hz=44.0),
            )
            if self._rx_callback:
                try: self._rx_callback(packet)
                except Exception: pass
    async def send_rdm_discovery(self) -> list[str]: return []
    async def send_rdm_get(self, uid: str, pid: int, sub_device: int = 0) -> bytes | None: return None
    async def send_rdm_set(self, uid: str, pid: int, data: bytes, sub_device: int = 0) -> bool: return False
