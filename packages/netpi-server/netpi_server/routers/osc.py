"""Open Sound Control endpoints."""
from fastapi import APIRouter

from netpi_core.models.osc import OSCListenRequest, OSCMessage, OSCSendRequest, OSCTarget
from netpi_osc.engine import get_engine

router = APIRouter(tags=["osc"])


@router.get("/osc/status")
async def osc_status():
    """Return OSC listener status."""
    return get_engine().status()


@router.post("/osc/send")
async def osc_send(request: OSCSendRequest):
    """Send one OSC message to a UDP target."""
    return await get_engine().send(request.target, request.message)


@router.post("/osc/send/{host}/{port}")
async def osc_send_to(host: str, port: int, message: OSCMessage):
    """Send one OSC message to a target encoded in the URL."""
    return await get_engine().send(OSCTarget(host=host, port=port), message)


@router.post("/osc/listen/start")
async def osc_start_listener(request: OSCListenRequest = OSCListenRequest()):
    """Start the OSC UDP listener."""
    return await get_engine().start_listener(request.host, request.port)


@router.post("/osc/listen/stop")
async def osc_stop_listener():
    """Stop the OSC UDP listener."""
    return await get_engine().stop_listener()


@router.get("/osc/messages")
async def osc_messages(limit: int = 50):
    """Return recently received OSC messages."""
    return {"messages": get_engine().list_messages(limit=limit)}


@router.delete("/osc/messages")
async def osc_clear_messages():
    """Clear received OSC message history."""
    return {"cleared": get_engine().clear_messages()}
