from pydantic import BaseModel, Field
from ..enums.link_state import LinkState

class Interface(BaseModel):
    name: str
    index: int
    mac_address: str | None = None
    ip_addresses: list[str] = Field(default_factory=list)
    link_state: LinkState = LinkState.UNKNOWN
    speed_mbps: int | None = None
    duplex: str | None = None
    mtu: int = 1500
    is_loopback: bool = False
    is_wireless: bool = False
    supports_cable_test: bool = False

class InterfaceStats(BaseModel):
    interface: str
    rx_bytes: int; tx_bytes: int
    rx_packets: int; tx_packets: int
    rx_errors: int; tx_errors: int
    rx_dropped: int; tx_dropped: int
    collisions: int
