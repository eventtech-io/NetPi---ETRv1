"""OCA/AES70 endpoints."""
from fastapi import APIRouter, HTTPException

from netpi_core.models.oca import OCADiscoveryRequest, OCAManualDeviceRequest
from netpi_oca.engine import get_engine

router = APIRouter(tags=["oca"])


@router.get("/oca/status")
async def oca_status():
    """Return OCA/AES70 subsystem status."""
    return get_engine().status()


@router.post("/oca/discover")
async def oca_discover(request: OCADiscoveryRequest = OCADiscoveryRequest()):
    """Discover OCA/AES70 devices advertised with DNS-SD/mDNS."""
    devices = await get_engine().discover(
        timeout_sec=request.timeout_sec,
        service_type=request.service_type,
    )
    return {"devices": devices, "count": len(devices)}


@router.get("/oca/devices")
async def oca_list_devices():
    """List discovered and manually added OCA/AES70 devices."""
    return get_engine().list_devices()


@router.post("/oca/devices")
async def oca_add_device(request: OCAManualDeviceRequest):
    """Add an OCA/AES70 device manually by host/port."""
    return get_engine().add_manual_device(request)


@router.get("/oca/devices/{device_id}")
async def oca_get_device(device_id: str):
    """Get one OCA/AES70 device from the local registry."""
    device = get_engine().get_device(device_id)
    if not device:
        raise HTTPException(status_code=404, detail="OCA device not found")
    return device


@router.delete("/oca/devices/{device_id}")
async def oca_remove_device(device_id: str):
    """Remove one OCA/AES70 device from the local registry."""
    if not get_engine().remove_device(device_id):
        raise HTTPException(status_code=404, detail="OCA device not found")
    return {"deleted": True, "device_id": device_id}


@router.post("/oca/devices/{device_id}/probe")
async def oca_probe_device(device_id: str, timeout_sec: float = 1.0):
    """Probe TCP reachability for a registered OCA/AES70 device."""
    result = await get_engine().probe(device_id, timeout_sec=timeout_sec)
    if not result:
        raise HTTPException(status_code=404, detail="OCA device not found")
    return result


@router.get("/oca/devices/{device_id}/objects")
async def oca_device_objects(device_id: str):
    """Return the expected AES70 object skeleton for a device."""
    objects = get_engine().object_skeleton(device_id)
    if objects is None:
        raise HTTPException(status_code=404, detail="OCA device not found")
    return {"device_id": device_id, "objects": objects}


@router.get("/oca/classes")
async def oca_known_classes():
    """List OCA/AES70 classes currently recognized by NetPi."""
    return get_engine().known_classes()
