"""Tests for OCA/AES70 mDNS parsing."""
import socket
import struct

from netpi_oca.mdns import _encode_name, parse_response


def _rr(name: str, rrtype: int, payload: bytes) -> bytes:
    return _encode_name(name) + struct.pack(">HHIH", rrtype, 1, 120, len(payload)) + payload


class TestOCAMDNS:
    def test_parse_dns_sd_response(self):
        service = "_oca._tcp.local."
        instance = "NetPi Test._oca._tcp.local."
        host = "oca-device.local."

        ptr = _rr(service, 12, _encode_name(instance))
        srv_payload = struct.pack(">HHH", 0, 0, 65000) + _encode_name(host)
        srv = _rr(instance, 33, srv_payload)
        txt_values = [b"name=Stage DSP", b"txtvers=1"]
        txt_payload = b"".join(bytes([len(v)]) + v for v in txt_values)
        txt = _rr(instance, 16, txt_payload)
        address = _rr(host, 1, socket.inet_aton("192.0.2.10"))

        header = struct.pack(">HHHHHH", 0, 0x8400, 0, 4, 0, 0)
        devices = parse_response(header + ptr + srv + txt + address)

        assert len(devices) == 1
        assert devices[0].name == "Stage DSP"
        assert devices[0].host == "192.0.2.10"
        assert devices[0].port == 65000
        assert devices[0].service_name == instance
        assert devices[0].txt["txtvers"] == "1"
