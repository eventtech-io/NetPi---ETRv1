from enum import Enum
class CableStatusEnum(str, Enum):
    OK = "ok"; FAULT = "fault"; DISCONNECTED = "disconnected"; UNKNOWN = "unknown"
