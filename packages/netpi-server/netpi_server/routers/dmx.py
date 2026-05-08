"""DMX512/RDM endpoints."""
import asyncio
import logging
import uuid

from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect

from netpi_core.models.dmx import DMXChannel, DMXFixture
from netpi_dmx.engine import get_engine
from netpi_dmx.fixtures import list_profiles, get_profile, get_profile_modes
from netpi_db.database import get_db
from netpi_db.repositories.dmx import DMXUniverseRepository, DMXFixtureRepository

router = APIRouter(tags=["dmx"])
logger = logging.getLogger("netpi.dmx")


# ------------------------------------------------------------------
# Backend
# ------------------------------------------------------------------

@router.post("/dmx/backend/detect")
async def dmx_detect_backend():
    engine = get_engine()
    backend = await engine.auto_detect_backend()
    return {"backend": backend.name if backend else None, "available": backend is not None}


@router.get("/dmx/backend")
async def dmx_get_backend():
    engine = get_engine()
    backend = engine.get_backend()
    return {"backend": backend.name if backend else None}


# ------------------------------------------------------------------
# Universe
# ------------------------------------------------------------------

@router.post("/dmx/universes")
async def dmx_create_universe(name: str = "Universe 1"):
    universe = get_engine().create_universe(name)
    try:
        db = get_db()
        await DMXUniverseRepository(db).save(universe)
    except Exception:
        logger.exception("Failed to persist universe creation")
    return universe


@router.get("/dmx/universes")
async def dmx_list_universes():
    # Merge in-memory + persisted
    engine = get_engine()
    memory = {u.id: u for u in engine.list_universes()}
    try:
        db = get_db()
        persisted = await DMXUniverseRepository(db).list_all()
        for u in persisted:
            if u.id not in memory:
                memory[u.id] = u
                engine._universes[u.id] = u
    except Exception:
        logger.exception("Failed to load persisted universes")
    return list(memory.values())


@router.get("/dmx/universes/{uni_id}")
async def dmx_get_universe(uni_id: str):
    uni = get_engine().get_universe(uni_id)
    if not uni:
        raise HTTPException(status_code=404, detail="Universe not found")
    return uni


@router.post("/dmx/universes/{uni_id}/channels/{channel}")
async def dmx_set_channel(uni_id: str, channel: int, value: int):
    if not get_engine().set_channel(uni_id, channel, value):
        raise HTTPException(status_code=404, detail="Invalid universe or channel number")
    # Persist updated state
    try:
        db = get_db()
        uni = get_engine().get_universe(uni_id)
        if uni:
            await DMXUniverseRepository(db).save(uni)
    except Exception:
        logger.exception("Failed to persist channel update")
    return {"channel": channel, "value": value}


@router.post("/dmx/universes/{uni_id}/channels")
async def dmx_set_channels(uni_id: str, channels: list[DMXChannel]):
    if not get_engine().set_channels(uni_id, channels):
        raise HTTPException(status_code=404, detail="Universe not found")
    try:
        db = get_db()
        uni = get_engine().get_universe(uni_id)
        if uni:
            await DMXUniverseRepository(db).save(uni)
    except Exception:
        logger.exception("Failed to persist channels update")
    return {"channels_set": len(channels)}


@router.get("/dmx/universes/{uni_id}/channels/{channel}")
async def dmx_get_channel(uni_id: str, channel: int):
    value = get_engine().get_channel(uni_id, channel)
    if value is None:
        raise HTTPException(status_code=404, detail="Invalid universe or channel number")
    return {"channel": channel, "value": value}


@router.get("/dmx/universes/{uni_id}/channels")
async def dmx_get_all_channels(uni_id: str):
    uni = get_engine().get_universe(uni_id)
    if not uni:
        raise HTTPException(status_code=404, detail="Universe not found")
    return {"channels": uni.channels}


# ------------------------------------------------------------------
# Transmission
# ------------------------------------------------------------------

