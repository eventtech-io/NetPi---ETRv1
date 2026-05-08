"""Capture session persistence."""
import json
import logging
from datetime import datetime

from netpi_core.models.capture import CaptureSession, CaptureFilter, CaptureStatus
from netpi_db.database import Database

logger = logging.getLogger("netpi.db.capture")


class CaptureSessionRepository:
    def __init__(self, db: Database) -> None:
        self.db = db

    async def save(self, session: CaptureSession) -> None:
        filter_cfg = session.filter
        await self.db.execute(
            """
            INSERT INTO capture_sessions (
                id, interface, bpf_expression, promiscuous, snaplen,
                max_packets, max_duration_sec, status, started_at, stopped_at,
                packet_count, byte_count, file_path, format, error_message
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                status=excluded.status,
                stopped_at=excluded.stopped_at,
                packet_count=excluded.packet_count,
                byte_count=excluded.byte_count,
                error_message=excluded.error_message
            """,
            (
                session.id,
                session.interface,
                filter_cfg.bpf_expression,
                int(filter_cfg.promiscuous),
                filter_cfg.snaplen,
                filter_cfg.max_packets,
                filter_cfg.max_duration_sec,
                session.status,
                session.started_at.isoformat() if session.started_at else None,
                session.stopped_at.isoformat() if session.stopped_at else None,
                session.packet_count,
                session.byte_count,
                session.file_path,
                session.format,
                session.error_message,
            ),
        )
        logger.debug("Capture session %s persisted", session.id)

    async def get(self, session_id: str) -> CaptureSession | None:
        row = await self.db.fetchone(
            "SELECT * FROM capture_sessions WHERE id = ?", (session_id,)
        )
        if not row:
            return None
        return self._row_to_session(row)

    async def list_recent(self, limit: int = 100) -> list[CaptureSession]:
        rows = await self.db.fetchall(
            "SELECT * FROM capture_sessions ORDER BY started_at DESC LIMIT ?",
            (limit,),
        )
        return [self._row_to_session(r) for r in rows]

    def _row_to_session(self, row) -> CaptureSession:
        filter_cfg = CaptureFilter(
            interface=row["interface"],
            bpf_expression=row["bpf_expression"],
            promiscuous=bool(row["promiscuous"]),
            snaplen=row["snaplen"],
            max_packets=row["max_packets"],
            max_duration_sec=row["max_duration_sec"],
        )
        return CaptureSession(
            id=row["id"],
            interface=row["interface"],
            filter=filter_cfg,
            status=CaptureStatus(row["status"]),
            started_at=datetime.fromisoformat(row["started_at"]),
            stopped_at=datetime.fromisoformat(row["stopped_at"]) if row["stopped_at"] else None,
            packet_count=row["packet_count"],
            byte_count=row["byte_count"],
            file_path=row["file_path"],
            format=row["format"],
            error_message=row["error_message"],
        )



