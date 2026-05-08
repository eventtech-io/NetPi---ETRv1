# NetPi Test Suite

## Structure

```
tests/
├── conftest.py              # Shared fixtures (mock backends, TestClient, temp dirs)
├── test_core/
│   └── test_models.py       # Pydantic model validation tests
├── test_analyzer/
│   └── test_capture.py      # Capture engine + BPF sanitization tests
├── test_dmx/
│   └── test_engine.py       # DMX engine, transmission, flicker, DIP switch tests
└── test_server/
    ├── test_system.py       # Health, metrics, root endpoint tests
    ├── test_auth.py         # API key auth tests
    ├── test_capture_api.py  # Capture REST API tests
    ├── test_dmx_api.py      # DMX REST API tests
    └── test_cabletest_api.py # Cable test REST API tests
```

## Running Tests

### With Makefile (recommended)
```bash
make install   # Create venv and install all packages
make test      # Run full suite
make test-verbose  # Run with debug logging
make test-coverage # Generate HTML coverage report
```

### Manual
```bash
python -m venv .venv
source .venv/bin/activate
pip install --upgrade pip hatchling

# Install all netpi packages
for pkg in packages/netpi-core packages/netpi-analyzer packages/netpi-cabletester packages/netpi-discovery packages/netpi-dmx packages/netpi-tests packages/netpi-server; do
    pip install -e "$pkg"
done

pip install pytest pytest-asyncio httpx
pytest tests/ -v
```

## Fixtures

### `client`
FastAPI `TestClient` against the real app. Database is mocked via temp directories.

### `client_with_auth`
Same as `client`, but `NETPI_API_KEY=test-secret-key` is set. Use to test protected endpoints.

### `dmx_engine`
`DMXEngine` with a `MockDMXBackend` attached. Safe to use in CI (no hardware).

### `mock_capture_engine`
In-memory `CaptureEngine` that never spawns `tcpdump`. Returns fake sessions instantly.

### `mock_cabletest_registry`
Mocked cable test backend that always returns OK results for `eth0`/`eth1`.

## Writing New Tests

1. Create a file under the appropriate `test_*/` directory.
2. Import fixtures from `conftest.py` implicitly (pytest magic).
3. Use `pytest.mark.asyncio` for any async test functions.
4. For router tests, use `client.post(...)` / `client.get(...)` and assert on status codes and JSON bodies.

## CI

GitHub Actions workflow (`.github/workflows/ci.yml`) runs on Python 3.11 and 3.12 on every push/PR.



