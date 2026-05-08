from netpi_core.models.discovery import TopologyNode, TopologyEdge, Neighbor

class TopologyBuilder:
    def __init__(self) -> None:
        self.nodes: dict[str, TopologyNode] = {}
        self.edges: list[TopologyEdge] = []

    def add_local_device(self, device_id: str, label: str, ip: str | None = None) -> None:
        self.nodes[device_id] = TopologyNode(id=device_id, label=label, type="server", ip=ip)

    def add_neighbor(self, local_id: str, neighbor: Neighbor) -> None:
        remote_id = neighbor.device_id or neighbor.ip_address or neighbor.port_id or "unknown"
        if remote_id not in self.nodes:
            self.nodes[remote_id] = TopologyNode(
                id=remote_id, label=neighbor.device_id or remote_id,
                type="switch" if "switch" in neighbor.capabilities else "unknown",
                ip=neighbor.ip_address,
            )
        self.edges.append(TopologyEdge(
            source=local_id, target=remote_id,
            local_port=neighbor.local_interface,
            remote_port=neighbor.port_id, protocol=neighbor.protocol,
        ))

    def add_scan_result(self, local_id: str, ip: str, mac: str | None = None) -> None:
        if ip not in self.nodes:
            self.nodes[ip] = TopologyNode(id=ip, label=ip, type="host", ip=ip, mac=mac)
        self.edges.append(TopologyEdge(source=local_id, target=ip, protocol="ARP"))

    def to_dict(self):
        return {"nodes": [n.model_dump() for n in self.nodes.values()],
                "edges": [e.model_dump() for e in self.edges]}
