"""Minimal OSC 1.0 message codec."""
import struct

from netpi_core.models.osc import OSCArgument, OSCMessage


class OSCDecodeError(ValueError):
    """Raised when an OSC datagram cannot be decoded."""


def _pad(data: bytes) -> bytes:
    padding = (4 - (len(data) % 4)) % 4
    return data + (b"\0" * padding)


def _pack_string(value: str) -> bytes:
    return _pad(value.encode("utf-8") + b"\0")


def _read_string(data: bytes, offset: int) -> tuple[str, int]:
    end = data.find(b"\0", offset)
    if end == -1:
        raise OSCDecodeError("OSC string is not null-terminated")
    try:
        value = data[offset:end].decode("utf-8")
    except UnicodeDecodeError as exc:
        raise OSCDecodeError(f"Invalid UTF-8 string: {exc}") from exc
    next_offset = end + 1
    while next_offset % 4:
        next_offset += 1
    if next_offset > len(data):
        raise OSCDecodeError("OSC string padding exceeds datagram length")
    return value, next_offset


def encode_message(message: OSCMessage) -> bytes:
    """Encode an OSC message datagram."""
    type_tags = [","]
    payload = bytearray()

    for arg in message.arguments:
        if isinstance(arg, bool):
            type_tags.append("T" if arg else "F")
        elif arg is None:
            type_tags.append("N")
        elif isinstance(arg, int):
            type_tags.append("i")
            payload.extend(struct.pack(">i", arg))
        elif isinstance(arg, float):
            type_tags.append("f")
            payload.extend(struct.pack(">f", arg))
        elif isinstance(arg, str):
            type_tags.append("s")
            payload.extend(_pack_string(arg))
        else:
            raise TypeError(f"Unsupported OSC argument type: {type(arg)!r}")

    return _pack_string(message.address) + _pack_string("".join(type_tags)) + bytes(payload)


def decode_message(data: bytes) -> OSCMessage:
    """Decode one OSC message datagram."""
    address, offset = _read_string(data, 0)
    if not address.startswith("/"):
        raise OSCDecodeError("OSC address must start with '/'")

    type_tags, offset = _read_string(data, offset)
    if not type_tags.startswith(","):
        raise OSCDecodeError("OSC type tag string must start with ','")

    arguments: list[OSCArgument] = []
    for tag in type_tags[1:]:
        if tag == "i":
            if offset + 4 > len(data):
                raise OSCDecodeError("Missing int32 argument payload")
            arguments.append(struct.unpack(">i", data[offset:offset + 4])[0])
            offset += 4
        elif tag == "f":
            if offset + 4 > len(data):
                raise OSCDecodeError("Missing float32 argument payload")
            arguments.append(struct.unpack(">f", data[offset:offset + 4])[0])
            offset += 4
        elif tag == "s":
            value, offset = _read_string(data, offset)
            arguments.append(value)
        elif tag == "T":
            arguments.append(True)
        elif tag == "F":
            arguments.append(False)
        elif tag == "N":
            arguments.append(None)
        else:
            raise OSCDecodeError(f"Unsupported OSC type tag {tag!r}")

    return OSCMessage(address=address, arguments=arguments)
