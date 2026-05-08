"""DMX engine — universe management, transmission, reception, testing."""
import asyncio
import uuid
from datetime import datetime, timezone
from typing import Callable

from netpi_core.models.dmx import (
    DMXUniverse,
    DMXChannel,
    DMXPacket,
    DMXFlickerEvent,
    DMXCableTestResult,
    DIPSwitchConfig,
    RDMDevice,
)
from .backends.base import DMXBackend
from .backends.dummy_backend import DummyDMXBackend
from .backends.uart_backend import UARTDMXBackend
from .backends.usb_backend import USBDMXBackend


class DMXEngine:
    """High-level DMX engine managing universes, TX, RX, and testing."""

    def __init__(self) -> None:
        self._backend: DMXBackend | None = None
        self._universes: dict[str, DMXUniverse] = {}
        # BUG-FIX: one task per universe, not a single shared task/flag
        self._tx_tasks: dict[str, asyncio.Task] = {}
        self._rx_packets: list[DMXPacket] = []
        self._rx_max_history = 100
        self._flicker_callbacks: list[Callable[[DMXFlickerEvent], None]] = []
        self._last_rx_slots: list[int] | None = None

    async def auto_detect_backend(self) -> DMXBackend:
        """Auto-detect available DMX hardware, fallback to dummy."""
        candidates: list[DMXBackend] = [
            USBDMXBackend("/dev/ttyUSB0"),
            USBDMXBackend("/dev/ttyUSB1"),
            UARTDMXBackend("/dev/ttyAMA0"),
            UARTDMXBackend("/dev/ttyS0"),
        ]
        for backend in candidates:
            if await backend.is_available():
                if await backend.open():
                    self._backend = backend
                    return backend
        dummy = DummyDMXBackend()
        await dummy.open()
        self._backend = dummy
        return dummy

    async def set_backend(self, backend: DMXBackend) -> None:
        if self._backend:
            await self._backend.close()
        self._backend = backend
        await backend.open()

    def get_backend(self) -> DMXBackend | None:
        return self._backend

    # ------------------------------------------------------------------
    # Universe Management
    # ------------------------------------------------------------------

    def create_universe(self, name: str = "Universe 1") -> DMXUniverse:
        uni = DMXUniverse(
            id=str(uuid.uuid4()),
            name=name,
            channels=[0] * 512,
        )
        self._universes[uni.id] = uni
        return uni

    def get_universe(self, uni_id: str) -> DMXUniverse | None:
        return self._universes.get(uni_id)

    def list_universes(self) -> list[DMXUniverse]:
        return list(self._universes.values())

    def set_channel(self, uni_id: str, channel: int, value: int) -> bool:
        uni = self._universes.get(uni_id)
        if not uni or channel < 1 or channel > 512:
            return False
        uni.channels[channel - 1] = max(0, min(255, value))
        uni.last_updated = datetime.now(timezone.utc)
        return True

    def set_channels(self, uni_id: str, channels: list[DMXChannel]) -> bool:
        uni = self._universes.get(uni_id)
        if not uni:
            return False
        for ch in channels:
            if 1 <= ch.channel <= 512:
                uni.channels[ch.channel - 1] = max(0, min(255, ch.value))
        uni.last_updated = datetime.now(timezone.utc)
        return True

    def get_channel(self, uni_id: str, channel: int) -> int | None:
        uni = self._universes.get(uni_id)
        if not uni or channel < 1 or channel > 512:
            return None
        return uni.channels[channel - 1]

    # ------------------------------------------------------------------
    # Transmission — one asyncio.Task per universe
    # ------------------------------------------------------------------

    async def start_transmit(self, uni_id: str, rate_hz: float = 44.0) -> bool:
        """Start continuously transmitting a universe.

        BUG-FIX: was a single _tx_task / _tx_running flag shared across all
        universes.  Now each universe owns its own Task stored in _tx_tasks.
        """
        uni = self._universes.get(uni_id)
        if not uni or not self._backend:
            return False
        # Stop any existing task for this universe before starting a new one
        await self.stop_transmit(uni_id)
        uni.is_transmitting = True
        uni.tx_rate_hz = rate_hz
        self._tx_tasks[uni_id] = asyncio.create_task(self._tx_loop(uni_id, rate_hz))
        return True

    async def stop_transmit(self, uni_id: str) -> bool:
        uni = self._universes.get(uni_id)
        if uni:
            uni.is_transmitting = False
        task = self._tx_tasks.pop(uni_id, None)
        if task:
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
        return True

    async def _tx_loop(self, uni_id: str, rate_hz: float) -> None:
        interval = 1.0 / rate_hz
        while True:
            uni = self._universes.get(uni_id)
            if uni and self._backend:
                await self._backend.send_universe(uni)
            await asyncio.sleep(interval)

    async def send_once(self, uni_id: str) -> bool:
        uni = self._universes.get(uni_id)
        if not uni or not self._backend:
            return False
        return await self._backend.send_universe(uni)

    # ------------------------------------------------------------------
    # Reception
    # ------------------------------------------------------------------

    async def start_receive(self) -> bool:
        if not self._backend:
            return False
        await self._backend.start_receiver(self._on_packet_received)
        return True

    async def stop_receive(self) -> bool:
        if not self._backend:
            return False
        await self._backend.stop_receiver()
        return True

    def _on_packet_received(self, packet: DMXPacket) -> None:
        self._rx_packets.append(packet)
        if len(self._rx_packets) > self._rx_max_history:
            self._rx_packets.pop(0)
        self._check_flicker(packet)

    def get_received_packets(self) -> list[DMXPacket]:
        return list(self._rx_packets)

    def get_latest_packet(self) -> DMXPacket | None:
        return self._rx_packets[-1] if self._rx_packets else None

    # ------------------------------------------------------------------
    # Flicker Finder
    # ------------------------------------------------------------------

    def _check_flicker(self, packet: DMXPacket) -> None:
        if self._last_rx_slots is None:
            self._last_rx_slots = list(packet.slots)
            return
        for i, (old, new) in enumerate(zip(self._last_rx_slots, packet.slots)):
            if old != new:
                event = DMXFlickerEvent(
                    channel=i + 1,
                    old_value=old,
                    new_value=new,
                    timestamp=packet.timestamp,
                )
                for cb in self._flicker_callbacks:
                    try:
                        cb(event)
                    except Exception:
                        pass
        self._last_rx_slots = list(packet.slots)

    def on_flicker(self, callback: Callable[[DMXFlickerEvent], None]) -> None:
        self._flicker_callbacks.append(callback)

    # ------------------------------------------------------------------
    # RDM (stub — full E1.20 implementation planned)
    # ------------------------------------------------------------------

    async def rdm_discover(self) -> list[RDMDevice]:
        if not self._backend:
            return []
        uids = await self._backend.send_rdm_discovery()
        return [RDMDevice(uid=uid, last_seen=datetime.now(timezone.utc)) for uid in uids]

    # ------------------------------------------------------------------
    # DMX Cable Test (XLR loopback)
    # ------------------------------------------------------------------

    async def test_dmx_cable(self, port_id: str) -> DMXCableTestResult:
        """Test a DMX XLR cable using send+receive loopback.

        BUG-FIX: now starts receive mode internally before sending the test
        pattern, so get_latest_packet() actually has a chance to return data.
        Previously it always returned 'open' because RX was never started.

        Note: loopback only works if a loopback plug or self-terminating
        transceiver is used.  Without hardware loopback, result is 'open'.
        """
        result = DMXCableTestResult(
            id=str(uuid.uuid4()),
            port_id=port_id,
            timestamp=datetime.now(timezone.utc),
            status="unknown",
        )

        if not self._backend:
            result.status = "no_backend"
            return result

        test_universe = DMXUniverse(
            id="cable_test",
            name="Cable Test",
            channels=[0] * 512,
        )
        test_pattern = [0x55, 0xAA, 0xFF, 0x00, 0x12, 0x34, 0x56, 0x78]
        for i, val in enumerate(test_pattern):
            test_universe.channels[i] = val

        # Start RX so we can read back what we send
        was_receiving = bool(self._rx_packets) or self._backend is not None
        rx_started_here = False
        if not self._rx_packets:
            await self._backend.start_receiver(self._on_packet_received)
            rx_started_here = True

        await self._backend.send_universe(test_universe)
        await asyncio.sleep(0.05)  # Give hardware time to loop back

        latest = self.get_latest_packet()
        if latest and len(latest.slots) >= len(test_pattern):
            received = latest.slots[:len(test_pattern)]
            if received == test_pattern:
                result.loopback_detected = True
                result.status = "ok"
                result.pin2_data_minus = True
                result.pin3_data_plus = True
                result.pin1_shield = True
            else:
                result.status = "fault"
                result.shorts.append("data_corruption")
        else:
            result.status = "open"

        if rx_started_here:
            await self._backend.stop_receiver()

        return result

    # ------------------------------------------------------------------
    # DIP Switch Calculator
    # ------------------------------------------------------------------

    @staticmethod
    def calculate_dip_switches(address: int, step_size: int = 1) -> DIPSwitchConfig:
        """Calculate DIP switch positions for a DMX start address.

        Standard 9-switch DIP: switches 1–9 represent binary weights 1–256.
        Convention: address 1 = all switches OFF (0-indexed representation).

        BUG-FIX: previous code did format(address, "09b") which overflows for
        address 512 (requires 10 bits).  The correct encoding is (address-1)
        in 9-bit binary, giving address 512 → "111111111" (all switches ON).
        """
        return DMXUniverse.calculate_dip_switches(address, step_size)

    # ------------------------------------------------------------------
    # Fixture Library
    # ------------------------------------------------------------------

    def add_fixture_profile(self, fixture_id: str, profile: dict) -> None:
        pass  # Delegate to fixtures module; engine doesn't own profiles

    def get_fixture_profile(self, fixture_id: str) -> dict | None:
        from netpi_dmx.fixtures import get_profile
        return get_profile(fixture_id)

    def list_fixture_profiles(self) -> list[dict]:
        from netpi_dmx.fixtures import list_profiles
        return list_profiles()


_engine: DMXEngine | None = None


def get_engine() -> DMXEngine:
    global _engine
    if _engine is None:
        _engine = DMXEngine()
    return _engine
