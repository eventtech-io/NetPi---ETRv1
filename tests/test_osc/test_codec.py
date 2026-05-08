"""Tests for OSC encoding and decoding."""
import pytest

from netpi_core.models.osc import OSCMessage
from netpi_osc.codec import OSCDecodeError, decode_message, encode_message


class TestOSCCodec:
    def test_round_trip_supported_arguments(self):
        message = OSCMessage(
            address="/netpi/test",
            arguments=[1, 2.5, "hello", True, False, None],
        )

        decoded = decode_message(encode_message(message))

        assert decoded.address == "/netpi/test"
        assert decoded.arguments[0] == 1
        assert decoded.arguments[1] == pytest.approx(2.5)
        assert decoded.arguments[2:] == ["hello", True, False, None]

    def test_invalid_address_rejected(self):
        with pytest.raises(ValueError):
            OSCMessage(address="bad/address")

    def test_invalid_datagram_rejected(self):
        with pytest.raises(OSCDecodeError):
            decode_message(b"not-osc")
