"""Topology export formats."""
import json
from datetime import datetime, timezone

from netpi_core.models.discovery import TopologyNode, TopologyEdge


def to_cytoscape(nodes: list[TopologyNode], edges: list[TopologyEdge]) -> dict:
    """Export topology to Cytoscape.js JSON format."""
    return {
        "elements": {
            "nodes": [
                {
                    "data": {
                        "id": n.id,
                        "label": n.label,
                        "type": n.type,
                        "ip": n.ip,
                        "mac": n.mac,
                        "vendor": n.vendor,
                    }
                }
                for n in nodes
            ],
            "edges": [
                {
                    "data": {
                        "id": f"{e.source}_{e.target}",
                        "source": e.source,
                        "target": e.target,
                        "local_port": e.local_port,
                        "remote_port": e.remote_port,
                        "protocol": e.protocol,
                    }
                }
                for e in edges
            ],
        },
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }


def to_graphviz(nodes: list[TopologyNode], edges: list[TopologyEdge]) -> str:
    """Export topology to Graphviz DOT format."""
    lines = [
        "// NetPi Topology Export",
        f"// Generated: {datetime.now(timezone.utc).isoformat()}",
        "digraph netpi {",
        '    rankdir=LR;',
        '    node [shape=box, style="rounded,filled", fillcolor="#e8e8e8"];',
    ]

    type_colors = {
        "server": "#4a90d9",
        "switch": "#7ed957",
        "host": "#f5a623",
        "unknown": "#d9d9d9",
    }

    for n in nodes:
        color = type_colors.get(n.type, "#d9d9d9")
        label = n.label or n.id
        if n.ip:
            label += f"\n{n.ip}"
        lines.append(f'    "{n.id}" [label="{label}", fillcolor="{color}"];')

    for e in edges:
        label = e.protocol or ""
        if e.local_port and e.remote_port:
            label += f"\n{e.local_port} -> {e.remote_port}"
        lines.append(f'    "{e.source}" -> "{e.target}" [label="{label}"];')

    lines.append("}")
    return "\n".join(lines)


def to_jsonl(nodes: list[TopologyNode], edges: list[TopologyEdge]) -> str:
    """Export as newline-delimited JSON (one node/edge per line)."""
    lines = []
    for n in nodes:
        lines.append(json.dumps({"type": "node", **n.model_dump()}))
    for e in edges:
        lines.append(json.dumps({"type": "edge", **e.model_dump()}))
    return "\n".join(lines)



