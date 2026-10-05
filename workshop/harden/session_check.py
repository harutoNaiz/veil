"""Check a logcat dump (and optional cover-event JSONL) from a free-use or heat session."""

import argparse
import json
import re
import sys
from pathlib import Path

_PROC = re.compile(r"Process:\s*([^,\s]+)")


def count_crashes(lines: list[str], package: str) -> int:
    n = 0
    for i, line in enumerate(lines):
        if "FATAL EXCEPTION" not in line:
            continue
        for nxt in lines[i + 1 : i + 6]:
            m = _PROC.search(nxt)
            if m:
                if m.group(1).startswith(package):
                    n += 1
                break
    return n


def count_anrs(lines: list[str], package: str) -> int:
    return sum(1 for ln in lines if "ANR in " + package in ln)


def stuck_covers(events: list[dict], window_ms: int = 2000) -> int:
    """A show is stuck if no hide comes within window_ms after the next appSwitch or
    screenOff, or if it is still open at the end of the log."""
    events = sorted(events, key=lambda e: e["tMs"])
    shows: dict[str, int] = {}
    stuck = 0
    for e in events:
        if e["op"] == "show":
            shows[e["id"]] = e["tMs"]
        elif e["op"] == "hide":
            t0 = shows.pop(e["id"], None)
            if t0 is None:
                continue
            sw = [x["tMs"] for x in events if x["op"] in ("appSwitch", "screenOff")]
            sw = [s for s in sw if t0 <= s <= e["tMs"]]
            if sw and e["tMs"] - sw[0] > window_ms:
                stuck += 1
    return stuck + len(shows)


def check(logcat: Path, covers: Path | None, package: str) -> dict:
    lines = logcat.read_text(encoding="utf-8", errors="replace").splitlines()
    events = []
    if covers:
        text = covers.read_text(encoding="utf-8")
        events = [json.loads(x) for x in text.splitlines() if x.strip()]
    r = {
        "crashes": count_crashes(lines, package),
        "anrs": count_anrs(lines, package),
        "stuckCovers": stuck_covers(events),
    }
    r["verdict"] = "PASS" if not (r["crashes"] or r["anrs"] or r["stuckCovers"]) else "FAIL"
    return r


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--logcat", required=True, type=Path)
    ap.add_argument("--covers", type=Path)
    ap.add_argument("--package", default="com.veil")
    ap.add_argument("--out", type=Path)
    a = ap.parse_args(argv)
    r = check(a.logcat, a.covers, a.package)
    if a.out:
        a.out.write_text(json.dumps(r), encoding="utf-8")
    print(json.dumps(r))
    return 0 if r["verdict"] == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
