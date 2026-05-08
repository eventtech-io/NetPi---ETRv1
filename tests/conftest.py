"""Shared pytest fixtures for NetPi."""
import asyncio
import os
import tempfile
from collections.abc import Generator
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient


# ------------------------------------------------------------------
# Environment / Settings
# ------------------------------------------------------------------

@pytest.fixture(scope="session", autouse=True)
def _test_env() -> None:
    """Ensure all tests run against temp directories."""
    os.environ.setdefault("NETPI_DATA_DIR", tempfile.mkdtemp(prefix="netpi_data_"))
    os.environ.setdefault("NETPI_CAPTURE_DIR", tempfile.mkdtemp(prefix="netpi_cap_"))
    os.environ.setdefault("NETPI_LOG_LEVEL", "DEBUG")


@pytest.fixture
def temp_dir() -> Generator[str, None, None]:
    with tempfile.TemporaryDirectory() as d:
        yield d


@pytest.fixture
def clear_settings_cache() -> None:
    """Clear the cached Settings instance so env changes are picked up."""
    from netpi_core.config import get_settings
    get_settings.cache_clear()


# ------------------------------------------------------------------
# FastAPI App
# ------------------------------------------------------------------

@pytest.fixture
def client(clear_settings_cache) -> Generator[TestClient, None, None]:
    """Yield a TestClient for the NetPi FastAPI app."""
    from netpi_server.main import app
    with TestClient(app) as c:
        yield c


@pytest.fixture
def client_with_auth(clear_settings_cache) -> Generator[TestClient, None, None]:
    """Yield a TestClient with API key auth enabled."""
    old_key = os.environ.get("NETPI_API_KEY")
    os.environ["NETPI_API_KEY"] = "test-secret-key"
    from netpi_core.config import get_settings
    get_settings.cache_clear()
    from netpi_server.main import app
    with TestClient(app) as c:
        yield c
    if old_key is None:
        os.environ.pop("NETPI_API_KEY", None)
    else:
        os.environ["NETPI_API_KEY"] = old_key
    get_settings.cache_clear()


# ------------------------------------------------------------------
# Mocked DMX Backend
# ------------------------------------------------------------------

class MockDMXBackend:
    name = "mock"

    def __init__(self) -> None:
        self._open = False
        self.sent_universes: list = []
        self._rx_callback = None

    async def open(self) -> bool:
        self._open = True
        return True

    async def close(self) -> None:
        self._open = False

    async def is_available(self) -> bool:
        return True

    async def send_universe(self, universe) -> bool:
        self.sent_universes.append(universe)
        return True

    async def start_receiver(self, callback) -> None:
        self._rx_callback = callback

    async def stop_receiver(self) -> None:
        self._rx_callback = None

    async def send_rdm_discovery(self) -> list[str]:
        return ["1234:5678", "9abc:def0"]

    async def send_rdm_get(self, uid: str, pid: int, sub_device: int = 0):
        return None

    async def send_rdm_set(self, uid: str, pid: int, data: bytes, sub_device: int = 0) -> bool:
        return False


@pytest.fixture
def mock_dmx_backend() -> MockDMXBackend:
    return MockDMXBackend()


@pytest.fixture
def dmx_engine(mock_dmx_backend):
    """Yield a DMXEngine with a mocked backend."""
    from netpi_dmx.engine import DMXEngine
    engine = DMXEngine()
    engine._backend = mock_dmx_backend
    yield engine
    # Cleanup any stray tasks
    for uni_id in list(engine._tx_tasks):
        engine._tx_tasks[uni_id].cancel()


# ------------------------------------------------------------------
# Mocked Capture Engine
# ------------------------------------------------------------------

@pytest.fixture
def mock_capture_engine(monkeypatch):
    """Replace the global CaptureEngine with an in-memory mock."""
    from netpi_analyzer.capture.engine import CaptureEngine

    class MockCaptureEngine(CaptureEngine):
        def __init__(self):
            self._sessions = {}
            self._processes = {}
            self._db_repo = None

        async def start(self, filter_cfg):
            import uuid
            from datetime import datetime, timezone
            from netpi_core.models.capture import CaptureSession, CaptureStatus
            session = CaptureSession(
                id=str(uuid.uuid4()),
                interface=filter_cfg.interface,
                filter=filter_cfg,
                status=CaptureStatus.RUNNING,
                started_at=datetime.now(timezone.utc),
                file_path="/tmp/fake.pcapng",
                format="pcapng",
            )
            self._sessions[session.id] = session
            return session

        async def stop(self, session_id):
            session = self._sessions.get(session_id)
            if session:
                from netpi_core.models.capture import CaptureStatus
                session.status = CaptureStatus.STOPPED
                session.stopped_at = datetime.now(timezone.utc)
            return session

        def get_session(self, session_id):
            return self._sessions.get(session_id)

        def list_sessions(self):
            return list(self._sessions.values())

        async def stream_packets(self, session_id):
            return
            yield  # type: ignore

    mock = MockCaptureEngine()
    monkeypatch.setattr("netpi_analyzer.capture.engine._engine", mock)
    return mock


# ------------------------------------------------------------------
# Mocked Cable Test Registry
# ------------------------------------------------------------------

@pytest.fixture
def mock_cabletest_registry(monkeypatch):
    """Return a mocked cable test backend."""
    from netpi_core.models.cabletest import CableTestResult, CableStatus, PairResult, PairStatus

    async def fake_test(port_id: str):
        import uuid

        return CableTestResult(
            id=str(uuid.uuid4()),
            port_id=port_id,
            backend="mock",
            timestamp=datetime.now(timezone.utc),
            status=CableStatus.OK,
            pairs=[
                PairResult(pair="1-2", status=PairStatus.OK, length_m=10.5),
                PairResult(pair="3-6", status=PairStatus.OK, length_m=10.5),
            ],
            duration_ms=120,
        )

    async def fake_available(port_id: str):
        return port_id in ("eth0", "eth1")

    mock_backend = MagicMock()
    mock_backend.test = fake_test
    mock_backend.is_available = fake_available
    mock_backend.name = "mock"

    mock_registry = MagicMock()
    async def fake_find_backend(port_id: str):
        return mock_backend if await fake_available(port_id) else None

    mock_registry.find_backend = AsyncMock(side_effect=fake_find_backend)
    mock_registry.test = AsyncMock(side_effect=fake_test)

    monkeypatch.setattr("netpi_cabletester.registry.get_registry", lambda: mock_registry)
    return mock_registry



