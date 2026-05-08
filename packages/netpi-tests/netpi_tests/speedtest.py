import asyncio, json
async def run_speedtest():
    proc = await asyncio.create_subprocess_exec("speedtest-cli", "--json",
        stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
    stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=120)
    if proc.returncode != 0:
        return {"error": stderr.decode().strip() or "speedtest failed"}
    data = json.loads(stdout.decode())
    return {"server": {"name": data["server"]["name"], "location": data["server"]["country"],
                        "host": data["server"]["host"], "latency_ms": data["server"]["latency"]},
            "download_mbps": data["download"] / 1e6,
            "upload_mbps": data["upload"] / 1e6,
            "ping_ms": data["ping"], "timestamp": data["timestamp"]}
