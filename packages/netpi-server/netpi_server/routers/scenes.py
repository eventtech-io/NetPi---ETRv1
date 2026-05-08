"""DMX scene (preset) endpoints."""
import logging

from fastapi import APIRouter, HTTPException

from netpi_core.models.dmx import DMXUniverse
from netpi_dmx.engine import get_engine as get_dmx_engine
from netpi_dmx.scenes import get_scene_engine

router = APIRouter(tags=["dmx-scenes"])
logger = logging.getLogger("netpi.scenes")


@router.post("/dmx/universes/{uni_id}/scenes")
async def create_scene(uni_id: str, name: str):
    """Save the current universe state as a named scene."""
    engine = get_dmx_engine()
    uni = engine.get_universe(uni_id)
    if not uni:
        raise HTTPException(status_code=404, detail="Universe not found")
    scene = get_scene_engine().create_scene(uni, name)
    return get_scene_engine().to_dict(scene)


@router.get("/dmx/universes/{uni_id}/scenes")
async def list_scenes(uni_id: str):
    """List all scenes for a universe."""
    scenes = get_scene_engine().list_scenes(universe_id=uni_id)
    return [get_scene_engine().to_dict(s) for s in scenes]


@router.get("/dmx/scenes/{scene_id}")
async def get_scene(scene_id: str):
    """Get a scene by ID."""
    scene = get_scene_engine().get_scene(scene_id)
    if not scene:
        raise HTTPException(status_code=404, detail="Scene not found")
    return get_scene_engine().to_dict(scene)


@router.delete("/dmx/scenes/{scene_id}")
async def delete_scene(scene_id: str):
    """Delete a scene."""
    if not get_scene_engine().delete_scene(scene_id):
        raise HTTPException(status_code=404, detail="Scene not found")
    return {"deleted": True}


@router.post("/dmx/universes/{uni_id}/scenes/{scene_id}/recall")
async def recall_scene(uni_id: str, scene_id: str, fade_ms: int = 0, rate_hz: float = 44.0):
    """Recall a scene, optionally with a fade transition."""
    engine = get_dmx_engine()
    uni = engine.get_universe(uni_id)
    if not uni:
        raise HTTPException(status_code=404, detail="Universe not found")

    success = await get_scene_engine().recall_scene(uni, scene_id, fade_ms=fade_ms, rate_hz=rate_hz)
    if not success:
        raise HTTPException(status_code=400, detail="Scene recall failed (wrong universe or scene missing)")

    return {"status": "recalled", "fade_ms": fade_ms, "scene_id": scene_id}



