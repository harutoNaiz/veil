"""Check the capture logs pulled from the phone (Phase 4.1 "Watch the watcher").

Input directory: frames.jsonl (frame.schema.json objects), state.jsonl (CaptureLog
transitions + heartbeats), optional meminfo.jsonl ({"tMs","pssKb"}) and markers.jsonl
({"tMs","event"}; events idleStart, idleEnd, lock, kill).
Output: JSON report with metrics and AC verdicts (PASS / FAIL / NA). Exit 1 on any FAIL.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path

from workshop.contracts import validate

NETFLIX = "com.netflix.mediaclient"


def read_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    rows = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            rows.append(json.loads(line))
    return rows


def _verdict(ok: bool | None) -> str:
    return "NA" if ok is None else ("PASS" if ok else "FAIL")


def analyse(directory: Path) -> dict:
    frames = read_jsonl(directory / "frames.jsonl")
    states = read_jsonl(directory / "state.jsonl")
    mem = read_jsonl(directory / "meminfo.jsonl")
    markers = read_jsonl(directory / "markers.jsonl")
    m: dict = {"frames": len(frames)}

    bad = 0
    for f in frames:
        try:
            validate.validate("Frame", f)
        except Exception:
            bad += 1
    m["schema_errors"] = bad

    starts = [x["tMs"] for x in markers if x["event"] == "idleStart"]
    ends = [x["tMs"] for x in markers if x["event"] == "idleEnd"]
    m["idle_fps"] = None
    if starts and ends and ends[0] > starts[0]:
        n = sum(1 for f in frames if starts[0] <= f["tMs"] < ends[0])
        m["idle_fps"] = n / ((ends[0] - starts[0]) / 1000.0)

    sizes: dict[str, list[int]] = {}
    for f in frames:
        sizes.setdefault(str(f["rotation"]), [f["width"], f["height"]])
    m["sizes_by_rotation"] = sizes

    def size_ok(rot: str, wh: list[int]) -> bool:
        w, h = wh
        short, long_ = min(w, h), max(w, h)
        portrait = rot in ("0", "180")
        return short == 360 and (h >= w) == portrait and long_ >= 360

    m["sizes_ok"] = bool(sizes) and all(size_ok(r, wh) for r, wh in sizes.items())

    awaiting = [s["tMs"] for s in states if s.get("state") == "awaitingPermission"]
    latencies = []
    for x in markers:
        if x["event"] in ("lock", "kill"):
            after = [t for t in awaiting if t >= x["tMs"]]
            latencies.append(min(after) - x["tMs"] if after else None)
    m["stop_to_awaiting_ms"] = latencies
    m["resume_count"] = sum(
        1
        for prev, cur in zip(states, states[1:], strict=False)
        if prev.get("state") == "awaitingPermission" and cur.get("state") == "running"
    )
    m["max_outstanding"] = max((s.get("outstanding", 0) for s in states), default=0)

    m["memory_growth_pct"] = None
    if len(mem) >= 2 and mem[0]["pssKb"] > 0:
        m["memory_growth_pct"] = (mem[-1]["pssKb"] - mem[0]["pssKb"]) * 100.0 / mem[0]["pssKb"]

    blind: dict[str, int] = defaultdict(int)
    netflix_full = None
    for f in frames:
        pkg = f.get("foregroundPackage", "unknown")
        if f.get("blindRects"):
            blind[pkg] += 1
        if pkg == NETFLIX:
            netflix_full = bool(netflix_full) or any(
                r["w"] >= 0.95 * f["screenWidth"] and r["h"] >= 0.95 * f["screenHeight"]
                for r in f.get("blindRects", [])
            )
    m["blind_frames_per_package"] = dict(blind)
    m["netflix_full_blind"] = netflix_full

    verdicts = {
        "schema": _verdict(bad == 0 and bool(frames)),
        "AC-4.1-01": _verdict(m["sizes_ok"] if frames else None),
        "AC-4.1-02": _verdict(None if m["idle_fps"] is None else m["idle_fps"] <= 1.0),
        "AC-4.1-03": _verdict(
            None
            if m["memory_growth_pct"] is None
            else (m["memory_growth_pct"] <= 5.0 and m["max_outstanding"] <= 1)
        ),
        "AC-4.1-04": _verdict(
            None if not latencies else all(v is not None and v <= 1000 for v in latencies)
        ),
        "outstanding": _verdict(m["max_outstanding"] <= 1 if states else None),
        "blind-netflix": _verdict(netflix_full),
    }
    return {"metrics": m, "verdicts": verdicts, "pass": "FAIL" not in verdicts.values()}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("directory", type=Path)
    ap.add_argument("--out", type=Path, default=None, help="write the JSON report here too")
    args = ap.parse_args(argv)
    report = analyse(args.directory)
    text = json.dumps(report, indent=2)
    print(text)
    if args.out:
        args.out.write_text(text, encoding="utf-8")
    return 0 if report["pass"] else 1


if __name__ == "__main__":
    sys.exit(main())
