"""DMX backend using Raspberry Pi UART + RS485 HAT via PySerial.

Requires:
  - RS485 HAT on GPIO14/15 (UART0)
  - dtoverlay=disable-bt in /boot/firmware/config.txt
  - init_uart_clock=16000000
  - User in dialout group (sudo usermod -a -G dialout netpi)
"""
import asyncio
import os
import time
from datetime import datetime, timezone
from typing import Callable

import serial

from netpi_core.models.dmx import DMXPacket, DMXPacketTiming, DMXUniverse
from .base import DMXBackend


class UARTDMXBackend(DMXBackend):
    """DMX via Pi UART (ttyAMA0) with RS485 transceiver, driven by PySerial.

    BUG-FIX (multiple):
      - Removed termios.BOTHER (not exposed by Python's termios)
      - Removed tty.tcsendbreak (doesn't exist in Python's tty module)
      - Removed hand-rolled termios2 struct (wrong field sizes)
      - Fixed lambda capturing self._fd by reference in run_in_executor
      - Blocking serial I/O now runs in executor threads
    """

    name = "uart"

    _DMX_BAUD = 250_000
    _BREAK_SECS = 176e-6   # 176 µs — minimum is 88 µs; longer is fine
    _MAB_SECS = 12e-6      # Mark After Break

    def __init__(self, port: str = "/dev/ttyAMA0") -> None:
        self.port = port
        self._serial: serial.Serial | None = None
        self._tx_lock = asyncio.Lock()
        self._rx_task: asyncio.Task | None = None
        self._rx_running = False
        self._rx_callback: Callable[[DMXPacket], None] | None = None

    async def is_available(self) -> bool:
        return os.path.exists(self.port) and os.access(self.port, os.R_OK | os.W_OK)

    async def open(self) -> bool:
        loop = asyncio.get_event_loop()
        try:
            self._serial = await loop.run_in_executor(None, self._open_serial)
            return self._serial is not None
        except Exception:
            return False

    def _open_serial(self) -> serial.Serial | None:
        try:
            return serial.Serial(
                self.port,
                baudrate=self._DMX_BAUD,
                bytesize=serial.EIGHTBITS,
                parity=serial.PARITY_NONE,
                stopbits=serial.STOPBITS_TWO,
                timeout=0,          # Non-blocking reads
                write_timeout=1.0,
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
        channels = list(universe.channels[:512])
        async with self._tx_lock:
            loop = asyncio.get_event_loop()
            try:
                await loop.run_in_executor(None, self._send_frame, channels)
                return True
            except Exception:
                return False

    def _send_frame(self, channels: list[int]) -> None:
        """Send one DMX frame synchronously (runs in thread executor)."""
        ser = self._serial
        if not ser:
            return
        # Break: PySerial.send_break() uses TIOCSBRK/TIOCCBRK internally
        # BUG-FIX: was tty.tcsendbreak() which doesn't exist in Python's tty
        ser.send_break(duration=self._BREAK_SECS)
        # Mark After Break — line is already high; just wait the interval
        time.sleep(self._MAB_SECS)
        # Start code (0x00) + up to 512 slot bytes
        data = bytes([0x00] + channels)
        ser.write(data)
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
            # BUG-FIX: capture reference locally so the lambda doesn't close
            # over self._serial (which may become None on close())
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

                while len(buf) >= 2:
                    if buf[0] == 0x00:
                        # Best-effort framing: consume up to 513 bytes
                        expected = min(513, len(buf))
                        packet_data = bytes(buf[:expected])
                        buf = buf[expected:]

                        packet = DMXPacket(
                            timestamp=datetime.now(timezone.utc),
                            start_code=packet_data[0],
                            slots=list(packet_data[1:]),
                            timing=DMXPacketTiming(
                                break_us=self._BREAK_SECS * 1e6,
                                mab_us=self._MAB_SECS * 1e6,
                                slot_count=len(packet_data) - 1,
                            ),
                        )
                        if self._rx_callback:
                            try:
                                self._rx_callback(packet)
                            except Exception:
                                pass
                    else:
                        # Discard framing garbage
                        buf.pop(0)

            except Exception:
                await asyncio.sleep(0.001)

    async def send_rdm_discovery(self) -> list[str]:
        # RDM requires break + MAB + RDM packet framing (E1.20).
        # Full implementation is planned; stub returns empty discovery.
        return []

    async def send_rdm_get(self, uid: str, pid: int, sub_device: int = 0) -> bytes | None:
        return None

    async def send_rdm_set(self, uid: str, pid: int, data: bytes, sub_device: int = 0) -> bool:
        return False
