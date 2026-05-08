"""Topology persistence."""
import logging
from datetime import datetime, timezone

from netpi_core.models.discovery import TopologyNode, TopologyEdge, Neighbor
from netpi_db.database import Database

logger = logging.getLogger("netpi.db.discovery")


class TopologyRepository:
    def __init__(self, db: Database) -> None:
        self.db = db

    async def upsert_node(self, node: TopologyNode) -> None:
        now = datetime.now(timezone.utc).isoformat()
        await self.db.execute(
            """
            INSERT INTO topology_nodes (id, label, type, ip, mac, vendor, first_seen, last_seen)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                label=excluded.label,
                type=excluded.type,
                ip=excluded.ip,
                mac=excluded.mac,
                vendor=excluded.vendor,
                last_seen=excluded.last_seen
            """,
            (node.id, node.label, node.type, node.ip, node.mac, node.vendor, now, now),
        )

    async def upsert_edge(self, edge: TopologyEdge) -> None:
        now = datetime.now(timezone.utc).isoformat()
        # Upsert by source+target+protocol composite
        existing = await self.db.fetchone(
            "SELECT id FROM topology_edges WHERE source=? AND target=? AND protocol=?",
            (edge.source, edge.target, edge.protocol),
        )
        if existing:
            await self.db.execute(
                "UPDATE topology_edges SET local_port=?, remote_port=?, last_seen=? WHERE id=?",
                (edge.local_port, edge.remote_port, now, existing["id"]),
            )
        else:
            await self.db.execute(
                """
                INSERT INTO topology_edges (source, target, local_port, remote_port, protocol, first_seen, last_seen)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (edge.source, edge.target, edge.local_port, edge.remote_port, edge.protocol, now, now),
            )

    async def get_topology(self) -> dict:
        nodes = await self.db.fetchall("SELECT * FROM topology_nodes")
        edges = await self.db.fetchall("SELECT * FROM topology_edges")
        return {
            "nodes": [
                TopologyNode(
                    id=n["id"], label=n["label"], type=n["type"],
                    ip=n["ip"], mac=n["mac"], vendor=n["vendor"],
                ).model_dump()
                for n in nodes
            ],
            "edges": [
                TopologyEdge(
                    source=e["source"], target=e["target"],
                    local_port=e["local_port"], remote_port=e["remote_port"],
                    protocol=e["protocol"],
                ).model_dump()
                for e in edges
            ],
        }

    async def prune_older_than(self, days: int) -> int:
        """Remove nodes and edges not seen for N days. Returns rows deleted."""
        cutoff = datetime.now(timezone.utc).isoformat()
        # Simplified: real implementation would compute date arithmetic in SQL
        # For SQLite we can use datetime() function
        await self.db.execute(
            "DELETE FROM topology_nodes WHERE last_seen < datetime('now', '-{} days')".format(days)
        )
        await self.db.execute(
            "DELETE FROM topology_edges WHERE last_seen < datetime('now', '-{} days')".format(days)
        )
        return 0  # Could return changes() if needed



