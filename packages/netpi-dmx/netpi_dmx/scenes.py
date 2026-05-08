"""DMX scene (snapshot) engine with async fade transitions."""
import asyncio
import json
import logging
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Callable

from netpi_core.models.dmx import DMXUniverse

logger = logging.getLogger("netpi.dmx.scenes")


@dataclass
class Scene:
    id: str
    name: str
    universe_id: str
    channels: list[int]
    created_at: datetime


@dataclass
class FadeTask:
    task: asyncio.Task
    target_channels: list[int]
    duration_ms: int


class SceneEngine:
    """Manage DMX scenes and execute smooth fade transitions."""

    def __init__(self) -> None:
        self._scenes: dict[str, Scene] = {}
        self._active_fades: dict[str, FadeTask] = {}
        self._fade_callbacks: list[Callable[[str, int, int, int], None]] = []
        # signature: (universe_id, channel, old_value, new_value)

    def create_scene(self, universe: DMXUniverse, name: str) -> Scene:
        scene = Scene(
            id=str(uuid.uuid4()),
            name=name,
            universe_id=universe.id,
            channels=list(universe.channels),
            created_at=datetime.now(timezone.utc),
        )
        self._scenes[scene.id] = scene
        logger.info("Scene %s created for universe %s", scene.id, universe.id)
        return scene

    def get_scene(self, scene_id: str) -> Scene | None:
        return self._scenes.get(scene_id)

    def list_scenes(self, universe_id: str | None = None) -> list[Scene]:
        scenes = list(self._scenes.values())
        if universe_id:
            scenes = [s for s in scenes if s.universe_id == universe_id]
        return scenes

    def delete_scene(self, scene_id: str) -> bool:
        if scene_id in self._scenes:
            del self._scenes[scene_id]
            return True
        return False

    async def recall_scene(
        self,
        universe: DMXUniverse,
        scene_id: str,
        fade_ms: int = 0,
        rate_hz: float = 44.0,
    ) -> bool:
        """Recall a scene, optionally with a smooth fade."""
        scene = self._scenes.get(scene_id)
        if not scene:
            logger.warning("Scene %s not found", scene_id)
            return False

        if scene.universe_id != universe.id:
            logger.warning("Scene %s belongs to universe %s, not %s",
                           scene_id, scene.universe_id, universe.id)
            return False

        # Cancel any active fade for this universe
        await self._cancel_fade(universe.id)

        if fade_ms <= 0:
            universe.channels[:] = list(scene.channels)
            universe.last_updated = datetime.now(timezone.utc)
            logger.info("Scene %s recalled instantly on %s", scene_id, universe.id)
            return True

        # Async interpolation fade
        self._active_fades[universe.id] = FadeTask(
            task=asyncio.create_task(
                self._fade_universe(universe, scene.channels, fade_ms, rate_hz)
            ),
            target_channels=list(scene.channels),
            duration_ms=fade_ms,
        )
        return True

    async def _fade_universe(
        self,
        universe: DMXUniverse,
        target: list[int],
        fade_ms: int,
        rate_hz: float,
    ) -> None:
        start = list(universe.channels)
        steps = max(1, int((fade_ms / 1000.0) * rate_hz))
        interval = 1.0 / rate_hz

        for step in range(1, steps + 1):
            if universe.id not in self._active_fades:
                logger.debug("Fade on %s cancelled at step %d", universe.id, step)
                return

            t = step / steps
            for i in range(512):
                old_val = start[i]
                new_val = int(old_val + (target[i] - old_val) * t)
                if new_val != universe.channels[i]:
                    universe.channels[i] = new_val
                    for cb in self._fade_callbacks:
                        try:
                            cb(universe.id, i + 1, old_val, new_val)
                        except Exception:
                            pass

            universe.last_updated = datetime.now(timezone.utc)
            await asyncio.sleep(interval)

        # Ensure exact landing
        universe.channels[:] = list(target)
        universe.last_updated = datetime.now(timezone.utc)
        self._active_fades.pop(universe.id, None)
        logger.info("Fade complete on %s", universe.id)

    async def _cancel_fade(self, universe_id: str) -> None:
        fade = self._active_fades.pop(universe_id, None)
        if fade:
            fade.task.cancel()
            try:
                await fade.task
            except asyncio.CancelledError:
                pass

    def on_fade_step(self, callback: Callable[[str, int, int, int], None]) -> None:
        self._fade_callbacks.append(callback)

    def to_dict(self, scene: Scene) -> dict:
        return {
            "id": scene.id,
            "name": scene.name,
            "universe_id": scene.universe_id,
            "channels": scene.channels,
            "created_at": scene.created_at.isoformat(),
        }


_scene_engine: SceneEngine | None = None


def get_scene_engine() -> SceneEngine:
    global _scene_engine
    if _scene_engine is None:
        _scene_engine = SceneEngine()
    return _scene_engine


