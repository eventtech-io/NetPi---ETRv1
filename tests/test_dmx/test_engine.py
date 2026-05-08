"""Tests for the DMX engine."""
import asyncio
from datetime import datetime, timezone

import pytest

from netpi_core.models.dmx import DMXChannel, DMXUniverse
from netpi_dmx.engine import DMXEngine


class TestUniverseManagement:
    def test_create_universe(self, dmx_engine):
        u = dmx_engine.create_universe("Stage Left")
        assert u.name == "Stage Left"
        assert len(u.channels) == 512

    def test_get_universe(self, dmx_engine):
        u = dmx_engine.create_universe()
        assert dmx_engine.get_universe(u.id) == u
        assert dmx_engine.get_universe("nonexistent") is None

    def test_set_channel(self, dmx_engine):
        u = dmx_engine.create_universe()
        assert dmx_engine.set_channel(u.id, 1, 255) is True
        assert dmx_engine.get_channel(u.id, 1) == 255

    def test_set_channel_clamping(self, dmx_engine):
        u = dmx_engine.create_universe()
        dmx_engine.set_channel(u.id, 1, 999)
        assert dmx_engine.get_channel(u.id, 1) == 255
        dmx_engine.set_channel(u.id, 1, -10)
        assert dmx_engine.get_channel(u.id, 1) == 0

    def test_set_channel_invalid_universe(self, dmx_engine):
        assert dmx_engine.set_channel("fake", 1, 100) is False

    def test_set_channels_batch(self, dmx_engine):
        u = dmx_engine.create_universe()
        channels = [
            DMXChannel(channel=1, value=100),
            DMXChannel(channel=2, value=200),
        ]
        assert dmx_engine.set_channels(u.id, channels) is True
        assert dmx_engine.get_channel(u.id, 1) == 100
        assert dmx_engine.get_channel(u.id, 2) == 200


class TestTransmission:
    @pytest.mark.asyncio
    async def test_start_stop_transmit(self, dmx_engine, mock_dmx_backend):
        u = dmx_engine.create_universe()
        result = await dmx_engine.start_transmit(u.id, rate_hz=44.0)
        assert result is True
        assert u.is_transmitting is True
        assert u.tx_rate_hz == 44.0

        # Give the task one cycle
        await asyncio.sleep(0.03)
        assert len(mock_dmx_backend.sent_universes) >= 1

        stopped = await dmx_engine.stop_transmit(u.id)
        assert stopped is True
        assert u.is_transmitting is False

    @pytest.mark.asyncio
    async def test_send_once(self, dmx_engine, mock_dmx_backend):
        u = dmx_engine.create_universe()
        result = await dmx_engine.send_once(u.id)
        assert result is True
        assert len(mock_dmx_backend.sent_universes) == 1

    @pytest.mark.asyncio
    async def test_transmit_missing_backend(self, dmx_engine):
        dmx_engine._backend = None
        u = dmx_engine.create_universe()
        result = await dmx_engine.start_transmit(u.id)
        assert result is False


class TestReception:
    @pytest.mark.asyncio
    async def test_receive_callbacks(self, dmx_engine, mock_dmx_backend):
        from netpi_core.models.dmx import DMXPacket, DMXPacketTiming
        await dmx_engine.start_receive()

        # Simulate a packet arriving
        packet = DMXPacket(
            timestamp=datetime.now(timezone.utc),
            start_code=0x00,
            slots=[0] * 512,
            timing=DMXPacketTiming(break_us=176.0, mab_us=12.0, slot_count=512),
        )
        if mock_dmx_backend._rx_callback:
            mock_dmx_backend._rx_callback(packet)

        assert dmx_engine.get_latest_packet() == packet
        assert len(dmx_engine.get_received_packets()) == 1

        await dmx_engine.stop_receive()


class TestFlicker:
    def test_flicker_detection(self, dmx_engine):
        from netpi_core.models.dmx import DMXPacket, DMXPacketTiming
        from datetime import datetime, timezone

        events = []
        dmx_engine.on_flicker(lambda e: events.append(e))

        pkt1 = DMXPacket(
            timestamp=datetime.now(timezone.utc),
            start_code=0x00,
            slots=[0] * 512,
            timing=DMXPacketTiming(break_us=176.0, mab_us=12.0, slot_count=512),
        )
        dmx_engine._on_packet_received(pkt1)
        assert len(events) == 0  # First packet establishes baseline

        pkt2 = DMXPacket(
            timestamp=datetime.now(timezone.utc),
            start_code=0x00,
            slots=[100 if i == 0 else 0 for i in range(512)],
            timing=DMXPacketTiming(break_us=176.0, mab_us=12.0, slot_count=512),
        )
        dmx_engine._on_packet_received(pkt2)
        assert len(events) == 1
        assert events[0].channel == 1
        assert events[0].old_value == 0
        assert events[0].new_value == 100


class TestDIPSwitch:
    def test_address_512(self):
        cfg = DMXEngine.calculate_dip_switches(512)
        assert cfg.address == 512
        assert cfg.binary == "111111111"

    def test_address_1(self):
        cfg = DMXEngine.calculate_dip_switches(1)
        assert cfg.address == 1
        assert cfg.binary == "000000000"
        assert cfg.switches_on == []

    def test_address_257(self):
        cfg = DMXEngine.calculate_dip_switches(257)
        assert cfg.address == 257
        assert cfg.binary == "100000000"
        assert cfg.switches_on == [9]



