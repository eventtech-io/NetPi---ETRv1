# NetPi Functions and Capabilities

Review status: automated suite passes with 67 passed and 3 skipped. The skipped tests are live packet-capture tests because `tcpdump` is not installed on this Windows review machine.

## Summary

Most application, model, API, persistence, auth, DMX logic, and mocked hardware flows are working under automated tests. Hardware-dependent functions are implemented, but they still need final validation on the Raspberry Pi/Linux target with the real tools and devices attached.

## Verified Working in Tests

| Area | Functions / endpoints | Capabilities |
|---|---|---|
| Core models | Capture, cable test, device, interface, DMX models | Pydantic validation, enums, default values, bounds checks, DMX DIP switch calculations |
| API auth | `NETPI_API_KEY`, `X-API-Key` protection | Auth disabled when no key is set; protected APIs reject missing/wrong keys; health and metrics stay open |
| Health | `GET /api/v1/health`, `GET /api/v1/ready` | Liveness, readiness, data/capture directory write checks |
| Metrics | `GET /api/v1/metrics` | Request count, error count, per-path counters |
| System API | `GET /`, `GET /api/v1/system/info` | Root metadata, version/features response, system info endpoint |
| Capture API | `POST /capture/start`, `POST /capture/{id}/stop`, `GET /capture`, `GET /capture/{id}`, `GET /capture/{id}/download` | Start/stop/list/get capture sessions, safe download handling, API error behavior |
| Capture validation | `sanitize_bpf`, `validate_capture_path` | Rejects dangerous BPF input and path traversal attempts |
| Cable test API | `GET /cabletest/ports`, `POST /cabletest/ports/{port}/test`, result lookup/listing | Lists cable-testable ports, runs mocked cable tests, stores/loads results |
| DMX universes | Create/list/get universes, set/get channels | 512-channel universe management, channel bounds/clamping, persistence integration |
| DMX transmit logic | Start/stop/send once | Per-universe transmit task handling with mocked backend |
| DMX receive logic | Start/stop receive, latest/history packets | Receive callback flow, latest packet, packet history |
| DMX tester | Levels, timing, flicker finder | Active channel levels, timing data access, flicker event detection |
| DMX fixture library | Profile list/get/modes, add/list fixtures | Generic fixture profiles, mode selection, fixture persistence |
| DMX DIP calculator | `GET /dmx/dip-switch/{address}` | Correct 1-512 address handling, including address 512 |
| DMX scenes | Create/list/get/delete/recall scenes | Save universe state, recall instantly or with fade interpolation |
| OSC | `POST /osc/send`, listener start/stop/status, message history | Send and receive OSC 1.0 UDP messages, keep recent message history, works without special hardware |
| OCA/AES70 | Discovery, manual device registry, TCP probe, class inventory | Discover `_oca._tcp.local.` devices, add OCA devices manually, probe reachability, expose known AES70 classes and expected object skeletons |
| Scheduler | List/start/stop/run scheduled tests | Registers default schedules, runs async diagnostics on demand/interval |
| Database | SQLite manager, migrations, repositories | WAL mode, migrations, capture/DMX/topology/cable repositories |
| CI/dev tooling | Makefile and GitHub Actions | Installs all packages including `netpi-db`, includes `pytest-cov` |

## Implemented, Needs Pi/Linux Hardware Validation

| Area | Functions / endpoints | Capabilities to validate on target |
|---|---|---|
| Live packet capture | `tcpdump` capture engine, `tshark` packet streaming | Actual capture start/stop, packet counts via `capinfos`, WebSocket decoded packet stream |
| Interface discovery | `/system/interfaces`, `/system/interfaces/{iface}/stats` | `/sys/class/net`, `/proc/net/dev`, `ip -j addr`, and `ethtool -i` parsing on Raspberry Pi |
| ARP discovery | `POST /discovery/arp-scan` | Scapy ARP scanning on the selected interface and topology persistence |
| Ping sweep | `POST /discovery/ping-sweep` | ICMP sweep behavior on local network |
| Network tests | Ping, traceroute, iperf3, speedtest endpoints | External command/network behavior, permissions, and installed tools |
| Cable testing | `ethtool --cable-test` backend | Real Pi 4/5 onboard Ethernet support and non-destructive availability detection |
| DMX hardware | USB/UART backend auto-detect, transmit, receive | USB serial adapters, UART serial port, timing, real DMX fixtures/controllers |
| DMX cable test | `/dmx/cabletest/{port_id}` | Loopback behavior with real transceiver/cable hardware |
| RDM discovery | `/dmx/rdm/discover` | Backend discovery plumbing; full E1.20 RDM implementation is still planned |

## Known Partial or Planned Items

| Area | Current behavior |
|---|---|
| RDM | Discovery endpoint exists, but the code notes full RDM E1.20 support is planned |
| OCA/AES70 method control | Discovery and registry are implemented; full OCP.1 binary method/event control is a future phase |
| Scene persistence | Scene engine is in memory; migration notes list DB persistence as future work |
| Schedule persistence | Scheduler state is in memory; persistence is listed as future work |
| Gateway auto-discovery | Default scheduler uses a simplified hardcoded gateway example |
| Topology layout | Export formats exist, but visual layout hints are listed as future work |
