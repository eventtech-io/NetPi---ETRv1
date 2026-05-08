"""Topology export endpoints."""
from fastapi import APIRouter, HTTPException, Response
from fastapi.responses import PlainTextResponse

from netpi_discovery.topology import TopologyBuilder
from netpi_discovery.export import to_cytoscape, to_graphviz, to_jsonl
from netpi_db.database import get_db
from netpi_db.repositories.discovery import TopologyRepository

router = APIRouter(tags=["topology"])


@router.get("/discovery/topology/cytoscape")
async def topology_cytoscape():
    """Export topology as Cytoscape.js JSON."""
    try:
        db = get_db()
        data = await TopologyRepository(db).get_topology()
        from netpi_core.models.discovery import TopologyNode, TopologyEdge
        nodes = [TopologyNode(**n) for n in data["nodes"]]
        edges = [TopologyEdge(**e) for e in data["edges"]]
        return to_cytoscape(nodes, edges)
    except Exception:
        # Fallback to in-memory
        builder = TopologyBuilder()
        return to_cytoscape(list(builder.nodes.values()), builder.edges)


@router.get("/discovery/topology/graphviz")
async def topology_graphviz():
    """Export topology as Graphviz DOT."""
    try:
        db = get_db()
        data = await TopologyRepository(db).get_topology()
        from netpi_core.models.discovery import TopologyNode, TopologyEdge
        nodes = [TopologyNode(**n) for n in data["nodes"]]
        edges = [TopologyEdge(**e) for e in data["edges"]]
        dot = to_graphviz(nodes, edges)
    except Exception:
        builder = TopologyBuilder()
        dot = to_graphviz(list(builder.nodes.values()), builder.edges)

    return PlainTextResponse(content=dot, media_type="text/vnd.graphviz")


@router.get("/discovery/topology/jsonl")
async def topology_jsonl():
    """Export topology as newline-delimited JSON."""
    try:
        db = get_db()
        data = await TopologyRepository(db).get_topology()
        from netpi_core.models.discovery import TopologyNode, TopologyEdge
        nodes = [TopologyNode(**n) for n in data["nodes"]]
        edges = [TopologyEdge(**e) for e in data["edges"]]
        return PlainTextResponse(content=to_jsonl(nodes, edges), media_type="application/x-ndjson")
    except Exception:
        builder = TopologyBuilder()
        return PlainTextResponse(
            content=to_jsonl(list(builder.nodes.values()), builder.edges),
            media_type="application/x-ndjson",
        )



