"""ARP scan for local subnet discovery."""
import asyncio
import logging
from datetime import datetime, timezone
from ipaddress import IPv4Network
from typing import AsyncGenerator

from scapy.layers.l2 import ARP, Ether
from scapy.sendrecv import srp

from netpi_core.models.device import Device

logger = logging.getLogger("netpi.discovery.arp")


async def arp_scan(
    network: str,
    interface: str = "eth0",
    timeout: float = 2.0,
) -> AsyncGenerator[Device, None]:
    """Async ARP scan of a CIDR network."""
    net = IPv4Network(network, strict=False)
    loop = asyncio.get_event_loop()

    def _scan():
        ans, _ = srp(
            Ether(dst="ff:ff:ff:ff:ff:ff") / ARP(pdst=str(net)),
            iface=interface,
            timeout=timeout,
            verbose=0,
        )
        return ans

    try:
        ans = await loop.run_in_executor(None, _scan)
    except Exception:
        logger.exception("ARP scan failed on %s", interface)
        return

    now = datetime.now(timezone.utc)

    for _sent, received in ans:
        ip = received.psrc
        mac = received.hwsrc
        yield Device(
            id=mac,
            ip_address=ip,
            mac_address=mac,
            first_seen=now,
            last_seen=now,
            is_online=True,
        )



