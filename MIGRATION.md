# NetPi Feature Expansion (v0.2.1 → v0.3.0)

This patch adds DMX scene management, scheduled background network tests, and topology export formats.

---

## What Changed

### 1. DMX Scene / Preset Engine
**New file:** `packages/netpi-dmx/netpi_dmx/scenes.py`

- **Scene snapshots:** Save the current 512-channel state of any universe as a named scene.
- **Smooth fades:** Recall a scene with an optional `fade_ms` parameter. The engine interpolates every channel value at the DMX frame rate (default 44 Hz) using an async background task.
- **Fade cancellation:** Starting a new fade or recalling another scene automatically cancels the active fade for that universe.
- **Fade step callbacks:** Subscribe to per-channel value changes during a fade for real-time WebSocket streaming.

**New endpoints:**

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/api/v1/dmx/universes/{id}/scenes` | Save current state as scene |
| `GET` | `/api/v1/dmx/universes/{id}/scenes` | List scenes for universe |
| `GET` | `/api/v1/dmx/scenes/{scene_id}` | Get scene by ID |
| `DELETE` | `/api/v1/dmx/scenes/{scene_id}` | Delete scene |
| `POST` | `/api/v1/dmx/universes/{id}/scenes/{scene_id}/recall` | Recall with optional `fade_ms` |

**Example:**
```bash
curl -X POST "http://pi:8080/api/v1/dmx/universes/{uid}/scenes?fade_ms=2000"   -H "X-API-Key: secret"
```

### 2. Scheduled Network Tests
**New file:** `packages/netpi-server/netpi_server/scheduler.py`

A lightweight asyncio task scheduler (no Celery, no Redis) for recurring diagnostics:

- Register any async coroutine factory with an interval.
- Start/stop individual schedules or all at once.
- `run_once()` for ad-hoc execution outside the loop.
- Event callbacks for WebSocket broadcasting on degradation.

**Default schedules (registered on startup, disabled by default):**

| ID | Name | Interval | Description |
|----|------|----------|-------------|
| `ping_gateway` | Gateway Ping | 60s | Ping default gateway |
| `speedtest` | Internet Speedtest | 3600s | `speedtest-cli` run |

**New endpoints:**

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/api/v1/scheduler` | List all schedules + last results |
| `POST` | `/api/v1/scheduler/{id}/start` | Start the loop |
| `POST` | `/api/v1/scheduler/{id}/stop` | Stop the loop |
| `POST` | `/api/v1/scheduler/{id}/run` | Execute once immediately |

### 3. Topology Export
**New file:** `packages/netpi-discovery/netpi_discovery/export.py`

Three export formats from the same topology data:

| Format | Endpoint | MIME Type | Use Case |
|--------|----------|-----------|----------|
| Cytoscape.js | `/api/v1/discovery/topology/cytoscape` | `application/json` | Web visualization |
| Graphviz DOT | `/api/v1/discovery/topology/graphviz` | `text/vnd.graphviz` | `dot -Tpng` rendering |
| NDJSON | `/api/v1/discovery/topology/jsonl` | `application/x-ndjson` | Streaming import to Elastic/BigQuery |

Graphviz export uses color-coded nodes:
- Server: blue (`#4a90d9`)
- Switch: green (`#7ed957`)
- Host: orange (`#f5a623`)
- Unknown: gray (`#d9d9d9`)

### 4. Application Lifecycle Updates
**Updated:** `packages/netpi-server/netpi_server/main.py`

Startup sequence now includes:
1. Configure logging
2. Connect SQLite + migrations
3. Attach capture repository
4. Auto-detect DMX backend
5. **Register default scheduled tests**

Shutdown gracefully stops:
1. Scheduled test loops
2. DMX TX tasks
3. Database connection

---

## API Changes

### New Endpoints

All under `/api/v1/`:

- `POST /dmx/universes/{id}/scenes`
- `GET /dmx/universes/{id}/scenes`
- `GET /dmx/scenes/{id}`
- `DELETE /dmx/scenes/{id}`
- `POST /dmx/universes/{id}/scenes/{scene_id}/recall`
- `GET /scheduler`
- `POST /scheduler/{id}/start`
- `POST /scheduler/{id}/stop`
- `POST /scheduler/{id}/run`
- `GET /discovery/topology/cytoscape`
- `GET /discovery/topology/graphviz`
- `GET /discovery/topology/jsonl`

### Version Bump
`version` field in `main.py` and root endpoint updated to **0.3.0**.

---

## Zero New Dependencies

The scene engine, scheduler, and export formats use only the Python standard library and existing NetPi packages. No `pip install` required.

---

## Future Enhancements

- **Scene persistence:** Wire `SceneEngine` to `netpi-db` so scenes survive restarts.
- **WebSocket fade streaming:** Connect `on_fade_step` to a `/ws/dmx/fade` endpoint.
- **Schedule persistence:** Save enabled/disabled state and custom intervals to SQLite.
- **Gateway auto-discovery:** Parse `/proc/net/route` instead of hardcoding `192.168.1.1`.
- **Topology layout:** Add Cytoscape `position` hints from LLDP/CDP coordinate data.



