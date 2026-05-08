from datetime import datetime
from enum import Enum
from pydantic import BaseModel, Field


class CaptureFormat(str, Enum):
    PCAP = "pcap"
    PCAPNG = "pcapng"
    JSON = "json"
    CSV = "csv"


class CaptureStatus(str, Enum):
    RUNNING = "running"
    PAUSED = "paused"
    STOPPED = "stopped"
    ERROR = "error"


class CaptureFilter(BaseModel):
    bpf_expression: str | None = None
    interface: str = "eth0"
    max_packets: int | None = Field(default=None, ge=1)
    max_duration_sec: int | None = Field(default=None, ge=1)
    promiscuous: bool = True
    snaplen: int = Field(default=65535, ge=1)


class CaptureSession(BaseModel):
    id: str
    interface: str
    filter: CaptureFilter
    status: CaptureStatus = CaptureStatus.RUNNING   # BUG-FIX: was bare str
    started_at: datetime
    stopped_at: datetime | None = None
    packet_count: int = 0
    byte_count: int = 0
    file_path: str | None = None
    format: CaptureFormat = CaptureFormat.PCAPNG
    error_message: str | None = None


class PacketSummary(BaseModel):
    timestamp: float
    length: int
    src_mac: str | None = None
    dst_mac: str | None = None
    ethertype: str | None = None
    src_ip: str | None = None
    dst_ip: str | None = None
    protocol: str | None = None
    src_port: int | None = None
    dst_port: int | None = None
    info: str | None = None
    raw_hex: str | None = None
