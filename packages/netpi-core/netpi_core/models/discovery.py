from datetime import datetime
from pydantic import BaseModel, Field

class Neighbor(BaseModel):
    local_interface: str
    protocol: str
    device_id: str | None = None
    port_id: str | None = None
    platform: str | None = None
    ip_address: str | None = None
    vlan_id: int | None = None
    capabilities: list[str] = Field(default_factory=list)
    ttl: int | None = None
    last_seen: datetime

class TopologyNode(BaseModel):
    id: str; label: str; type: str
    ip: str | None = None; mac: str | None = None; vendor: str | None = None

class TopologyEdge(BaseModel):
    source: str; target: str
    local_port: str | None = None
    remote_port: str | None = None
    protocol: str | None = None
