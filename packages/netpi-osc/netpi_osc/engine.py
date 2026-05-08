"""Async OSC UDP engine."""
import asyncio
import logging
from datetime import datetime, timezone

from netpi_core.models.osc import OSCMessage, OSCReceivedMessage, OSCStatus, OSCTarget

from .codec import OSCDecodeError, decode_message, encode_message

logger = logging.getLogger("netpi.osc")


class _OSCProtocol(asyncio.DatagramProtocol):
    def __init__(self, engine: "OSCEngine") -> None:
        self.engine = engine

    def datagram_received(self, data: bytes, addr) -> None:
        host, port = addr[:2]
        self.engine._handle_datagram(data, host, int(port))

    def error_received(self, exc: Exception) -> None:
        logger.warning("OSC UDP error: %s", exc)


class OSCEngine:
    """Send, receive, and retain recent OSC messages."""

    def __init__(self, history_limit: int = 200) -> None:
        self.history_limit = history_limit
        self._transport: asyncio.DatagramTransport | None = None
        self._host: str | None = None
        self._port: int | None = None
        self._messages: list[OSCReceivedMessage] = []

    async def send(self, target: OSCTarget, message: OSCMessage) -> dict:
        """Send one OSC message to a UDP target."""
        loop = asyncio.get_running_loop()
        transport, _ = await loop.create_datagram_endpoint(
            asyncio.DatagramProtocol,
            remote_addr=(target.host, target.port),
        )
        try:
            transport.sendto(encode_message(message))
        finally:
            transport.close()
        return {
            "sent": True,
            "host": target.host,
            "port": target.port,
            "address": message.address,
            "argument_count": len(message.arguments),
        }

    async def start_listener(self, host: str = "0.0.0.0", port: int = 9001) -> OSCStatus:
        """Start receiving OSC UDP messages."""
        await self.stop_listener()
        loop = asyncio.get_running_loop()
        transport, _ = await loop.create_datagram_endpoint(
            lambda: _OSCProtocol(self),
            local_addr=(host, port),
        )
        self._transport = transport
        socket = transport.get_extra_info("socket")
        actual_host, actual_port = socket.getsockname()[:2]
        self._host = str(actual_host)
        self._port = int(actual_port)
        return self.status()

    async def stop_listener(self) -> OSCStatus:
        """Stop receiving OSC UDP messages."""
        if self._transport:
            self._transport.close()
            await asyncio.sleep(0)
        self._transport = None
        self._host = None
        self._port = None
        return self.status()

    def status(self) -> OSCStatus:
        return OSCStatus(
            listening=self._transport is not None,
            host=self._host,
            port=self._port,
            message_count=len(self._messages),
        )

    def list_messages(self, limit: int = 50) -> list[OSCReceivedMessage]:
        if limit <= 0:
            return []
        return self._messages[-limit:]

    def clear_messages(self) -> int:
        count = len(self._messages)
        self._messages.clear()
        return count

    def _handle_datagram(self, data: bytes, host: str, port: int) -> None:
        try:
            message = decode_message(data)
        except OSCDecodeError:
            logger.warning("Invalid OSC datagram from %s:%s", host, port, exc_info=True)
            return

        received = OSCReceivedMessage(
            address=message.address,
            arguments=message.arguments,
            remote_host=host,
            remote_port=port,
            received_at=datetime.now(timezone.utc),
        )
        self._messages.append(received)
        if len(self._messages) > self.history_limit:
            del self._messages[: len(self._messages) - self.history_limit]


_engine: OSCEngine | None = None


def get_engine() -> OSCEngine:
    global _engine
    if _engine is None:
        _engine = OSCEngine()
    return _engine
