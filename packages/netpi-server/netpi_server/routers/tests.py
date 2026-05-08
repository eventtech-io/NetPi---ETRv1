"""Network test endpoints."""
from fastapi import APIRouter
from netpi_tests.ping import ping_host
from netpi_tests.traceroute import trace_host
from netpi_tests.iperf3 import iperf3_client
from netpi_tests.speedtest import run_speedtest

router = APIRouter(tags=["tests"])

@router.post("/tests/ping")
async def api_ping(host: str, count: int = 4):
    return await ping_host(host, count=count)

@router.post("/tests/traceroute")
async def api_traceroute(host: str, max_hops: int = 30):
    return await trace_host(host, max_hops=max_hops)

@router.post("/tests/iperf3")
async def api_iperf3(host: str, port: int = 5201, duration: int = 10,
                      reverse: bool = False, udp: bool = False):
    return await iperf3_client(host, port=port, duration=duration, reverse=reverse, udp=udp)

@router.post("/tests/speedtest")
async def api_speedtest():
    return await run_speedtest()
