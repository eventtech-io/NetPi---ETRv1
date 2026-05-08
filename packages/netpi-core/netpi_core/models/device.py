from datetime import datetime
from pydantic import BaseModel, Field

class Device(BaseModel):
    id: str = Field(..., description="Unique device identifier")
    hostname: str | None = None
    ip_address: str | None = None
    mac_address: str | None = None
    vendor: str | None = None
    model: str | None = None
    os_name: str | None = None
    os_version: str | None = None
    first_seen: datetime
    last_seen: datetime
    is_online: bool = True
    tags: list[str] = Field(default_factory=list)

class DeviceSummary(BaseModel):
    total: int
    online: int
    offline: int
    by_vendor: dict[str, int] = Field(default_factory=dict)