@router.post("/dmx/universes/{uni_id}/transmit/start")
async def dmx_start_transmit(uni_id: str, rate_hz: float = 44.0):
    if not await get_engine().start_transmit(uni_id, rate_hz):
        raise HTTPException(status_code=404, detail="Universe not found or no backend available")
    try:
        db = get_db()
        uni = get_engine().get_universe(uni_id)
        if uni:
            await DMXUniverseRepository(db).save(uni)
    except Exception:
        logger.exception("Failed to persist transmit state")
    return {"status": "transmitting", "rate_hz": rate_hz}


@router.post("/dmx/universes/{uni_id}/transmit/stop")
async def dmx_stop_transmit(uni_id: str):
    await get_engine().stop_transmit(uni_id)
    try:
        db = get_db()
        uni = get_engine().get_universe(uni_id)
        if uni:
            await DMXUniverseRepository(db).save(uni)
    except Exception:
        logger.exception("Failed to persist transmit stop")
    return {"status": "stopped"}


@router.post("/dmx/universes/{uni_id}/transmit/once")
async def dmx_send_once(uni_id: str):
    sent = await get_engine().send_once(uni_id)
    return {"sent": sent}


# ------------------------------------------------------------------
# Reception
# ------------------------------------------------------------------

@router.post("/dmx/receive/start")
async def dmx_start_receive():
    return {"receiving": await get_engine().start_receive()}


@router.post("/dmx/receive/stop")
async def dmx_stop_receive():
    success = await get_engine().stop_receive()
    return {"receiving": not success}


@router.get("/dmx/receive/latest")
async def dmx_get_latest_packet():
    packet = get_engine().get_latest_packet()
    if not packet:
        raise HTTPException(status_code=404, detail="No packets received yet")
    return packet


@router.get("/dmx/receive/history")
async def dmx_get_packet_history(limit: int = 10):
    packets = get_engine().get_received_packets()[-limit:]
    return {"packets": packets}


# ------------------------------------------------------------------
# DMX Tester / Analyzer
# ------------------------------------------------------------------

@router.get("/dmx/tester/levels")
async def dmx_view_levels():
    packet = get_engine().get_latest_packet()
    if not packet:
        raise HTTPException(status_code=404, detail="No DMX data received")
    active = {i + 1: v for i, v in enumerate(packet.slots) if v > 0}
    return {
        "timestamp": packet.timestamp,
        "start_code": packet.start_code,
        "active_channels": active,
        "slot_count": len(packet.slots),
    }


@router.get("/dmx/tester/timing")
async def dmx_analyze_timing():
    packet = get_engine().get_latest_packet()
    if not packet or not packet.timing:
        raise HTTPException(status_code=404, detail="No timing data available")
    return packet.timing


@router.get("/dmx/tester/flicker")
async def dmx_flicker_finder():
    return {"note": "Subscribe to /api/v1/ws/dmx/flicker for real-time flicker detection"}


# ------------------------------------------------------------------
# DMX Cable Test
# ------------------------------------------------------------------

@router.post("/dmx/cabletest/{port_id}")
async def dmx_cable_test(port_id: str):
    return await get_engine().test_dmx_cable(port_id)


# ------------------------------------------------------------------
# RDM
# ------------------------------------------------------------------

@router.post("/dmx/rdm/discover")
async def dmx_rdm_discover():
    devices = await get_engine().rdm_discover()
    return {"devices": devices, "note": "Full RDM (E1.20) implementation is planned"}


# ------------------------------------------------------------------
# DIP Switch Calculator
# ------------------------------------------------------------------

@router.get("/dmx/dip-switch/{address}")
async def dmx_dip_switch(address: int, step_size: int = 1):
    if address < 1 or address > 512:
        raise HTTPException(status_code=422, detail="Address must be between 1 and 512")
    return get_engine().calculate_dip_switches(address, step_size)


# ------------------------------------------------------------------
# Fixture Library
# ------------------------------------------------------------------

