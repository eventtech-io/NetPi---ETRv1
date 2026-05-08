"""Cisco Discovery Protocol (CDP) parser using Scapy."""
from dataclasses import dataclass, field

from scapy.layers.l2 import Ether


@dataclass
class CDPPacket:
    device_id: str | None = None
    # BUG-FIX: was `= None  # type: ignore` — use dataclass field() for mutable defaults
    addresses: list[str] = field(default_factory=list)
    port_id: str | None = None
    capabilities: list[str] = field(default_factory=list)
    software_version: str | None = None
    platform: str | None = None
    native_vlan: int | None = None
    duplex: str | None = None
    voip_vlan: int | None = None


def parse_cdp(raw_bytes: bytes) -> CDPPacket | None:
    """Parse a raw Ethernet frame for CDP."""
    try:
        pkt = Ether(raw_bytes)

        if pkt.type == 0x2000:
            cdp_data = bytes(pkt.payload)
        else:
            # Check for LLC/SNAP encapsulation (802.3 + SNAP header)
            payload = bytes(pkt.payload)
            # SNAP: AA AA 03 <OUI 3 bytes> <EtherType/PID 2 bytes>
            if len(payload) < 8 or payload[:3] != b"\xaa\xaa\x03":
                return None
            # Cisco OUI: 00 00 0C, CDP PID: 20 00
            if payload[3:6] != b"\x00\x00\x0c" or payload[6:8] != b"\x20\x00":
                return None
            cdp_data = payload[8:]

        if len(cdp_data) < 4:
            return None

        # CDP header: version(1) + ttl(1) + checksum(2)
        offset = 4
        cdp = CDPPacket()

        while offset + 4 <= len(cdp_data):
            typ = int.from_bytes(cdp_data[offset:offset + 2], "big")
            length = int.from_bytes(cdp_data[offset + 2:offset + 4], "big")
            if length < 4 or offset + length > len(cdp_data):
                break
            value = cdp_data[offset + 4:offset + length]

            if typ == 0x0001:
                cdp.device_id = value.decode("utf-8", errors="ignore").strip("\x00")
            elif typ == 0x0002:
                cdp.addresses = _parse_addresses(value)
            elif typ == 0x0003:
                cdp.port_id = value.decode("utf-8", errors="ignore").strip("\x00")
            elif typ == 0x0004:
                cdp.capabilities = _parse_capabilities(int.from_bytes(value[:4], "big"))
            elif typ == 0x0005:
                cdp.software_version = value.decode("utf-8", errors="ignore").strip("\x00")
            elif typ == 0x0006:
                cdp.platform = value.decode("utf-8", errors="ignore").strip("\x00")
            elif typ == 0x000A:
                cdp.native_vlan = int.from_bytes(value[:2], "big")
            elif typ == 0x000B:
                cdp.duplex = "full" if value[0] == 1 else "half"
            elif typ == 0x0011:
                cdp.voip_vlan = int.from_bytes(value[:2], "big")

            offset += length

        return cdp
    except Exception:
        return None


def _parse_addresses(data: bytes) -> list[str]:
    """Parse CDP address list TLV value.

    Layout per address entry:
      Protocol Type  : 1 byte  (1=NLPID, 2=802.2)
      Protocol Length: 1 byte
      Protocol       : proto_len bytes
      Address Length : 2 bytes    ← BUG-FIX: was incorrectly reading 4 bytes
      Address        : addr_len bytes
    """
    if len(data) < 4:
        return []
    count = int.from_bytes(data[:4], "big")
    addrs: list[str] = []
    offset = 4

    for _ in range(count):
        if offset + 2 > len(data):
            break
        proto_type = data[offset]
        proto_len = data[offset + 1]
        offset += 2

        if offset + proto_len + 2 > len(data):
            break
        offset += proto_len  # skip protocol bytes

        addr_len = int.from_bytes(data[offset:offset + 2], "big")
        offset += 2

        if offset + addr_len > len(data):
            break

        # IPv4: proto_type=1, proto_len=1 (NLPID 0xCC = IP), addr_len=4
        if proto_type == 1 and proto_len == 1 and addr_len == 4:
            ip = ".".join(str(b) for b in data[offset:offset + 4])
            addrs.append(ip)

        offset += addr_len

    return addrs


def _parse_capabilities(cap_int: int) -> list[str]:
    caps: list[str] = []
    mapping = {
        0x01: "router",
        0x02: "transparent_bridge",
        0x04: "source_route_bridge",
        0x08: "switch",
        0x10: "host",
        0x20: "igmp",
        0x40: "repeater",
        0x80: "phone",
    }
    for bit, name in mapping.items():
        if cap_int & bit:
            caps.append(name)
    return caps
