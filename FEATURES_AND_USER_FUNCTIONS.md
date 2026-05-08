# NetPi Features and User Functions

Version: 0.3.0

Live local API while developed here: `http://127.0.0.1:8091/`

Interactive API docs: `http://127.0.0.1:8091/docs`

## Current Feature Set

NetPi is a network, DMX, show-control, and AV-control toolkit for Raspberry Pi 4/5 and local development. It includes packet capture, cable testing, network discovery, diagnostics, DMX512/RDM tools, OSC, OCA/AES70 discovery, scheduling, topology export, health checks, metrics, API-key auth, and SQLite persistence.

## System and App

User functions:

- View app name, version, status, auth state, and enabled features.
- View host/system info.
- List network interfaces.
- View per-interface packet/byte/error/drop statistics.
- Check app health and readiness.
- View request metrics.

API:

- `GET /`
- `GET /api/v1/system/info`
- `GET /api/v1/system/interfaces`
- `GET /api/v1/system/interfaces/{iface}/stats`
- `GET /api/v1/health`
- `GET /api/v1/ready`
- `GET /api/v1/metrics`

## Security

User functions:

- Run with open local/demo access when no API key is configured.
- Enable API-key protection with `NETPI_API_KEY`.
- Authenticate protected endpoints with `X-API-Key`.
- Keep health and metrics open for probes.

## Packet Capture

User functions:

- Start a packet capture on an interface.
- Use BPF capture filters with validation.
- Set max packets, max duration, snap length, and promiscuous mode.
- Stop a running capture.
- List capture sessions.
- Get capture session details.
- Download capture files safely.
- Stream decoded packets over WebSocket.
- Block unsafe BPF input and path traversal.

API:

- `POST /api/v1/capture/start`
- `GET /api/v1/capture`
- `GET /api/v1/capture/{session_id}`
- `POST /api/v1/capture/{session_id}/stop`
- `GET /api/v1/capture/{session_id}/download`
- `WS /api/v1/ws/capture/{session_id}`

Needs target validation:

- Live `tcpdump`, `tshark`, and `capinfos` behavior on Linux/Pi.

## Cable Testing

User functions:

- List Ethernet ports that support cable testing.
- Run a cable test on a supported port.
- View cable pair status.
- Store cable test results.
- Retrieve one previous result.
- List historical results by port.

API:

- `GET /api/v1/cabletest/ports`
- `POST /api/v1/cabletest/ports/{port}/test`
- `GET /api/v1/cabletest/results/{result_id}`
- `GET /api/v1/cabletest/ports/{port}/results`

Needs target validation:

- Real `ethtool --cable-test` behavior on Raspberry Pi Ethernet hardware.

## Network Discovery and Topology

User functions:

- Run ARP scan on a CIDR network.
- Run ICMP ping sweep on a CIDR network.
- Store discovered devices as topology nodes.
- View current topology.
- Export topology for web visualization, graph rendering, or data pipelines.

API:

- `POST /api/v1/discovery/arp-scan`
- `POST /api/v1/discovery/ping-sweep`
- `GET /api/v1/discovery/topology`
- `GET /api/v1/discovery/topology/cytoscape`
- `GET /api/v1/discovery/topology/graphviz`
- `GET /api/v1/discovery/topology/jsonl`

Export formats:

- Cytoscape.js JSON
- Graphviz DOT
- NDJSON

## Network Tests

User functions:

- Ping a host.
- Trace route to a host.
- Run iperf3 client tests.
- Run speedtest-cli.
- Use scheduled tests for repeated diagnostics.

API:

- `POST /api/v1/tests/ping`
- `POST /api/v1/tests/traceroute`
- `POST /api/v1/tests/iperf3`
- `POST /api/v1/tests/speedtest`

Needs target validation:

- Network permissions, internet access, and external tools on the target system.

## DMX512

User functions:

- Auto-detect DMX backend.
- View current DMX backend.
- Create DMX universes.
- List DMX universes.
- Get one universe.
- Set one DMX channel.
- Set multiple channels.
- Read one channel.
- Read all 512 channels.
- Start continuous transmission for a universe.
- Stop transmission.
- Send a universe once.
- Start receiving DMX.
- Stop receiving DMX.
- View latest received packet.
- View receive history.
- View active channel levels.
- Analyze packet timing.
- Detect flicker changes.
- Calculate DIP switch settings for addresses 1-512.

API:

- `POST /api/v1/dmx/backend/detect`
- `GET /api/v1/dmx/backend`
- `POST /api/v1/dmx/universes`
- `GET /api/v1/dmx/universes`
- `GET /api/v1/dmx/universes/{uni_id}`
- `POST /api/v1/dmx/universes/{uni_id}/channels/{channel}`
- `GET /api/v1/dmx/universes/{uni_id}/channels/{channel}`
- `POST /api/v1/dmx/universes/{uni_id}/channels`
- `GET /api/v1/dmx/universes/{uni_id}/channels`
- `POST /api/v1/dmx/universes/{uni_id}/transmit/start`
- `POST /api/v1/dmx/universes/{uni_id}/transmit/stop`
- `POST /api/v1/dmx/universes/{uni_id}/transmit/once`
- `POST /api/v1/dmx/receive/start`
- `POST /api/v1/dmx/receive/stop`
- `GET /api/v1/dmx/receive/latest`
- `GET /api/v1/dmx/receive/history`
- `GET /api/v1/dmx/tester/levels`
- `GET /api/v1/dmx/tester/timing`
- `GET /api/v1/dmx/tester/flicker`
- `GET /api/v1/dmx/dip-switch/{address}`
- `WS /api/v1/ws/dmx/universe/{uni_id}`
- `WS /api/v1/ws/dmx/receive`
- `WS /api/v1/ws/dmx/flicker`

