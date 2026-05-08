"""Fast async ping sweep using icmplib."""
import asyncio
import logging
from datetime import datetime, timezone
from ipaddress import IPv4Network
from typing import AsyncGenerator

from icmplib import async_ping

from netpi_core.models.device import Device

logger = logging.getLogger("netpi.discovery.ping")


async def ping_sweep(
    network: str,
    count: int = 1,
    interval: float = 0.0,
    timeout: float = 1.0,
    concurrent: int = 50,
) -> AsyncGenerator[Device, None]:
    """Ping sweep a CIDR network with controlled concurrency."""
    net = IPv4Network(network, strict=False)
    hosts = [str(h) for h in net.hosts()]
    semaphore = asyncio.Semaphore(concurrent)

    async def _ping_host(host: str) -> Device | None:
        async with semaphore:
            try:
                result = await async_ping(
                    host, count=count, interval=interval, timeout=timeout
                )
                if result.is_alive:
                    now = datetime.now(timezone.utc)
                    return Device(
                        id=host,
                        ip_address=host,
                        first_seen=now,
                        last_seen=now,
                        is_online=True,
                    )
            except Exception:
                logger.debug("Ping failed for %s", host, exc_info=True)
            return None

    tasks = [asyncio.create_task(_ping_host(h)) for h in hosts]

    for coro in asyncio.as_completed(tasks):
        dev = await coro
        if dev:
            yield dev



