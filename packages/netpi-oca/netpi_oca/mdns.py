"""Small DNS-SD/mDNS discovery helper for OCA/AES70 services."""
import asyncio
import socket
import struct
from dataclasses import dataclass, field
from datetime import datetime, timezone

from netpi_core.models.oca import OCADevice

MDNS_GROUP = "224.0.0.251"
MDNS_PORT = 5353


@dataclass
class _ServiceRecord:
    fullname: str
    host: str | None = None
    port: int | None = None
    txt: dict[str, str] = field(default_factory=dict)


def _encode_name(name: str) -> bytes:
    labels = name.rstrip(".").split(".")
    return b"".join(bytes([len(label)]) + label.encode("utf-8") for label in labels) + b"\0"


def _read_name(data: bytes, offset: int) -> tuple[str, int]:
    labels: list[str] = []
    jumped = False
    next_offset = offset
    seen: set[int] = set()

    while True:
        if offset >= len(data):
            raise ValueError("DNS name exceeds packet length")
        length = data[offset]
        if length == 0:
            offset += 1
            if not jumped:
                next_offset = offset
            return ".".join(labels) + ".", next_offset
        if length & 0xC0 == 0xC0:
            if offset + 1 >= len(data):
                raise ValueError("DNS compression pointer exceeds packet length")
            pointer = ((length & 0x3F) << 8) | data[offset + 1]
            if pointer in seen:
                raise ValueError("DNS compression pointer loop")
            seen.add(pointer)
            if not jumped:
                next_offset = offset + 2
            offset = pointer
            jumped = True
            continue
        offset += 1
        label = data[offset:offset + length].decode("utf-8", errors="replace")
        labels.append(label)
        offset += length
        if not jumped:
            next_offset = offset


def _build_query(service_type: str) -> bytes:
    header = struct.pack(">HHHHHH", 0, 0, 1, 0, 0, 0)
    # QU response bit requests unicast replies back to this socket.
    question = _encode_name(service_type) + struct.pack(">HH", 12, 0x8001)
    return header + question


def _parse_txt(payload: bytes) -> dict[str, str]:
    values: dict[str, str] = {}
    offset = 0
    while offset < len(payload):
        length = payload[offset]
        offset += 1
        chunk = payload[offset:offset + length]
        offset += length
        if not chunk:
            continue
        text = chunk.decode("utf-8", errors="replace")
        if "=" in text:
            key, value = text.split("=", 1)
            values[key] = value
        else:
            values[text] = ""
    return values


def parse_response(data: bytes) -> list[OCADevice]:
    """Parse a DNS-SD response and return OCA devices found in it."""
    if len(data) < 12:
        return []

    _, _, qdcount, ancount, nscount, arcount = struct.unpack(">HHHHHH", data[:12])
    offset = 12

    for _ in range(qdcount):
        _, offset = _read_name(data, offset)
        offset += 4

    records: dict[str, _ServiceRecord] = {}
    host_addresses: dict[str, str] = {}

    for _ in range(ancount + nscount + arcount):
        name, offset = _read_name(data, offset)
        if offset + 10 > len(data):
            break
        rrtype, _, _, rdlength = struct.unpack(">HHIH", data[offset:offset + 10])
        offset += 10
        rdata_start = offset
        rdata_end = offset + rdlength
        if rdata_end > len(data):
            break

        if rrtype == 12:
            service_name, _ = _read_name(data, rdata_start)
            records.setdefault(service_name, _ServiceRecord(fullname=service_name))
        elif rrtype == 33:
            if rdlength >= 6:
                _, _, port = struct.unpack(">HHH", data[rdata_start:rdata_start + 6])
                target, _ = _read_name(data, rdata_start + 6)
                record = records.setdefault(name, _ServiceRecord(fullname=name))
                record.host = target
                record.port = port
        elif rrtype == 16:
            record = records.setdefault(name, _ServiceRecord(fullname=name))
            record.txt.update(_parse_txt(data[rdata_start:rdata_end]))
        elif rrtype == 1 and rdlength == 4:
            host_addresses[name] = socket.inet_ntoa(data[rdata_start:rdata_end])
        elif rrtype == 28 and rdlength == 16:
            host_addresses[name] = socket.inet_ntop(socket.AF_INET6, data[rdata_start:rdata_end])

        offset = rdata_end

    now = datetime.now(timezone.utc)
    devices: list[OCADevice] = []
    for record in records.values():
        if not record.port:
            continue
        host = record.host or record.fullname
        address = host_addresses.get(host, host.rstrip("."))
        devices.append(
            OCADevice(
                id=f"{address}:{record.port}",
                name=record.txt.get("name") or record.fullname.rstrip("."),
                host=address,
                port=record.port,
                transport="tcp",
                service_name=record.fullname,
                txt=record.txt,
                source="mdns",
                discovered_at=now,
                last_seen=now,
            )
        )

    return devices


class MDNSDiscovery:
    """Discover OCA/AES70 devices advertised with DNS-SD."""

    async def discover(self, service_type: str = "_oca._tcp.local.", timeout_sec: float = 1.0) -> list[OCADevice]:
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, self._discover_sync, service_type, timeout_sec)

    def _discover_sync(self, service_type: str, timeout_sec: float) -> list[OCADevice]:
        query = _build_query(service_type)
        devices: dict[str, OCADevice] = {}

        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP) as sock:
            sock.settimeout(timeout_sec)
            sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, 1)
            try:
                sock.sendto(query, (MDNS_GROUP, MDNS_PORT))
            except OSError:
                return []

            while True:
                try:
                    packet, _ = sock.recvfrom(9000)
                except socket.timeout:
                    break
                except OSError:
                    break
                for device in parse_response(packet):
                    devices[device.id] = device

        return list(devices.values())
