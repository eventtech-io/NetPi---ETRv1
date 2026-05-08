"""BPF filter builder helpers."""

def build_bpf(
    hosts: list[str] | None = None,
    ports: list[int] | None = None,
    protocols: list[str] | None = None,
    exclude_hosts: list[str] | None = None,
) -> str:
    parts: list[str] = []
    if hosts:
        parts.append("(" + " or ".join(f"host {h}" for h in hosts) + ")")
    if ports:
        parts.append("(" + " or ".join(f"port {p}" for p in ports) + ")")
    if protocols:
        parts.append("(" + " or ".join(protocols) + ")")
    expr = " and ".join(parts) if parts else ""
    if exclude_hosts:
        excl = " and ".join(f"not host {h}" for h in exclude_hosts)
        expr = f"({expr}) and ({excl})" if expr else excl
    return expr
