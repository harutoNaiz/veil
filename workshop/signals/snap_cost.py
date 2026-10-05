"""Parse VEIL_SNAP lines from logcat: p50/p95/max ms and max nodes."""

from __future__ import annotations

import argparse
import re
import statistics
import subprocess
import sys
from collections.abc import Iterable

_RE = re.compile(r"VEIL_SNAP ms=(\d+) nodes=(\d+) truncated=(true|false)")


def parse(lines: Iterable[str]) -> list[tuple[int, int, bool]]:
    return [(int(m[1]), int(m[2]), m[3] == "true") for m in map(_RE.search, lines) if m]


def pct(vals: list[int], p: float) -> float:
    s = sorted(vals)
    return float(s[min(len(s) - 1, int(p * len(s)))])


def report(rows: list[tuple[int, int, bool]]) -> tuple[str, bool]:
    if not rows:
        return "SNAP: FAIL (no VEIL_SNAP lines)", False
    ms = [r[0] for r in rows]
    nodes = [r[1] for r in rows]
    p95 = pct(ms, 0.95)
    ok = p95 <= 40 and max(nodes) <= 300
    text = (
        f"n={len(rows)} p50={statistics.median(ms):.0f} p95={p95:.0f} max={max(ms)} "
        f"maxNodes={max(nodes)}\nSNAP: {'PASS' if ok else 'FAIL'}"
    )
    return text, ok


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--file", help="logcat text file; default: adb logcat -d")
    a = ap.parse_args(argv)
    if a.file:
        with open(a.file, encoding="utf-8") as f:
            lines = f.read().splitlines()
    else:
        lines = subprocess.run(
            ["adb", "logcat", "-d", "-s", "VeilSnap"], capture_output=True, text=True, check=False
        ).stdout.splitlines()
    text, ok = report(parse(lines))
    print(text)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
