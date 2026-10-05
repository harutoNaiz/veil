"""Pull a Veil Guard UiEvent log.

Usage: python -m workshop.signals.pull_log --name s [--boottime] --out data/signals
"""

from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path

REMOTE = "files/signals"


def shift_boottime(lines: list[str], clock: dict) -> list[str]:
    """Shift tMs from uptime to boottime (adds elapsedRealtime - uptime from the clock sidecar)."""
    off = int(clock["elapsedRealtimeMs"]) - int(clock["uptimeMs"])
    out = []
    for line in lines:
        if not line.strip():
            continue
        d = json.loads(line)
        d["tMs"] = int(d["tMs"]) + off
        out.append(json.dumps(d, separators=(",", ":")))
    return out


def _cat(name: str, suffix: str) -> bytes:
    cmd = ["adb", "exec-out", "run-as", "com.veil.guard", "cat", f"{REMOTE}/{name}.{suffix}"]
    return subprocess.run(cmd, check=True, capture_output=True).stdout


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="python -m workshop.signals.pull_log")
    p.add_argument("--name", required=True)
    p.add_argument("--boottime", action="store_true")
    p.add_argument("--out", default="data/signals")
    a = p.parse_args(argv)
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    events = _cat(a.name, "events.jsonl").decode("utf-8").splitlines()
    clock_raw = _cat(a.name, "clock.json")
    (out / f"{a.name}.clock.json").write_bytes(clock_raw)
    if a.boottime:
        events = shift_boottime(events, json.loads(clock_raw))
    (out / f"{a.name}.events.jsonl").write_text(
        "\n".join(events) + ("\n" if events else ""), encoding="utf-8"
    )
    print(f"pulled {len(events)} events -> {out / (a.name + '.events.jsonl')}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
