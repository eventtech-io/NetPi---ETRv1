"""DMX universe and fixture persistence."""
import json
import logging
from datetime import datetime

from netpi_core.models.dmx import DMXUniverse, DMXFixture, DMXFixtureChannel
from netpi_db.database import Database

logger = logging.getLogger("netpi.db.dmx")


class DMXUniverseRepository:
    def __init__(self, db: Database) -> None:
        self.db = db

    async def save(self, universe: DMXUniverse) -> None:
        await self.db.execute(
            """
            INSERT INTO dmx_universes (id, name, channels_json, is_transmitting, tx_rate_hz, last_updated)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                name=excluded.name,
                channels_json=excluded.channels_json,
                is_transmitting=excluded.is_transmitting,
                tx_rate_hz=excluded.tx_rate_hz,
                last_updated=excluded.last_updated
            """,
            (
                universe.id,
                universe.name,
                json.dumps(universe.channels),
                int(universe.is_transmitting),
                universe.tx_rate_hz,
                universe.last_updated.isoformat() if universe.last_updated else None,
            ),
        )

    async def get(self, universe_id: str) -> DMXUniverse | None:
        row = await self.db.fetchone(
            "SELECT * FROM dmx_universes WHERE id = ?", (universe_id,)
        )
        if not row:
            return None
        return self._row_to_universe(row)

    async def list_all(self) -> list[DMXUniverse]:
        rows = await self.db.fetchall("SELECT * FROM dmx_universes ORDER BY name")
        return [self._row_to_universe(r) for r in rows]

    async def delete(self, universe_id: str) -> None:
        await self.db.execute("DELETE FROM dmx_universes WHERE id = ?", (universe_id,))

    def _row_to_universe(self, row) -> DMXUniverse:
        return DMXUniverse(
            id=row["id"],
            name=row["name"],
            channels=json.loads(row["channels_json"]),
            is_transmitting=bool(row["is_transmitting"]),
            tx_rate_hz=row["tx_rate_hz"],
            last_updated=datetime.fromisoformat(row["last_updated"]) if row["last_updated"] else None,
        )


class DMXFixtureRepository:
    def __init__(self, db: Database) -> None:
        self.db = db

    async def save(self, fixture: DMXFixture, universe_id: str | None = None) -> None:
        channels = [ch.model_dump() for ch in fixture.channels]
        await self.db.execute(
            """
            INSERT INTO dmx_fixtures (
                id, universe_id, name, manufacturer, model, mode,
                start_address, channel_count, channels_json, is_rdm, rdm_uid
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                universe_id=excluded.universe_id,
                name=excluded.name,
                manufacturer=excluded.manufacturer,
                model=excluded.model,
                mode=excluded.mode,
                start_address=excluded.start_address,
                channel_count=excluded.channel_count,
                channels_json=excluded.channels_json,
                is_rdm=excluded.is_rdm,
                rdm_uid=excluded.rdm_uid
            """,
            (
                fixture.id,
                universe_id,
                fixture.name,
                fixture.manufacturer,
                fixture.model,
                fixture.mode,
                fixture.start_address,
                fixture.channel_count,
                json.dumps(channels),
                int(fixture.is_rdm),
                fixture.rdm_uid,
            ),
        )

    async def list_by_universe(self, universe_id: str) -> list[DMXFixture]:
        rows = await self.db.fetchall(
            "SELECT * FROM dmx_fixtures WHERE universe_id = ?", (universe_id,)
        )
        return [self._row_to_fixture(r) for r in rows]

    async def delete(self, fixture_id: str) -> None:
        await self.db.execute("DELETE FROM dmx_fixtures WHERE id = ?", (fixture_id,))

    def _row_to_fixture(self, row) -> DMXFixture:
        channels = [
            DMXFixtureChannel(**ch) for ch in json.loads(row["channels_json"])
        ]
        return DMXFixture(
            id=row["id"],
            name=row["name"],
            manufacturer=row["manufacturer"],
            model=row["model"],
            mode=row["mode"],
            start_address=row["start_address"],
            channel_count=row["channel_count"],
            channels=channels,
            is_rdm=bool(row["is_rdm"]),
            rdm_uid=row["rdm_uid"],
        )