@router.get("/dmx/fixtures/profiles")
async def dmx_list_fixture_profiles():
    return list_profiles()


@router.get("/dmx/fixtures/profiles/{profile_id}")
async def dmx_get_fixture_profile(profile_id: str):
    profile = get_profile(profile_id)
    if not profile:
        raise HTTPException(status_code=404, detail="Fixture profile not found")
    return profile


@router.get("/dmx/fixtures/profiles/{profile_id}/modes")
async def dmx_get_fixture_modes(profile_id: str):
    modes = get_profile_modes(profile_id)
    if not modes:
        raise HTTPException(status_code=404, detail="Fixture profile not found")
    return modes


# ------------------------------------------------------------------
# Fixture Control
# ------------------------------------------------------------------

@router.post("/dmx/universes/{uni_id}/fixtures")
async def dmx_add_fixture(
    uni_id: str,
    profile_id: str,
    start_address: int,
    name: str | None = None,
    mode: str = "1ch",
):
    profile = get_profile(profile_id)
    if not profile:
        raise HTTPException(status_code=404, detail="Fixture profile not found")
    mode_data = profile.get("modes", {}).get(mode)
    if not mode_data:
        raise HTTPException(status_code=404, detail=f"Mode '{mode}' not found in profile")

    fixture = DMXFixture(
        id=str(uuid.uuid4()),
        name=name or f"{profile['name']} @ {start_address}",
        manufacturer=profile.get("manufacturer"),
        model=profile.get("model"),
        mode=mode,
        start_address=start_address,
        channel_count=mode_data["channel_count"],
        channels=[
            {"name": ch["name"], "offset": ch["offset"], "default_value": 0, "current_value": 0}
            for ch in mode_data["channels"]
        ],
    )

    try:
        db = get_db()
        await DMXFixtureRepository(db).save(fixture, universe_id=uni_id)
    except Exception:
        logger.exception("Failed to persist fixture")

    return fixture


@router.get("/dmx/universes/{uni_id}/fixtures")
async def dmx_list_fixtures(uni_id: str):
    try:
        db = get_db()
        fixtures = await DMXFixtureRepository(db).list_by_universe(uni_id)
        return fixtures
    except Exception:
        logger.exception("Failed to load fixtures")
        raise HTTPException(status_code=500, detail="Failed to load fixtures")


# ------------------------------------------------------------------
# WebSocket endpoints
# ------------------------------------------------------------------

@router.websocket("/ws/dmx/universe/{uni_id}")
async def dmx_universe_websocket(websocket: WebSocket, uni_id: str):
    """Stream DMX universe channel values in real-time (~20 Hz)."""
    await websocket.accept()
    engine = get_engine()
    try:
        while True:
            uni = engine.get_universe(uni_id)
            if uni:
                await websocket.send_json({
                    "channels": uni.channels,
                    "is_transmitting": uni.is_transmitting,
                    "tx_rate_hz": uni.tx_rate_hz,
                })
            await asyncio.sleep(0.05)
    except WebSocketDisconnect:
        pass


@router.websocket("/ws/dmx/receive")
async def dmx_receive_websocket(websocket: WebSocket):
    """Stream received DMX packets in real-time."""
    await websocket.accept()
    engine = get_engine()
    last_count = 0
    try:
        while True:
            packets = engine.get_received_packets()
            for pkt in packets[last_count:]:
                await websocket.send_json(pkt.model_dump())
            last_count = len(packets)
            await asyncio.sleep(0.01)
    except WebSocketDisconnect:
        pass


@router.websocket("/ws/dmx/flicker")
async def dmx_flicker_websocket(websocket: WebSocket):
    """Stream DMX flicker events in real-time."""
    await websocket.accept()
    engine = get_engine()
    queue: list = []

    engine.on_flicker(lambda event: queue.append(event))
    try:
        while True:
            while queue:
                await websocket.send_json(queue.pop(0).model_dump())
            await asyncio.sleep(0.01)
    except WebSocketDisconnect:
        pass



