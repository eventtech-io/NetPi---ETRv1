import asyncio

from icmplib import traceroute


async def trace_host(host: str, count: int = 2, interval: float = 0.05,
                     timeout: float = 2.0, max_hops: int = 30):
    result = await asyncio.to_thread(
        traceroute,
        host,
        count=count,
        interval=interval,
        timeout=timeout,
        max_hops=max_hops,
    )
    hops = [{"hop": h.distance, "ip": h.address, "host": getattr(h, "hostname", None),
             "avg_rtt_ms": h.avg_rtt, "min_rtt_ms": h.min_rtt,
             "max_rtt_ms": h.max_rtt, "packets_sent": h.packets_sent,
             "packet_loss_pct": h.packet_loss} for h in result]
    return {"destination": host, "hops": hops}
