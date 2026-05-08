"""Async SQLite database manager."""
import json
import logging
from pathlib import Path
from typing import Any

import aiosqlite

from netpi_core.config import get_settings

logger = logging.getLogger("netpi.db")


class Database:
    """Lightweight async SQLite connection manager."""

    def __init__(self, db_path: str | None = None) -> None:
        settings = get_settings()
        self.db_path = db_path or str(Path(settings.data_dir) / "netpi.db")
        self._connection: aiosqlite.Connection | None = None

    async def connect(self) -> aiosqlite.Connection:
        """Open connection and enable WAL mode for better concurrency."""
        if self._connection is not None:
            return self._connection
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        self._connection = await aiosqlite.connect(self.db_path, isolation_level=None)
        self._connection.row_factory = aiosqlite.Row
        await self._connection.execute("PRAGMA journal_mode=WAL")
        await self._connection.execute("PRAGMA foreign_keys=ON")
        logger.info("Database connected: %s", self.db_path)
        return self._connection

    async def close(self) -> None:
        if self._connection:
            await self._connection.close()
            self._connection = None
            logger.info("Database closed")

    async def execute(self, sql: str, parameters: tuple[Any, ...] | None = None) -> aiosqlite.Cursor:
        if self._connection is None:
            raise RuntimeError("Database not connected. Call connect() first.")
        return await self._connection.execute(sql, parameters or ())

    async def executemany(self, sql: str, parameters: list[tuple[Any, ...]]) -> aiosqlite.Cursor:
        if self._connection is None:
            raise RuntimeError("Database not connected")
        return await self._connection.executemany(sql, parameters)

    async def executescript(self, sql: str) -> aiosqlite.Cursor:
        if self._connection is None:
            raise RuntimeError("Database not connected")
        return await self._connection.executescript(sql)

    async def fetchone(self, sql: str, parameters: tuple[Any, ...] | None = None) -> aiosqlite.Row | None:
        cur = await self.execute(sql, parameters)
        return await cur.fetchone()

    async def fetchall(self, sql: str, parameters: tuple[Any, ...] | None = None) -> list[aiosqlite.Row]:
        cur = await self.execute(sql, parameters)
        return await cur.fetchall()


_db: Database | None = None


def get_db(db_path: str | None = None) -> Database:
    global _db
    if _db is None:
        _db = Database(db_path)
    return _db



