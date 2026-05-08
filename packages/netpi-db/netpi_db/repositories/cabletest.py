"""Cable test result persistence."""
import json
import logging

from netpi_core.models.cabletest import CableTestResult, PairResult
from netpi_db.database import Database

logger = logging.getLogger("netpi.db.cabletest")


class CableTestRepository:
    def __init__(self, db: Database) -> None:
        self.db = db

    async def save(self, result: CableTestResult) -> None:
        pairs = [p.model_dump() for p in result.pairs]
        await self.db.execute(
            """
            INSERT INTO cable_test_results (
                id, port_id, backend, timestamp, status,
                pairs_json, overall_length_m, duration_ms
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                result.id,
                result.port_id,
                result.backend,
                result.timestamp.isoformat(),
                result.status,
                json.dumps(pairs),
                result.overall_length_m,
                result.duration_ms,
            ),
        )

    async def get(self, result_id: str) -> CableTestResult | None:
        row = await self.db.fetchone(
            "SELECT * FROM cable_test_results WHERE id = ?", (result_id,)
        )
        if not row:
            return None
        return self._row_to_result(row)

    async def list_by_port(self, port_id: str, limit: int = 50) -> list[CableTestResult]:
        rows = await self.db.fetchall(
            "SELECT * FROM cable_test_results WHERE port_id = ? ORDER BY timestamp DESC LIMIT ?",
            (port_id, limit),
        )
        return [self._row_to_result(r) for r in rows]

    def _row_to_result(self, row) -> CableTestResult:
        from datetime import datetime
        pairs = [PairResult(**p) for p in json.loads(row["pairs_json"])]
        return CableTestResult(
            id=row["id"],
            port_id=row["port_id"],
            backend=row["backend"],
            timestamp=datetime.fromisoformat(row["timestamp"]),
            status=row["status"],
            pairs=pairs,
            overall_length_m=row["overall_length_m"],
            duration_ms=row["duration_ms"],
        )



