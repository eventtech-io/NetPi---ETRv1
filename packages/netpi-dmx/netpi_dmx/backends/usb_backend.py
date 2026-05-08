"""DMX backend for USB DMX interfaces (Enttec USB Pro, DMXKing, etc.)."""
import asyncio
from datetime import datetime, timezone
from typing import Callable

from netpi_core.models.dmx import DMXPacket, DMXPacketTiming, DMXUniverse
from .base import DMXBackend


class USBDMXBackend(DMXBackend):
    """USB DMX interface backend.

    Supports Enttec USB Pro protocol and similar FTDI-based adapters.
    These devices handle DMX break/MAB timing in firmware.

    BUG-FIX: _send_message() and serial reads now run in a thread executor
    so they don't block the asyncio event loop.
    """

    name = "usb"

    _LABEL_GET_WIDGET_PARAMS = 0x03
    _LABEL_SEND_DMX = 0x06
    _LABEL_RECEIVE_DMX = 0x05

    def __init__(self, port: str = "/dev/ttyUSB0") -> None:
        self.port = port
        self._serial = None
        self._rx_task: asyncio.Task | None = None
        self._rx_running = False
        self._rx_callback: Callable[[DMXPacket], None] | None = None

    async def is_available(self) -> bool:
        try:
            import serial.tools.list_ports
            ports = [p.device for p in serial.tools.list_ports.comports()]
            return self.port in ports
        except Exception:
            return False

    async def open(self) -> bool:
        loop = asyncio.get_event_loop()
        try:
            self._serial = await loop.run_in_executor(None, self._open_serial)
            if self._serial:
                # Probe: request widget parameters to confirm it's alive
                await loop.run_in_executor(
                    None,
                    lambda: self._write_message(
                        self._LABEL_GET_WIDGET_PARAMS, bytes([0x00, 0x00, 0x00, 0x00])
                    ),
                )
            return self._serial is not None
        except Exception:
            return False

    def _open_serial(self):
        try:
            import serial
            return serial.Serial(
                self.port,
                baudrate=115200,
                bytesize=8,
                parity="N",
                stopbits=1,
                timeout=0,
            )
        except Exception:
            return None

    async def close(self) -> None:
        await self.stop_receiver()
        ser = self._serial
        self._serial = None
        if ser:
            ser.close()

    async def send_universe(self, universe: DMXUniverse) -> bool:
        if not self._serial:
            return False
        data = bytes(universe.channels[:512])
        loop = asyncio.get_event_loop()
        # BUG-FIX: was calling _send_message synchronously on the event loop thread
        await loop.run_in_executor(None, self._write_message, self._LABEL_SEND_DMX, data)
        return True

    def _write_message(self, label: int, data: bytes) -> None:
        """Write an Enttec USB Pro framed message (runs in thread executor)."""
        ser = self._serial
        if not ser:
            return
        header = bytes([0x7E, label, len(data) & 0xFF, (len(data) >> 8) & 0xFF])
        footer = bytes([0xE7])
        ser.write(header + data + footer)
        ser.flush()

    async def start_receiver(self, callback: Callable[[DMXPacket], None]) -> None:
        self._rx_callback = callback
        self._rx_running = True
        self._rx_task = asyncio.create_task(self._rx_loop())

    async def stop_receiver(self) -> None:
        self._rx_running = False
        if self._rx_task:
            self._rx_task.cancel()
            try:
                await self._rx_task
            except asyncio.CancelledError:
                pass
            self._rx_task = None

    async def _rx_loop(self) -> None:
        loop = asyncio.get_event_loop()
        buf = bytearray()

        while self._rx_running:
            # BUG-FIX: capture local reference to avoid lambda closing over
            # self._serial which may be set to None during close()
            ser = self._serial
            if not ser:
                break
            try:
                waiting = ser.in_waiting
                if waiting:
                    data = await loop.run_in_executor(None, lambda: ser.read(waiting))
                else:
                    await asyncio.sleep(0.001)
                    continue

                buf.extend(data)

                while True:
                    start = buf.find(0x7E)
                    if start == -1:
                        buf.clear()
                        break
                    if len(buf) < start + 4:
                        break
                    label = buf[start + 1]
                    length = buf[start + 2] | (buf[start + 3] << 8)
                    if len(buf) < start + 5 + length:
                        break
                    if buf[start + 4 + length] != 0xE7:
                        buf = buf[start + 1:]
                        continue

                    payload = bytes(buf[start + 4:start + 4 + length])
                    buf = buf[start + 5 + length:]

                    if label == self._LABEL_RECEIVE_DMX and self._rx_callback:
                        packet = DMXPacket(
                            timestamp=datetime.now(timezone.utc),
                            start_code=payload[0] if payload else 0x00,
                            slots=list(payload[1:]) if len(payload) > 1 else [],
                            timing=DMXPacketTiming(
                                break_us=176.0,
                                mab_us=12.0,
                                slot_count=len(payload) - 1,
                            ),
                        )
                        try:
                            self._rx_callback(packet)
                        except Exception:
                            pass

            except Exception:
                await asyncio.sleep(0.001)

    async def send_rdm_discovery(self) -> list[str]:
        return []

    async def send_rdm_get(self, uid: str, pid: int, sub_device: int = 0) -> bytes | None:
        return None

    async def send_rdm_set(self, uid: str, pid: int, data: bytes, sub_device: int = 0) -> bool:
        return False
