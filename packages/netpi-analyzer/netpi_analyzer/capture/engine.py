"""Async packet capture engine using tcpdump."""
import asyncio
import logging
import os
import re
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import AsyncIterator

from netpi_core.config import get_settings
from netpi_core.models.capture import CaptureFilter, CaptureSession, CaptureStatus, PacketSummary

logger = logging.getLogger("netpi.capture.engine")


class CaptureEngine:
    """Async capture engine that wraps tcpdump for high-throughput capture."""

    def __init__(self, data_dir: str = "/var/lib/netpi/captures") -> None:
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self._sessions: dict[str, CaptureSession] = {}
        self._processes: dict[str, asyncio.subprocess.Process] = {}
        self._db_repo = None

    def set_repository(self, repo) -> None:
        """Attach a CaptureSessionRepository for persistence."""
        self._db_repo = repo

    async def start(self, filter_cfg: CaptureFilter) -> CaptureSession:
        """Start a new capture session."""
        session_id = str(uuid.uuid4())
        file_path = self.data_dir / f"{session_id}.pcapng"

        session = CaptureSession(
            id=session_id,
            interface=filter_cfg.interface,
            filter=filter_cfg,
            status=CaptureStatus.RUNNING,
            started_at=datetime.now(timezone.utc),
            file_path=str(file_path),
            format="pcapng",
        )
        self._sessions[session_id] = session

        if self._db_repo:
            try:
                await self._db_repo.save(session)
            except Exception:
                logger.exception("Failed to persist capture start")

        cmd = [
            "tcpdump",
            "-i", filter_cfg.interface,
            "-U",
            "-w", str(file_path),
            "-s", str(filter_cfg.snaplen),
        ]
        if not filter_cfg.promiscuous:
            cmd.append("-p")
        if filter_cfg.max_packets:
            cmd.extend(["-c", str(filter_cfg.max_packets)])
        if filter_cfg.bpf_expression:
            cmd.append(filter_cfg.bpf_expression)

        logger.info("Starting capture %s: %s", session_id, " ".join(cmd))

        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.PIPE,
        )
        self._processes[session_id] = proc

        asyncio.create_task(self._monitor_stderr(session_id, proc))

        if filter_cfg.max_duration_sec:
            asyncio.create_task(self._auto_stop(session_id, filter_cfg.max_duration_sec))

        return session

    async def _monitor_stderr(self, session_id: str, proc: asyncio.subprocess.Process) -> None:
        """Monitor tcpdump stderr for errors, accumulating all messages."""
        if proc.stderr is None:
            return
        errors: list[str] = []
        async for line in proc.stderr:
            text = line.decode().strip()
            if text:
                errors.append(text)
        if errors and session_id in self._sessions:
            self._sessions[session_id].error_message = "; ".join(errors)
            if proc.returncode not in (0, None):
                self._sessions[session_id].status = CaptureStatus.ERROR
                logger.error("Capture %s failed: %s", session_id, errors)
            else:
                logger.warning("Capture %s stderr: %s", session_id, errors)

    async def _auto_stop(self, session_id: str, delay_sec: int) -> None:
        await asyncio.sleep(delay_sec)
        await self.stop(session_id)

    async def stop(self, session_id: str) -> CaptureSession | None:
        """Stop a running capture session."""
        session = self._sessions.get(session_id)
        if not session:
            return None

        proc = self._processes.pop(session_id, None)
        if proc and proc.returncode is None:
            proc.terminate()
            try:
                await asyncio.wait_for(proc.wait(), timeout=5.0)
            except asyncio.TimeoutError:
                proc.kill()
                await proc.wait()

        session.status = CaptureStatus.STOPPED
        session.stopped_at = datetime.now(timezone.utc)

        if session.file_path and os.path.exists(session.file_path):
            session.byte_count = os.path.getsize(session.file_path)
            try:
                proc2 = await asyncio.create_subprocess_exec(
                    "capinfos", "-c", session.file_path,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )
                stdout, _ = await asyncio.wait_for(proc2.communicate(), timeout=5.0)
                m = re.search(r"Number of packets =\s*(\d+)", stdout.decode())
                if m:
                    session.packet_count = int(m.group(1))
            except Exception:
                logger.warning("Failed to parse packet count for %s", session_id)

        if self._db_repo:
            try:
                await self._db_repo.save(session)
            except Exception:
                logger.exception("Failed to persist capture stop")

        logger.info("Capture %s stopped: %s bytes", session_id, session.byte_count or 0)
        return session

    def get_session(self, session_id: str) -> CaptureSession | None:
        return self._sessions.get(session_id)

    def list_sessions(self) -> list[CaptureSession]:
        return list(self._sessions.values())

    async def stream_packets(self, session_id: str) -> AsyncIterator[PacketSummary]:
        """Stream decoded packets from a capture file using tshark."""
        session = self._sessions.get(session_id)
        if not session or not session.file_path:
            return

        for _ in range(50):
            if os.path.exists(session.file_path) and os.path.getsize(session.file_path) > 24:
                break
            await asyncio.sleep(0.1)

        cmd = [
            "tshark",
            "-r", session.file_path,
            "-T", "fields",
            "-e", "frame.time_epoch",
            "-e", "frame.len",
            "-e", "eth.src",
            "-e", "eth.dst",
            "-e", "eth.type",
            "-e", "ip.src",
            "-e", "ip.dst",
            "-e", "ipv6.src",
            "-e", "ipv6.dst",
            "-e", "tcp.srcport",
            "-e", "tcp.dstport",
            "-e", "udp.srcport",
            "-e", "udp.dstport",
            "-E", "header=n",
            "-E", "separator=\t",
        ]

        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

        if proc.stdout is None:
            return

        async for line in proc.stdout:
            parts = line.decode().strip().split("\t")
            if len(parts) < 2:
                continue

            def _int(s: str) -> int | None:
                return int(s) if s else None

            yield PacketSummary(
                timestamp=float(parts[0]) if parts[0] else 0.0,
                length=int(parts[1]) if parts[1] else 0,
                src_mac=parts[2] or None,
                dst_mac=parts[3] or None,
                ethertype=parts[4] or None,
                src_ip=parts[5] or (parts[7] if len(parts) > 7 else None) or None,
                dst_ip=parts[6] or (parts[8] if len(parts) > 8 else None) or None,
                src_port=_int(parts[9]) if len(parts) > 9 else (
                    _int(parts[11]) if len(parts) > 11 else None
                ),
                dst_port=_int(parts[10]) if len(parts) > 10 else (
                    _int(parts[12]) if len(parts) > 12 else None
                ),
            )

        await proc.wait()


_engine: CaptureEngine | None = None


def get_engine(data_dir: str | None = None) -> CaptureEngine:
    global _engine
    if _engine is None:
        _engine = CaptureEngine(data_dir or get_settings().capture_dir)
    return _engine



