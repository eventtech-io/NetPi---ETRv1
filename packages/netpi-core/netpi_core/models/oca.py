"""OCA/AES70 models."""
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, field_validator


OCATransport = Literal["tcp", "tcp_tls", "udp", "websocket", "unknown"]


class OCADevice(BaseModel):
    id: str
    name: str
    host: str
    port: int = Field(65000, ge=1, le=65535)
    transport: OCATransport = "tcp"
    service_name: str | None = None
    txt: dict[str, str] = Field(default_factory=dict)
    source: Literal["manual", "mdns"] = "manual"
    discovered_at: datetime
    last_seen: datetime
    reachable: bool | None = None


class OCADiscoveryRequest(BaseModel):
    timeout_sec: float = Field(1.0, ge=0.1, le=10.0)
    service_type: str = "_oca._tcp.local."

    @field_validator("service_type")
    @classmethod
    def _validate_service_type(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("service_type cannot be empty")
        return value if value.endswith(".") else f"{value}."


class OCAManualDeviceRequest(BaseModel):
    name: str | None = None
    host: str
    port: int = Field(65000, ge=1, le=65535)
    transport: OCATransport = "tcp"


class OCAProbeResult(BaseModel):
    device_id: str
    host: str
    port: int
    reachable: bool
    latency_ms: float | None = None
    error: str | None = None


class OCAKnownClass(BaseModel):
    name: str
    role: str
    description: str


class OCAObjectDescriptor(BaseModel):
    ono: str
    class_name: str
    role: str
    description: str
    implemented: bool = False
