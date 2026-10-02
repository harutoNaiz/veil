"""Check that logged scroll events line up with visible movement (<= 33 ms)."""

from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

import numpy as np

from workshop.recordings.estimate import estimate_scroll


def _bursts(events: list[dict], gap_ms: int = 100) -> list[int]:
    starts, last = [], None
    for e in events:
        if e["type"] != "scrolled":
            continue
        if last is None or e["tMs"] - last > gap_ms:
            starts.append(e["tMs"])
        last = e["tMs"]
    return starts


def check(session_json: Path, samples: int = 10) -> dict:
    session_json = Path(session_json)
    s = json.loads(session_json.read_text(encoding="utf-8"))
    folder = session_json.parent
    stem = session_json.name[: -len(".session.json")]
    text = (folder / f"{stem}.events.jsonl").read_text(encoding="utf-8")
    logged = [json.loads(x) for x in text.splitlines() if x]
    est = estimate_scroll(
        folder / s["video"], s["screenWidth"], s["packageName"], fps=s["fps"], t0_ms=s["t0Ms"]
    )
    lb, eb = _bursts(logged), _bursts(est)
    pick = []
    if lb:
        pick = sorted({int(round(v)) for v in np.linspace(0, len(lb) - 1, min(samples, len(lb)))})
    rows = []
    for k in pick:
        near = min(eb, key=lambda t: abs(t - lb[k]), default=None)
        off = None if near is None else lb[k] - near
        rows.append({"burst": k, "loggedMs": lb[k], "onsetMs": near, "offsetMs": off})
    with open(folder / f"{stem}.sync.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, ["burst", "loggedMs", "onsetMs", "offsetMs"])
        w.writeheader()
        w.writerows(rows)
    offs = [abs(r["offsetMs"]) for r in rows if r["offsetMs"] is not None]
    mx = max(offs) if offs else None
    ok = bool(rows) and len(offs) == len(rows) and mx <= 33
    return {"sessionId": s["sessionId"], "pass": ok, "maxOffsetMs": mx, "bursts": len(rows)}


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="python -m workshop.recordings.sync_check")
    p.add_argument("session", type=Path)
    p.add_argument("--samples", type=int, default=10)
    a = p.parse_args(argv)
    r = check(a.session, a.samples)
    print(f"SYNC {r['sessionId']}: {'PASS' if r['pass'] else 'FAIL'} max={r['maxOffsetMs']}")
    return 0 if r["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
