"""System and interface endpoints."""
import asyncio
import json
import os
import socket

from fastapi import APIRouter, HTTPException

from netpi_core.models.interface import Interface, InterfaceStats
from netpi_core.enums.link_state import LinkState

router = APIRouter(tags=["system"])


@router.get("/system/info")
async def system_info():
    return {
        "hostname": socket.gethostname(),
        "platform": "linux",
        "model": _get_pi_model(),
    }


@router.get("/system/interfaces", response_model=list[Interface])
async def list_interfaces():
    return await _get_interfaces()


@router.get("/system/interfaces/{iface}/stats", response_model=InterfaceStats)
async def interface_stats(iface: str):
    stats = await _get_interface_stats(iface)
    if stats is None:
        raise HTTPException(status_code=404, detail=f"Interface '{iface}' not found")
    return stats


def _get_pi_model() -> str:
    try:
        with open("/proc/device-tree/model") as f:
            return f.read().strip().replace("\x00", "")
    except Exception:
        return "Unknown"


async def _get_interfaces() -> list[Interface]:
    """Parse /sys/class/net for interface info."""
    interfaces: list[Interface] = []
    net_path = "/sys/class/net"
    if not os.path.isdir(net_path):
        return interfaces

    for name in sorted(os.listdir(net_path)):
        if name == "lo":
            continue
        path = os.path.join(net_path, name)

        def _read(filename: str, default=None):
            try:
                with open(os.path.join(path, filename)) as f:
                    return f.read().strip()
            except Exception:
                return default

        mac = _read("address")
        state = _read("operstate", "unknown")
        link_state = LinkState.UP if state == "up" else LinkState.DOWN

        mtu = int(_read("mtu", "1500"))

        speed_raw = _read("speed")
        speed = int(speed_raw) if speed_raw and speed_raw != "-1" else None
        duplex = _read("duplex")

        # IP addresses via `ip -j addr`
        ips: list[str] = []
        try:
            proc = await asyncio.create_subprocess_exec(
                "ip", "-j", "addr", "show", name,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=5.0)
            for entry in json.loads(stdout.decode()):
                for ai in entry.get("addr_info", []):
                    if ai.get("family") == "inet":
                        ips.append(f"{ai['local']}/{ai.get('prefixlen', 24)}")
        except Exception:
            pass

        # Cable-test support: check driver, not run the test
        # BUG-FIX: was using ethtool --cable-test (destructive) to check
        supports_cable_test = False
        try:
            proc = await asyncio.create_subprocess_exec(
                "ethtool", "-i", name,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=3.0)
            driver_info = stdout.decode().lower()
            # bcmgenet is the BCM54213 PHY driver on Pi 4/5
            if any(d in driver_info for d in ("bcmgenet", "tg3", "bnx2x")):
                supports_cable_test = True
        except Exception:
            pass

        interfaces.append(Interface(
            name=name,
            index=0,
            mac_address=mac,
            ip_addresses=ips,
            link_state=link_state,
            speed_mbps=speed,
            duplex=duplex,
            mtu=mtu,
            is_loopback=False,
            is_wireless=name.startswith("wl"),
            supports_cable_test=supports_cable_test,
        ))

    return interfaces


async def _get_interface_stats(iface: str) -> InterfaceStats | None:
    """Parse /proc/net/dev for interface statistics."""
    try:
        with open("/proc/net/dev") as f:
            for line in f:
                if iface + ":" in line:
                    parts = line.split()
                    if len(parts) >= 17:
                        return InterfaceStats(
                            interface=iface,
                            rx_bytes=int(parts[1]),
                            rx_packets=int(parts[2]),
                            rx_errors=int(parts[3]),
                            rx_dropped=int(parts[4]),
                            tx_bytes=int(parts[9]),
                            tx_packets=int(parts[10]),
                            tx_errors=int(parts[11]),
                            tx_dropped=int(parts[12]),
                            collisions=int(parts[14]),
                        )
    except Exception:
        pass
    return None
