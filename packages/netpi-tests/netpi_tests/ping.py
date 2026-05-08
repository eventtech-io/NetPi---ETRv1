from icmplib import async_ping
async def ping_host(host: str, count: int = 4, interval: float = 0.5,
                    timeout: float = 2.0, payload_size: int = 56):
    result = await async_ping(host, count=count, interval=interval,
                               timeout=timeout, payload_size=payload_size)
    return {"host": host, "is_alive": result.is_alive,
            "min_rtt_ms": result.min_rtt, "avg_rtt_ms": result.avg_rtt,
            "max_rtt_ms": result.max_rtt, "packets_sent": result.packets_sent,
            "packets_received": result.packets_received,
            "packet_loss_pct": result.packet_loss, "jitter_ms": result.jitter}
