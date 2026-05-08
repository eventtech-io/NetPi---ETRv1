"""Link Layer Discovery Protocol (LLDP) parser."""
from dataclasses import dataclass, field
from scapy.layers.l2 import Ether

@dataclass
class LLDPPacket:
    chassis_id: str | None = None
    chassis_id_subtype: int | None = None
    port_id: str | None = None
    port_id_subtype: int | None = None
    ttl: int | None = None
    port_description: str | None = None
    system_name: str | None = None
    system_description: str | None = None
    capabilities: list[str] = field(default_factory=list)
    management_addresses: list[str] = field(default_factory=list)
    vlan_id: int | None = None

def parse_lldp(raw_bytes: bytes) -> LLDPPacket | None:
    try:
        pkt = Ether(raw_bytes)
        if pkt.type != 0x88CC:
            return None
        data = bytes(pkt.payload)
        lldp = LLDPPacket()
        offset = 0
        while offset + 2 <= len(data):
            typ = (data[offset] >> 1) & 0x7F
            length = ((data[offset] & 0x01) << 8) | data[offset + 1]
            offset += 2
            if offset + length > len(data):
                break
            value = data[offset:offset + length]
            if typ == 1:
                lldp.chassis_id_subtype = value[0]
                lldp.chassis_id = _format_chassis(value[0], value[1:])
            elif typ == 2:
                lldp.port_id_subtype = value[0]
                lldp.port_id = _format_port(value[0], value[1:])
            elif typ == 3:
                lldp.ttl = int.from_bytes(value[:2], "big")
            elif typ == 4:
                lldp.port_description = value.decode("utf-8", errors="ignore").strip("\x00")
            elif typ == 5:
                lldp.system_name = value.decode("utf-8", errors="ignore").strip("\x00")
            elif typ == 6:
                lldp.system_description = value.decode("utf-8", errors="ignore").strip("\x00")
            elif typ == 7:
                lldp.capabilities = _parse_sys_caps(int.from_bytes(value[:2], "big"))
            elif typ == 8:
                lldp.management_addresses.extend(_parse_mgmt_addr(value))
            elif typ == 127:
                oui = value[:3]
                subtype = value[3] if len(value) > 3 else None
                if oui == b"\x00\x80\xc2" and subtype == 0x01 and len(value) >= 7:
                    lldp.vlan_id = int.from_bytes(value[5:7], "big")
            offset += length
            if typ == 0:
                break
        return lldp
    except Exception:
        return None

def _format_chassis(subtype: int, value: bytes) -> str:
    if subtype == 4:
        return ":".join(f"{b:02x}" for b in value)
    elif subtype == 5 and len(value) > 1 and value[0] == 1:
        return ".".join(str(b) for b in value[1:5])
    return value.decode("utf-8", errors="ignore").strip("\x00")

def _format_port(subtype: int, value: bytes) -> str:
    if subtype == 3:
        return ":".join(f"{b:02x}" for b in value)
    elif subtype == 4 and len(value) > 1 and value[0] == 1:
        return ".".join(str(b) for b in value[1:5])
    return value.decode("utf-8", errors="ignore").strip("\x00")

def _parse_sys_caps(cap_int: int) -> list[str]:
    mapping = {
        0x0001: "other", 0x0002: "repeater", 0x0004: "bridge",
        0x0008: "wlan_access_point", 0x0010: "router", 0x0020: "telephone",
        0x0040: "docsis", 0x0080: "station_only",
    }
    return [name for bit, name in mapping.items() if cap_int & bit]

def _parse_mgmt_addr(value: bytes) -> list[str]:
    if len(value) < 2:
        return []
    addr_len = value[0]
    if addr_len == 5 and value[1] == 1:
        return [".".join(str(b) for b in value[2:6])]
    return []
