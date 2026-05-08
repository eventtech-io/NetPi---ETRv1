"""Network discovery endpoints."""
from ipaddress import IPv4Network
from fastapi import APIRouter, HTTPException

from netpi_discovery.arp_scan import arp_scan
from netpi_discovery.ping_sweep import ping_sweep
from netpi_discovery.topology import TopologyBuilder
from netpi_db.database import get_db
from netpi_db.repositories.discovery import TopologyRepository

router = APIRouter(tags=["discovery"])


def _validate_network(network: str) -> IPv4Network:
    """Parse and validate CIDR; raise 422 on bad input."""
    try:
        return IPv4Network(network, strict=False)
    except ValueError:
        raise HTTPException(status_code=422, detail=f"Invalid network CIDR: {network!r}")


@router.post("/discovery/arp-scan")
async def discovery_arp_scan(network: str, interface: str = "eth0"):
    """Run an ARP scan on a network and persist discovered devices to topology."""
    _validate_network(network)
    devices = []
    db = get_db()
    topo_repo = TopologyRepository(db)

    async for dev in arp_scan(network, interface=interface):
        devices.append(dev.model_dump())
        # Persist as topology node
        try:
            from netpi_core.models.discovery import TopologyNode
            await topo_repo.upsert_node(
                TopologyNode(
                    id=dev.mac_address or dev.ip_address,
                    label=dev.ip_address or dev.mac_address,
                    type="host",
                    ip=dev.ip_address,
                    mac=dev.mac_address,
                    vendor=dev.vendor,
                )
            )
        except Exception:
            pass

    return {"network": network, "devices": devices}


@router.post("/discovery/ping-sweep")
async def discovery_ping_sweep(network: str):
    """Run a ping sweep on a network."""
    _validate_network(network)
    devices = []
    async for dev in ping_sweep(network):
        devices.append(dev.model_dump())
    return {"network": network, "devices": devices}


@router.get("/discovery/topology")
async def get_topology():
    """Get current network topology (persisted + in-memory)."""
    try:
        db = get_db()
        topo_repo = TopologyRepository(db)
        persisted = await topo_repo.get_topology()
        if persisted["nodes"]:
            return persisted
    except Exception:
        pass

    # Fallback to in-memory builder if DB is empty/unavailable
    builder = TopologyBuilder()
    return builder.to_dict()



