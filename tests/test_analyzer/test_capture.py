"""Tests for the capture engine."""
import shutil

import pytest
from datetime import datetime, timezone

from netpi_core.models.capture import CaptureFilter, CaptureStatus
from netpi_analyzer.capture.engine import CaptureEngine
from netpi_analyzer.capture.validation import sanitize_bpf, ValidationError


class TestCaptureEngine:
    pytestmark = pytest.mark.skipif(
        shutil.which("tcpdump") is None,
        reason="tcpdump is required for live capture engine integration tests",
    )

    @pytest.mark.asyncio
    async def test_start_stop(self, temp_dir):
        engine = CaptureEngine(data_dir=temp_dir)
        filt = CaptureFilter(interface="lo", max_packets=1)
        session = await engine.start(filt)
        assert session.status == CaptureStatus.RUNNING
        assert session.file_path.endswith(".pcapng")

        stopped = await engine.stop(session.id)
        assert stopped is not None
        assert stopped.status == CaptureStatus.STOPPED
        assert stopped.stopped_at is not None

    @pytest.mark.asyncio
    async def test_get_session(self, temp_dir):
        engine = CaptureEngine(data_dir=temp_dir)
        filt = CaptureFilter(interface="lo", max_packets=1)
        session = await engine.start(filt)
        assert engine.get_session(session.id) == session

        await engine.stop(session.id)
        assert engine.get_session(session.id).status == CaptureStatus.STOPPED

    @pytest.mark.asyncio
    async def test_list_sessions(self, temp_dir):
        engine = CaptureEngine(data_dir=temp_dir)
        assert engine.list_sessions() == []

        s1 = await engine.start(CaptureFilter(interface="lo"))
        s2 = await engine.start(CaptureFilter(interface="lo"))
        assert len(engine.list_sessions()) == 2

        await engine.stop(s1.id)
        await engine.stop(s2.id)


class TestBPFSanitization:
    def test_valid_bpf(self):
        assert sanitize_bpf("port 80") == "port 80"
        assert sanitize_bpf("host 192.168.1.1") == "host 192.168.1.1"

    def test_empty_bpf(self):
        assert sanitize_bpf(None) is None
        assert sanitize_bpf("") == ""

    def test_forbidden_characters(self):
        with pytest.raises(ValidationError):
            sanitize_bpf("port 80; rm -rf /")
        with pytest.raises(ValidationError):
            sanitize_bpf("`whoami`")
        with pytest.raises(ValidationError):
            sanitize_bpf("$(cmd)")

    def test_forbidden_sequences(self):
        with pytest.raises(ValidationError):
            sanitize_bpf("host 1.1.1.1 | cat /etc/passwd")
        with pytest.raises(ValidationError):
            sanitize_bpf("host 1.1.1.1 && echo pwned")


class TestPathValidation:
    def test_valid_path(self):
        from netpi_analyzer.capture.validation import validate_capture_path
        p = validate_capture_path("/var/lib/netpi/captures/abc.pcapng", "/var/lib/netpi/captures")
        assert p.name == "abc.pcapng"

    def test_traversal_blocked(self):
        from netpi_analyzer.capture.validation import validate_capture_path, ValidationError
        with pytest.raises(ValidationError):
            validate_capture_path("/var/lib/netpi/captures/../../etc/passwd", "/var/lib/netpi/captures")

    def test_relative_traversal_blocked(self):
        from netpi_analyzer.capture.validation import validate_capture_path, ValidationError
        with pytest.raises(ValidationError):
            validate_capture_path("/var/lib/netpi/captures/../secret.pcapng", "/var/lib/netpi/captures")



