"""OCA/AES70 discovery and control foundation."""
import asyncio
import time
from datetime import datetime, timezone

from netpi_core.models.oca import (
    OCADevice,
    OCAKnownClass,
    OCAManualDeviceRequest,
    OCAObjectDescriptor,
    OCAProbeResult,
)

from .mdns import MDNSDiscovery


KNOWN_CLASSES = [
    OCAKnownClass(
        name="OcaRoot",
        role="root",
        description="Base object from which all AES70 objects inherit.",
    ),
    OCAKnownClass(
        name="OcaDeviceManager",
        role="manager",
        description="Exposes device identity, model, serial, software, and reset controls.",
    ),
    OCAKnownClass(
        name="OcaSecurityManager",
        role="manager",
        description="Manages access, authentication, and secure-control policy.",
    ),
    OCAKnownClass(
        name="OcaFirmwareManager",
        role="manager",
        description="Coordinates device firmware package state and update operations.",
    ),
    OCAKnownClass(
        name="OcaSubscriptionManager",
        role="manager",
        description="Coordinates event subscriptions and notifications.",
    ),
    OCAKnownClass(
        name="OcaBlock",
        role="container",
        description="Contains and organizes control objects in a device object tree.",
    ),
    OCAKnownClass(
        name="OcaGain",
        role="worker",
        description="Controls gain values for audio signal paths.",
    ),
    OCAKnownClass(
        name="OcaMute",
        role="worker",
        description="Controls mute state for audio signal paths.",
    ),
    OCAKnownClass(
        name="OcaSwitch",
        role="worker",
        description="Controls binary or multi-position switch values.",
    ),
    OCAKnownClass(
        name="OcaLevelSensor",
        role="sensor",
        description="Reports measured signal level values.",
    ),
]


OBJECT_SKELETON = [
    OCAObjectDescriptor(
        ono="1",
        class_name="OcaRoot",
        role="root",
        description="Root object. Full property/method reads require OCP.1 method support.",
    ),
    OCAObjectDescriptor(
        ono="1.1",
        class_name="OcaDeviceManager",
        role="manager",
        description="Expected manager for device identity and model information.",
    ),
    OCAObjectDescriptor(
        ono="1.2",
        class_name="OcaSecurityManager",
        role="manager",
        description="Expected manager for security and access policy.",
    ),
    OCAObjectDescriptor(
        ono="1.3",
        class_name="OcaFirmwareManager",
        role="manager",
        description="Expected manager for firmware status and update operations.",
    ),
    OCAObjectDescriptor(
        ono="1.4",
        class_name="OcaSubscriptionManager",
        role="manager",
        description="Expected manager for event subscription coordination.",
    ),
]


class OCAEngine:
    """Manage OCA/AES70 devices discovered by mDNS or added manually."""

    def __init__(self, discovery: MDNSDiscovery | None = None) -> None:
        self.discovery = discovery or MDNSDiscovery()
        self._devices: dict[str, OCADevice] = {}

    def status(self) -> dict:
        return {
            "device_count": len(self._devices),
            "discovery_services": ["_oca._tcp.local."],
            "implementation": "discovery_registry_tcp_probe",
            "ocp1_method_layer": "planned",
        }

    async def discover(self, timeout_sec: float = 1.0, service_type: str = "_oca._tcp.local.") -> list[OCADevice]:
        devices = await self.discovery.discover(service_type=service_type, timeout_sec=timeout_sec)
        for device in devices:
            self.upsert_device(device)
        return devices

    def upsert_device(self, device: OCADevice) -> OCADevice:
        existing = self._devices.get(device.id)
        if existing:
            device.discovered_at = existing.discovered_at
        self._devices[device.id] = device
        return device

    def add_manual_device(self, request: OCAManualDeviceRequest) -> OCADevice:
        now = datetime.now(timezone.utc)
        device_id = f"{request.host}:{request.port}"
        device = OCADevice(
            id=device_id,
            name=request.name or device_id,
            host=request.host,
            port=request.port,
            transport=request.transport,
            source="manual",
            discovered_at=now,
            last_seen=now,
        )
        self._devices[device.id] = device
        return device

    def list_devices(self) -> list[OCADevice]:
        return sorted(self._devices.values(), key=lambda d: (d.name.lower(), d.host, d.port))

    def get_device(self, device_id: str) -> OCADevice | None:
        return self._devices.get(device_id)

    def remove_device(self, device_id: str) -> bool:
        return self._devices.pop(device_id, None) is not None

    async def probe(self, device_id: str, timeout_sec: float = 1.0) -> OCAProbeResult | None:
        device = self.get_device(device_id)
        if not device:
            return None
        result = await self.probe_address(device.host, device.port, timeout_sec=timeout_sec, device_id=device.id)
        device.reachable = result.reachable
        device.last_seen = datetime.now(timezone.utc)
        return result

    async def probe_address(
        self,
        host: str,
        port: int,
        timeout_sec: float = 1.0,
        device_id: str | None = None,
    ) -> OCAProbeResult:
        start = time.perf_counter()
        try:
            reader, writer = await asyncio.wait_for(
                asyncio.open_connection(host, port),
                timeout=timeout_sec,
            )
            writer.close()
            await writer.wait_closed()
            latency_ms = (time.perf_counter() - start) * 1000.0
            return OCAProbeResult(
                device_id=device_id or f"{host}:{port}",
                host=host,
                port=port,
                reachable=True,
                latency_ms=latency_ms,
            )
        except Exception as exc:
            return OCAProbeResult(
                device_id=device_id or f"{host}:{port}",
                host=host,
                port=port,
                reachable=False,
                error=str(exc),
            )

    def known_classes(self) -> list[OCAKnownClass]:
        return list(KNOWN_CLASSES)

    def object_skeleton(self, device_id: str) -> list[OCAObjectDescriptor] | None:
        if device_id not in self._devices:
            return None
        return list(OBJECT_SKELETON)


_engine: OCAEngine | None = None


def get_engine() -> OCAEngine:
    global _engine
    if _engine is None:
        _engine = OCAEngine()
    return _engine
