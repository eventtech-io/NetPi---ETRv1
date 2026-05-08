"""Tests for OCA/AES70 engine."""
import pytest

from netpi_core.models.oca import OCAManualDeviceRequest
from netpi_oca.engine import OCAEngine


class TestOCAEngine:
    def test_manual_device_registry(self):
        engine = OCAEngine()
        device = engine.add_manual_device(
            OCAManualDeviceRequest(name="Console", host="127.0.0.1", port=65000)
        )

        assert device.id == "127.0.0.1:65000"
        assert engine.get_device(device.id) == device
        assert engine.list_devices()[0].name == "Console"
        assert engine.remove_device(device.id) is True
        assert engine.get_device(device.id) is None

    def test_known_classes_and_object_skeleton(self):
        engine = OCAEngine()
        device = engine.add_manual_device(
            OCAManualDeviceRequest(name="DSP", host="192.0.2.20", port=65000)
        )

        classes = engine.known_classes()
        assert any(cls.name == "OcaRoot" for cls in classes)

        objects = engine.object_skeleton(device.id)
        assert objects is not None
        assert objects[0].class_name == "OcaRoot"

    @pytest.mark.asyncio
    async def test_unreachable_probe_returns_structured_result(self):
        engine = OCAEngine()
        device = engine.add_manual_device(
            OCAManualDeviceRequest(name="Missing", host="127.0.0.1", port=1)
        )

        result = await engine.probe(device.id, timeout_sec=0.2)

        assert result is not None
        assert result.device_id == device.id
        assert result.reachable is False
        assert engine.get_device(device.id).reachable is False
