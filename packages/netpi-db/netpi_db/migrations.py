"""Lightweight async migration runner."""
import logging
from dataclasses import dataclass
from datetime import datetime, timezone

from .database import Database

logger = logging.getLogger("netpi.db.migrations")


@dataclass
class Migration:
    version: int
    name: str
    sql: str


MIGRATIONS: list[Migration] = [
    Migration(
        version=1,
        name="create_capture_sessions",
        sql="""
        CREATE TABLE IF NOT EXISTS capture_sessions (
            id TEXT PRIMARY KEY,
            interface TEXT NOT NULL,
            bpf_expression TEXT,
            promiscuous INTEGER NOT NULL DEFAULT 1,
            snaplen INTEGER NOT NULL DEFAULT 65535,
            max_packets INTEGER,
            max_duration_sec INTEGER,
            status TEXT NOT NULL,
            started_at TEXT NOT NULL,
            stopped_at TEXT,
            packet_count INTEGER NOT NULL DEFAULT 0,
            byte_count INTEGER NOT NULL DEFAULT 0,
            file_path TEXT,
            format TEXT NOT NULL DEFAULT 'pcapng',
            error_message TEXT
        );
        CREATE INDEX IF NOT EXISTS idx_capture_started ON capture_sessions(started_at);
        """,
    ),
    Migration(
        version=2,
        name="create_dmx_universes",
        sql="""
        CREATE TABLE IF NOT EXISTS dmx_universes (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            channels_json TEXT NOT NULL,
            is_transmitting INTEGER NOT NULL DEFAULT 0,
            tx_rate_hz REAL NOT NULL DEFAULT 44.0,
            last_updated TEXT
        );
        """,
    ),
    Migration(
        version=3,
        name="create_dmx_fixtures",
        sql="""
        CREATE TABLE IF NOT EXISTS dmx_fixtures (
            id TEXT PRIMARY KEY,
            universe_id TEXT,
            name TEXT NOT NULL,
            manufacturer TEXT,
            model TEXT,
            mode TEXT,
            start_address INTEGER NOT NULL,
            channel_count INTEGER NOT NULL,
            channels_json TEXT NOT NULL,
            is_rdm INTEGER NOT NULL DEFAULT 0,
            rdm_uid TEXT,
            FOREIGN KEY (universe_id) REFERENCES dmx_universes(id) ON DELETE SET NULL
        );
        CREATE INDEX IF NOT EXISTS idx_fixture_universe ON dmx_fixtures(universe_id);
        """,
    ),
    Migration(
        version=4,
        name="create_topology",
        sql="""
        CREATE TABLE IF NOT EXISTS topology_nodes (
            id TEXT PRIMARY KEY,
            label TEXT NOT NULL,
            type TEXT NOT NULL,
            ip TEXT,
            mac TEXT,
            vendor TEXT,
            first_seen TEXT NOT NULL,
            last_seen TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS topology_edges (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            source TEXT NOT NULL,
            target TEXT NOT NULL,
            local_port TEXT,
            remote_port TEXT,
            protocol TEXT,
            first_seen TEXT NOT NULL,
            last_seen TEXT NOT NULL
        );
        CREATE INDEX IF NOT EXISTS idx_edge_source ON topology_edges(source);
        CREATE INDEX IF NOT EXISTS idx_edge_target ON topology_edges(target);
        """,
    ),
    Migration(
        version=5,
        name="create_cable_test_results",
        sql="""
        CREATE TABLE IF NOT EXISTS cable_test_results (
            id TEXT PRIMARY KEY,
            port_id TEXT NOT NULL,
            backend TEXT NOT NULL,
            timestamp TEXT NOT NULL,
            status TEXT NOT NULL,
            pairs_json TEXT NOT NULL,
            overall_length_m REAL,
            duration_ms INTEGER NOT NULL DEFAULT 0
        );
        CREATE INDEX IF NOT EXISTS idx_cable_port ON cable_test_results(port_id);
        CREATE INDEX IF NOT EXISTS idx_cable_time ON cable_test_results(timestamp);
        """,
    ),
]


class MigrationManager:
    def __init__(self, db: Database) -> None:
        self.db = db

    async def initialize(self) -> None:
        """Ensure migration tracking table exists."""
        await self.db.execute("""
            CREATE TABLE IF NOT EXISTS _migrations (
                version INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                applied_at TEXT NOT NULL
            )
        """)

    async def applied_versions(self) -> set[int]:
        rows = await self.db.fetchall("SELECT version FROM _migrations")
        return {r["version"] for r in rows}

    async def apply_all(self) -> None:
        await self.initialize()
        applied = await self.applied_versions()
        for mig in MIGRATIONS:
            if mig.version in applied:
                continue
            logger.info("Applying migration %d: %s", mig.version, mig.name)
            await self.db.executescript(mig.sql)
            await self.db.execute(
                "INSERT INTO _migrations (version, name, applied_at) VALUES (?, ?, ?)",
                (mig.version, mig.name, datetime.now(timezone.utc).isoformat()),
            )
            logger.info("Migration %d applied", mig.version)



