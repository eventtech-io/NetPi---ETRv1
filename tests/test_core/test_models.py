"""Tests for netpi-core Pydantic models."""
import pytest
from pydantic import ValidationError

from netpi_core.models.capture import CaptureFilter, CaptureSession, CaptureStatus, PacketSummary
from netpi_core.models.cabletest import PairStatus, CableStatus, PairResult, CableTestResult
from netpi_core.models.dmx import DMXChannel, DMXUniverse, DIPSwitchConfig
from netpi_core.models.device import Device
from netpi_core.models.interface import Interface
from netpi_core.enums.link_state import LinkState


class TestCaptureFilter:
    def test_defaults(self):
        f = CaptureFilter()
        assert f.interface == "eth0"
        assert f.promiscuous is True
        assert f.snaplen == 65535

    def test_bpf_optional(self):
        f = CaptureFilter(bpf_expression="port 80")
        assert f.bpf_expression == "port 80"

    def test_snaplen_range(self):
        with pytest.raises(ValidationError):
            CaptureFilter(snaplen=-1)


class TestCaptureSession:
    def test_status_enum(self):
        from datetime import datetime, timezone
        s = CaptureSession(
            id="abc",
            interface="eth0",
            filter=CaptureFilter(),
            status=CaptureStatus.RUNNING,
            started_at=datetime.now(timezone.utc),
        )
        assert s.status == CaptureStatus.RUNNING


class TestDMXModels:
    def test_channel_bounds(self):
        with pytest.raises(ValidationError):
            DMXChannel(channel=0, value=0)
        with pytest.raises(ValidationError):
            DMXChannel(channel=1, value=256)

    def test_universe_default_channels(self):
        u = DMXUniverse(id="u1", name="Test")
        assert len(u.channels) == 512
        assert all(v == 0 for v in u.channels)

    def test_dip_switch_512(self):
        cfg = DMXUniverse.calculate_dip_switches(512)
        assert cfg.address == 512
        assert cfg.binary == "111111111"
        assert cfg.switches_on == [1, 2, 3, 4, 5, 6, 7, 8, 9]

    def test_dip_switch_1(self):
        cfg = DMXUniverse.calculate_dip_switches(1)
        assert cfg.address == 1
        assert cfg.binary == "000000000"
        assert cfg.switches_on == []


class TestCableTest:
    def test_pair_result(self):
        p = PairResult(pair="1-2", status=PairStatus.OK, length_m=12.3)
        assert p.status == PairStatus.OK

    def test_cable_status_enum(self):
        assert CableStatus.OK == "ok"
        assert CableStatus.FAULT == "fault"


class TestDevice:
    def test_device_creation(self):
        from datetime import datetime, timezone
        d = Device(
            id="dev-1",
            ip_address="192.168.1.1",
            mac_address="aa:bb:cc:dd:ee:ff",
            first_seen=datetime.now(timezone.utc),
            last_seen=datetime.now(timezone.utc),
        )
        assert d.is_online is True


class TestInterface:
    def test_link_state_default(self):
        iface = Interface(name="eth0", index=0)
        assert iface.link_state == LinkState.UNKNOWN



