"""Open Sound Control models."""
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, field_validator


OSCArgument = bool | int | float | str | None


class OSCMessage(BaseModel):
    address: str = Field(..., min_length=1)
    arguments: list[OSCArgument] = Field(default_factory=list)

    @field_validator("address")
    @classmethod
    def _validate_address(cls, value: str) -> str:
        if not value.startswith("/"):
            raise ValueError("OSC address must start with '/'")
        if any(ch.isspace() for ch in value):
            raise ValueError("OSC address cannot contain whitespace")
        return value


class OSCTarget(BaseModel):
    host: str = "127.0.0.1"
    port: int = Field(9000, ge=1, le=65535)


class OSCSendRequest(BaseModel):
    target: OSCTarget = Field(default_factory=OSCTarget)
    message: OSCMessage


class OSCListenRequest(BaseModel):
    host: str = "0.0.0.0"
    port: int = Field(9001, ge=0, le=65535)


class OSCReceivedMessage(OSCMessage):
    remote_host: str
    remote_port: int
    received_at: datetime


class OSCStatus(BaseModel):
    listening: bool
    host: str | None = None
    port: int | None = None
    message_count: int = 0


class OSCMapping(BaseModel):
    id: str
    osc_address: str
    action: Literal["dmx_scene"]
    target_id: str
    universe_id: str | None = None
