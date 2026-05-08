import asyncio, json
async def iperf3_client(host: str, port: int = 5201, duration: int = 10,
                         reverse: bool = False, udp: bool = False,
                         bandwidth: str | None = None):
    cmd = ["iperf3", "-c", host, "-p", str(port), "-t", str(duration), "-J"]
    if reverse: cmd.append("-R")
    if udp: cmd.append("-u")
    if bandwidth: cmd.extend(["-b", bandwidth])
    proc = await asyncio.create_subprocess_exec(*cmd,
        stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
    stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=duration + 15)
    if proc.returncode != 0:
        return {"error": stderr.decode().strip() or "iperf3 failed"}
    data = json.loads(stdout.decode())
    summary = data.get("end", {})
    ss = summary.get("sum_sent", {}); sr = summary.get("sum_received", {})
    return {"host": host, "port": port, "duration_sec": duration,
            "protocol": "udp" if udp else "tcp",
            "sent_mbps": ss.get("bits_per_second", 0) / 1e6,
            "received_mbps": sr.get("bits_per_second", 0) / 1e6,
            "retransmits": ss.get("retransmits", 0)}
