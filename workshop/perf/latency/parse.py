"""Time-to-cover from Guard debug.jsonl + Test Feed feedlog.jsonl.

python -m workshop.perf.latency.parse --debug D --feed F --out evidence/latency.json
"""

from __future__ import annotations

import argparse
import math
import statistics
from pathlib import Path

from workshop.perf.schema import STAGES, Row, Section, jsonl

FIX_MENU = "fix menu: smaller look area, batching, cache, model size"


def appearances(feed: list[dict], targets: tuple[str, ...] = ("cat", "spider")):
    """(itemId, firstSeenTMs, rect) for each tracked item's first visible frame."""
    seen: dict[str, tuple[str, int, list[int]]] = {}
    for fr in feed:
        if fr.get("type") != "frame":
            continue
        for it in fr.get("visible", []):
            iid = str(it.get("itemId", ""))
            if iid not in seen and iid.startswith(tuple(targets)):
                seen[iid] = (iid, int(fr["tMs"]), list(it["rect"]))
    return sorted(seen.values(), key=lambda a: a[1])


def _covered(rect: list[int], masks: list[dict]) -> float:
    left, top, right, bottom = rect
    area = max(right - left, 0) * max(bottom - top, 0)
    if area == 0:
        return 0.0
    best = 0.0
    for m in masks:
        ml, mt, mr, mb = m["rect"]
        w, h = min(right, mr) - max(left, ml), min(bottom, mb) - max(top, mt)
        if w > 0 and h > 0:
            best = max(best, w * h / area)
    return best


def time_to_cover(apps, debug: list[dict], cover_pct: float = 80) -> list[dict]:
    plans = sorted((d for d in debug if d.get("kind") == "plan"), key=lambda d: d["tMs"])
    draws = {
        d["lookId"]: d["tMs"]
        for d in debug
        if d.get("kind") == "stage" and d.get("stage") == "draw"
    }
    out = []
    for iid, appear, rect in apps:
        cover = None
        for p in plans:
            if p["tMs"] >= appear and _covered(rect, p.get("masks", [])) * 100 >= cover_pct:
                cover = max(draws.get(p.get("lookId"), p["tMs"]), p["tMs"])
                break
        lat = None if cover is None else cover - appear
        out.append({"itemId": iid, "appearMs": appear, "coverMs": cover, "latencyMs": lat})
    return out


def _pct(vals: list[float], q: float) -> float:
    s = sorted(vals)
    return s[max(math.ceil(q * len(s)) - 1, 0)]


def stage_breakdown(debug: list[dict]) -> dict[str, dict[str, float]]:
    by_look: dict[int, dict[str, int]] = {}
    for d in debug:
        if d.get("kind") == "stage" and d.get("stage") in STAGES:
            by_look.setdefault(d["lookId"], {})[d["stage"]] = d["tMs"]
    deltas: dict[str, list[float]] = {}
    for st in by_look.values():
        seq = [(s, st[s]) for s in STAGES if s in st]
        for (_, a), (name, b) in zip(seq, seq[1:], strict=False):
            deltas.setdefault(name, []).append(b - a)
    return {
        n: {"p50": _pct(v, 0.5), "p95": _pct(v, 0.95), "mean": statistics.fmean(v)}
        for n, v in deltas.items()
    }


def slowest_stage(breakdown: dict[str, dict[str, float]]) -> str:
    if not breakdown:
        return "none"
    return max(breakdown, key=lambda k: breakdown[k]["p95"])


def p95_ms(lat: list[dict]) -> float:
    vals = [math.inf if x["latencyMs"] is None else x["latencyMs"] for x in lat]
    return _pct(vals, 0.95) if vals else math.inf


def build_section(lat: list[dict], breakdown: dict, mode: str = "balanced") -> Section:
    n, p95 = len(lat), p95_ms(lat)
    ok = n >= 100 and p95 <= 300
    sec = Section("latency")
    sec.rows.append(
        Row(
            "AC-5.3-01",
            "p95_ms",
            "inf" if math.isinf(p95) else p95,
            "p95 ≤ 0.3 s across 100 appearances, Balanced",
            ok,
        )
    )
    sec.notes.append(f"mode={mode} n={n} slowest_stage={slowest_stage(breakdown)}; {FIX_MENU}")
    if n < 100:
        sec.notes.append(f"only {n} appearances, need 100")
    return sec.finish()


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="workshop.perf.latency.parse")
    ap.add_argument("--debug", required=True, type=Path)
    ap.add_argument("--feed", required=True, type=Path)
    ap.add_argument("--out", required=True, type=Path)
    ap.add_argument("--targets", default="cat,spider")
    ap.add_argument("--mode", default="balanced")
    a = ap.parse_args(argv)
    debug = jsonl(a.debug)
    apps = appearances(jsonl(a.feed), tuple(a.targets.split(",")))
    lat = time_to_cover(apps, debug)
    bd = stage_breakdown(debug)
    sec = build_section(lat, bd, a.mode)
    a.out.parent.mkdir(parents=True, exist_ok=True)
    sec.write(a.out)
    print(f"P95 {sec.rows[0].value:g} n={len(lat)} slowest={slowest_stage(bd)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
