from datetime import datetime
from enum import Enum
from pydantic import BaseModel, Field

class PairStatus(str, Enum):
    OK = "ok"; OPEN = "open"; SHORT = "short"
    SHORT_TO_PAIR = "short_to_pair"; CROSSTALK = "crosstalk"; UNKNOWN = "unknown"

class CableStatus(str, Enum):
    OK = "ok"; FAULT = "fault"; DISCONNECTED = "disconnected"; UNKNOWN = "unknown"

class PairResult(BaseModel):
    pair: str = Field(..., description="e.g. '1-2', '3-6'")
    status: PairStatus
    length_m: float | None = Field(None, description="Estimated cable length in metres")
    fault_distance_m: float | None = Field(None, description="Distance to fault in metres")
    remote_status: str | None = None

class CableTestResult(BaseModel):
    id: str
    port_id: str = Field(..., description="Interface name, e.g. 'eth0'")
    backend: str = Field(..., description="Backend used: ethtool")
    timestamp: datetime
    status: CableStatus
    pairs: list[PairResult] = Field(default_factory=list)
    overall_length_m: float | None = None
    velocity_factor: float = 0.67
    duration_ms: int = 0
