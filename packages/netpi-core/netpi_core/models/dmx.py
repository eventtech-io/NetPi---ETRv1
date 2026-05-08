"""DMX512 and RDM models."""
from datetime import datetime
from enum import Enum
from pydantic import BaseModel, Field

class DMXChannel(BaseModel):
    channel: int = Field(..., ge=1, le=512)
    value: int = Field(0, ge=0, le=255)
    label: str | None = None

class DMXUniverse(BaseModel):
    id: str
    name: str = "Universe 1"
    channels: list[int] = Field(default_factory=lambda: [0] * 512)
    is_transmitting: bool = False
    tx_rate_hz: float = 44.0
    last_updated: datetime | None = None

    @staticmethod
    def calculate_dip_switches(address: int, step_size: int = 1):
        address = max(1, min(512, address))
        zero_indexed = address - 1
        binary = format(zero_indexed, "09b")
        switches_on = [
            i + 1
            for i, bit in enumerate(reversed(binary))
            if bit == "1"
        ]
        return DIPSwitchConfig(
            address=address,
            binary=binary,
            switches_on=switches_on,
            step_size=step_size,
        )

class DMXFixtureChannel(BaseModel):
    name: str
    offset: int = Field(..., ge=0, le=511)
    default_value: int = 0
    current_value: int = 0

class DMXFixture(BaseModel):
    id: str; name: str
    manufacturer: str | None = None; model: str | None = None; mode: str | None = None
    start_address: int = Field(..., ge=1, le=512)
    channel_count: int = Field(..., ge=1, le=512)
    channels: list[DMXFixtureChannel] = Field(default_factory=list)
    is_rdm: bool = False; rdm_uid: str | None = None

class RDMDevice(BaseModel):
    uid: str
    manufacturer: str | None = None; model: str | None = None
    device_label: str | None = None
    dmx_start_address: int | None = None
    footprint: int | None = None
    personality: int | None = None; personality_description: str | None = None
    sub_device_count: int = 0; sensor_count: int = 0
    lamp_hours: int | None = None; device_hours: int | None = None
    software_version_id: int | None = None; software_version_label: str | None = None
    is_identifying: bool = False; last_seen: datetime | None = None

class RDMSensor(BaseModel):
    uid: str; sensor_number: int
    description: str | None = None; type: str | None = None
    unit: str | None = None; prefix: str | None = None
    range_min: int | None = None; range_max: int | None = None
    normal_min: int | None = None; normal_max: int | None = None
    recorded_value: int | None = None; present_value: int | None = None

class DMXPacketTiming(BaseModel):
    break_us: float; mab_us: float
    slot_count: int
    inter_slot_us: float | None = None
    packet_rate_hz: float | None = None
    jitter_us: float | None = None

class DMXPacket(BaseModel):
    timestamp: datetime
    start_code: int = 0x00
    slots: list[int] = Field(default_factory=list)
    timing: DMXPacketTiming | None = None

class DMXCableTestResult(BaseModel):
    id: str; port_id: str; timestamp: datetime
    pin1_shield: bool = False
    pin2_data_minus: bool = False
    pin3_data_plus: bool = False
    pin4: bool = False; pin5: bool = False
    shorts: list[str] = Field(default_factory=list)
    status: str = "unknown"
    loopback_detected: bool = False

class DMXFlickerEvent(BaseModel):
    channel: int; old_value: int; new_value: int; timestamp: datetime

class DIPSwitchConfig(BaseModel):
    address: int = Field(..., ge=1, le=512)
    binary: str
    switches_on: list[int] = Field(default_factory=list)
    step_size: int = 1
