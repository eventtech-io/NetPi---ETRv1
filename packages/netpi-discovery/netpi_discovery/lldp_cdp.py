"""Listen for LLDP and CDP frames on interfaces."""
import asyncio, socket, struct
from datetime import datetime, timezone
from typing import Callable
from netpi_core.models.discovery import Neighbor
from netpi_analyzer.protocols.cdp import parse_cdp
from netpi_analyzer.protocols.lldp import parse_lldp

class DiscoveryListener:
    def __init__(self, interface: str = "eth0") -> None:
        self.interface = interface
        self._running = False
        self._callbacks: list[Callable[[Neighbor], None]] = []
        self._task: asyncio.Task | None = None

    def on_neighbor(self, callback: Callable[[Neighbor], None]) -> None:
        self._callbacks.append(callback)

    async def start(self) -> None:
        self._running = True
        self._task = asyncio.create_task(self._listen())

    async def stop(self) -> None:
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass

    async def _listen(self) -> None:
        try:
            sock = socket.socket(socket.AF_PACKET, socket.SOCK_RAW, socket.htons(0x0003))
            sock.bind((self.interface, 0))
            sock.setblocking(False)
        except PermissionError:
            return
        loop = asyncio.get_event_loop()
        while self._running:
            try:
                raw = await loop.sock_recv(sock, 2048)
                neighbor = self._parse_frame(raw)
                if neighbor:
                    for cb in self._callbacks:
                        try:
                            cb(neighbor)
                        except Exception:
                            pass
            except asyncio.CancelledError:
                break
            except Exception:
                await asyncio.sleep(0.01)
        sock.close()

    def _parse_frame(self, raw: bytes) -> Neighbor | None:
        if len(raw) < 14:
            return None
        ethertype = struct.unpack(">H", raw[12:14])[0]
        if ethertype == 0x88CC:
            lldp = parse_lldp(raw)
            if lldp:
                return Neighbor(
                    local_interface=self.interface, protocol="LLDP",
                    device_id=lldp.chassis_id, port_id=lldp.port_id,
                    platform=lldp.system_description,
                    ip_address=lldp.management_addresses[0] if lldp.management_addresses else None,
                    vlan_id=lldp.vlan_id, capabilities=lldp.capabilities,
                    ttl=lldp.ttl, last_seen=datetime.now(timezone.utc),
                )
        elif ethertype == 0x2000:
            cdp = parse_cdp(raw)
            if cdp:
                return Neighbor(
                    local_interface=self.interface, protocol="CDP",
                    device_id=cdp.device_id, port_id=cdp.port_id,
                    platform=cdp.platform,
                    ip_address=cdp.addresses[0] if cdp.addresses else None,
                    vlan_id=cdp.native_vlan, capabilities=cdp.capabilities,
                    ttl=None, last_seen=datetime.now(timezone.utc),
                )
        return None
