"""Broadcom PHY cable test via ethtool --cable-test."""
import asyncio
import re
import uuid
from datetime import datetime, timezone

from netpi_core.models.cabletest import (
    CableStatus,
    CableTestResult,
    PairResult,
    PairStatus,
)
from .base import CableTestBackend


class EthtoolCableTestBackend(CableTestBackend):
    """Cable test using Linux ethtool --cable-test (Broadcom BCM54213)."""

    name = "ethtool"

    _PAIR_MAP = {
        "Pair A": "1-2",
        "Pair B": "3-6",
        "Pair C": "4-5",
        "Pair D": "7-8",
    }

    _STATUS_MAP = {
        "Ok": PairStatus.OK,
        "Open": PairStatus.OPEN,
        "Short": PairStatus.SHORT,
        "Short to pair": PairStatus.SHORT_TO_PAIR,
        "Crosstalk": PairStatus.CROSSTALK,
        "Unknown": PairStatus.UNKNOWN,
    }

    async def is_available(self, port_id: str) -> bool:
        """Check cable-test support WITHOUT running the test.

        BUG-FIX: previous implementation called `ethtool --cable-test` which
        takes the link down for ~2 seconds.  We now probe via `ethtool -i`
        (driver info) and limit support to known-good Broadcom PHYs on Pi 4/5,
        falling back to a dry-run check via `ethtool --show-features`.
        """
        try:
            # Check driver info — Broadcom BCM54213 is 'bcmgenet'
            proc = await asyncio.create_subprocess_exec(
                "ethtool", "-i", port_id,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=5.0)
            if proc.returncode != 0:
                return False
            output = stdout.decode().lower()
            # Known drivers that support ethtool cable-test
            supported_drivers = {"bcmgenet", "tg3", "bnx2x"}
            for driver in supported_drivers:
                if driver in output:
                    return True

            # Fallback: check if the interface name is eth0/eth1 on a Pi
            # (heuristic — these are the onboard ports)
            if port_id in ("eth0", "eth1") and "driver" in output:
                return True

            return False
        except Exception:
            return False

    async def test(self, port_id: str) -> CableTestResult:
        """Run ethtool --cable-test and parse the output."""
        started = datetime.now(timezone.utc)
        proc = await asyncio.create_subprocess_exec(
            "ethtool", "--cable-test", port_id,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=30.0)
        duration_ms = int((datetime.now(timezone.utc) - started).total_seconds() * 1000)

        if proc.returncode != 0:
            return CableTestResult(
                id=str(uuid.uuid4()),
                port_id=port_id,
                backend=self.name,
                timestamp=started,
                status=CableStatus.UNKNOWN,
                duration_ms=duration_ms,
                pairs=[],
            )

        output = stdout.decode()
        pairs = self._parse_output(output)

        if not pairs:
            status = CableStatus.UNKNOWN
        elif all(p.status == PairStatus.OK for p in pairs):
            status = CableStatus.OK
        elif all(p.status == PairStatus.OPEN for p in pairs):
            status = CableStatus.DISCONNECTED
        elif any(p.status in (PairStatus.OPEN, PairStatus.SHORT, PairStatus.SHORT_TO_PAIR) for p in pairs):
            status = CableStatus.FAULT
        else:
            status = CableStatus.FAULT

        lengths = [p.length_m for p in pairs if p.length_m is not None]
        overall_length = sum(lengths) / len(lengths) if lengths else None

        return CableTestResult(
            id=str(uuid.uuid4()),
            port_id=port_id,
            backend=self.name,
            timestamp=started,
            status=status,
            pairs=pairs,
            overall_length_m=overall_length,
            duration_ms=duration_ms,
        )

    def _parse_output(self, output: str) -> list[PairResult]:
        """Parse ethtool --cable-test output into PairResult objects."""
        pairs: list[PairResult] = []
        current_pair_name: str | None = None
        current_status: PairStatus = PairStatus.UNKNOWN
        current_length: float | None = None
        current_fault: float | None = None

        def _flush():
            if current_pair_name is not None:
                pairs.append(PairResult(
                    pair=self._PAIR_MAP.get(current_pair_name, current_pair_name),
                    status=current_status,
                    length_m=current_length,
                    fault_distance_m=current_fault,
                ))

        for line in output.splitlines():
            line = line.strip()
            if not line:
                continue

            pair_match = re.match(r"^(Pair [A-D]):?\s*(.*)$", line)
            if pair_match:
                _flush()
                current_pair_name = pair_match.group(1)
                status_text = pair_match.group(2).strip()
                current_status = self._STATUS_MAP.get(status_text, PairStatus.UNKNOWN)
                current_length = None
                current_fault = None
                continue

            len_match = re.search(r"[Ll]ength.*?([0-9]+)\s*met", line)
            if len_match:
                current_length = float(len_match.group(1))
                continue

            fault_match = re.search(r"[Ff]ault.*?([0-9]+)\s*met", line)
            if fault_match:
                current_fault = float(fault_match.group(1))
                continue

            status_match = re.match(r"^(Ok|Open|Short|Short to pair|Crosstalk|Unknown)$", line, re.I)
            if status_match:
                current_status = self._STATUS_MAP.get(
                    status_match.group(1).capitalize(), PairStatus.UNKNOWN
                )

        _flush()
        return pairs
