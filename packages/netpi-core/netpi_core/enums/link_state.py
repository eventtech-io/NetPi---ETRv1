from enum import Enum
class LinkState(str, Enum):
    UP = "up"
    DOWN = "down"
    DORMANT = "dormant"
    UNKNOWN = "unknown"
