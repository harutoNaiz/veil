"""Scroll ruler: compare guard scroll events against ground truth, per gesture."""

from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path

GAP_MS = 150
PASS_MEAN_ERR = 8.0


def _load(path: Path) -> list[dict]:
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            rows.append(json.loads(line))
    return rows


def _gestures(events: list[dict]) -> list[list[dict]]:
    out: list[list[dict]] = []
    for ev in sorted(events, key=lambda e: e["tMs"]):
        if out and ev["tMs"] - out[-1][-1]["tMs"] <= GAP_MS:
            out[-1].append(ev)
        else:
            out.append([ev])
    return out


def _truth_dy(truth: list[dict], t0: int, t1: int) -> float:
    """Content-moved dy of the truth over [t0, t1]."""
    frames = [r for r in truth if r.get("type") == "frame"]
    if frames:
        win = sorted(
            (f for f in frames if t0 - 50 <= f["tMs"] <= t1 + GAP_MS), key=lambda f: f["tMs"]
        )
        if len(win) < 2:
            return 0.0
        return float(-(win[-1]["scrollY"] - win[0]["scrollY"]))
    return float(
        sum(r.get("dy", 0) for r in truth if r.get("type") == "scrolled" and t0 <= r["tMs"] <= t1)
    )


def ruler(guard: list[dict], truth: list[dict]) -> dict[str, dict]:
    scrolls = [e for e in guard if e.get("type") == "scrolled"]
    stats: dict[str, dict] = defaultdict(lambda: {"n": 0, "err": 0.0, "dir_ok": 0})
    for g in _gestures(scrolls):
        gdy = sum(e.get("dy", 0) for e in g)
        tdy = _truth_dy(truth, g[0]["tMs"], g[-1]["tMs"])
        s = stats[g[0].get("packageName") or "?"]
        s["n"] += 1
        s["err"] += abs(gdy - tdy)
        s["dir_ok"] += int(tdy == 0 or (gdy > 0) == (tdy > 0))
    return stats


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--guard", type=Path, required=True)
    ap.add_argument("--truth", type=Path, required=True)
    a = ap.parse_args(argv)
    stats = ruler(_load(a.guard), _load(a.truth))
    print(f"{'app':32} {'n':>4} {'mean_err_px':>12} {'direction%':>11}")
    ok = bool(stats)
    for app, s in sorted(stats.items()):
        mean = s["err"] / s["n"]
        print(f"{app:32} {s['n']:>4} {mean:>12.1f} {100.0 * s['dir_ok'] / s['n']:>11.1f}")
        ok = ok and mean <= PASS_MEAN_ERR and s["dir_ok"] == s["n"]
    print("RULER: PASS" if ok else "RULER: FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