Needs target validation:

- USB DMX adapters.
- Raspberry Pi UART DMX output.
- Real DMX receive/timing behavior.

## DMX Fixture Library

User functions:

- List fixture profiles.
- View a fixture profile.
- List supported fixture modes.
- Add a fixture to a universe.
- List fixtures assigned to a universe.

API:

- `GET /api/v1/dmx/fixtures/profiles`
- `GET /api/v1/dmx/fixtures/profiles/{profile_id}`
- `GET /api/v1/dmx/fixtures/profiles/{profile_id}/modes`
- `POST /api/v1/dmx/universes/{uni_id}/fixtures`
- `GET /api/v1/dmx/universes/{uni_id}/fixtures`

## DMX Scenes

User functions:

- Save current universe state as a scene.
- List scenes for a universe.
- Get one scene.
- Delete a scene.
- Recall a scene instantly.
- Recall a scene with a fade.

API:

- `POST /api/v1/dmx/universes/{uni_id}/scenes`
- `GET /api/v1/dmx/universes/{uni_id}/scenes`
- `GET /api/v1/dmx/scenes/{scene_id}`
- `DELETE /api/v1/dmx/scenes/{scene_id}`
- `POST /api/v1/dmx/universes/{uni_id}/scenes/{scene_id}/recall`

Current limitation:

- Scenes are stored in memory; database persistence is planned.

## DMX Cable Test and RDM

User functions:

- Run DMX cable loopback-style test.
- Run RDM discovery through the active backend.

API:

- `POST /api/v1/dmx/cabletest/{port_id}`
- `POST /api/v1/dmx/rdm/discover`

Current limitation:

- Full RDM E1.20 support is planned.
- DMX cable test needs real hardware loopback validation.

## OSC

User functions:

- View OSC listener status.
- Start an OSC UDP listener.
- Stop the OSC UDP listener.
- Send OSC messages to a target host/port.
- Send OSC messages to a target encoded in the URL.
- View recently received OSC messages.
- Clear received OSC history.

API:

- `GET /api/v1/osc/status`
- `POST /api/v1/osc/listen/start`
- `POST /api/v1/osc/listen/stop`
- `POST /api/v1/osc/send`
- `POST /api/v1/osc/send/{host}/{port}`
- `GET /api/v1/osc/messages`
- `DELETE /api/v1/osc/messages`

Supported OSC argument types:

- Integer
- Float
- String
- Boolean
- Null

## OCA/AES70

User functions:

- View OCA/AES70 subsystem status.
- Discover OCA/AES70 devices advertised as `_oca._tcp.local.`.
- Add an OCA/AES70 device manually by host and port.
- List discovered and manually added OCA devices.
- Get one device.
- Delete one device.
- Probe TCP reachability.
- View known AES70 classes recognized by NetPi.
- View expected AES70 object skeleton for a registered device.

API:

- `GET /api/v1/oca/status`
- `POST /api/v1/oca/discover`
- `GET /api/v1/oca/devices`
- `POST /api/v1/oca/devices`
- `GET /api/v1/oca/devices/{device_id}`
- `DELETE /api/v1/oca/devices/{device_id}`
- `POST /api/v1/oca/devices/{device_id}/probe`
- `GET /api/v1/oca/devices/{device_id}/objects`
- `GET /api/v1/oca/classes`

Known AES70 classes currently exposed:

- `OcaRoot`
- `OcaDeviceManager`
- `OcaSecurityManager`
- `OcaFirmwareManager`
- `OcaSubscriptionManager`
- `OcaBlock`
- `OcaGain`
- `OcaMute`
- `OcaSwitch`
- `OcaLevelSensor`

Current limitation:

- Discovery, registry, class inventory, object skeleton, and TCP probe are implemented.
- Full OCP.1 binary method/event control is planned.

## Scheduler

User functions:

- List registered scheduled tests.
- Start one scheduled test loop.
- Stop one scheduled test loop.
- Run a scheduled test once immediately.
- Track last run, last result, and last error.

API:

- `GET /api/v1/scheduler`
- `POST /api/v1/scheduler/{test_id}/start`
- `POST /api/v1/scheduler/{test_id}/stop`
- `POST /api/v1/scheduler/{test_id}/run`

Default schedules:

- `ping_gateway`
- `speedtest`

Current limitation:

- Schedule enabled/disabled state is in memory; persistence is planned.

## Persistence

User functions:

- Store capture sessions.
- Store cable test results.
- Store DMX universes.
- Store DMX fixtures.
- Store topology nodes and edges.
- Run SQLite migrations at startup.

Storage:

- SQLite database under `NETPI_DATA_DIR`.
- Capture files under `NETPI_CAPTURE_DIR`.

## Configuration

Environment variables:

- `NETPI_API_KEY`
- `NETPI_CORS_ORIGINS`
- `NETPI_DATA_DIR`
- `NETPI_CAPTURE_DIR`
- `NETPI_LOG_LEVEL`
- `NETPI_MAX_CAPTURE_SIZE_MB`

## Verified Test Status

Current automated result:

- `79 passed`
- `3 skipped`

Skipped tests:

- Live packet-capture integration tests that require `tcpdump`.

## Features That Still Need Hardware or Target Validation

- Live packet capture with `tcpdump`, `tshark`, and `capinfos`.
- Raspberry Pi interface discovery via `/sys/class/net` and `/proc/net/dev`.
- Real ARP scanning on a target network.
- Real cable testing with `ethtool`.
- USB/UART DMX transmit and receive.
- DMX cable loopback testing.
- RDM discovery on real devices.
- Real OCA/AES70 devices on the network.
- Real speedtest/iperf3/traceroute behavior in the target environment.

