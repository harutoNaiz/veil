"""Choose the fastest precision within max_drop points of float."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from workshop.forge.cloud import score_adapter

HERE = Path(__file__).parent
BITS = {"float16": 16, "w8a16": 12, "w8a8": 8}


def choose(float_score: float, cands: list[dict], max_drop: float = 2.0) -> str:
    ok = [c for c in cands if float_score - c["score"] <= max_drop + 1e-9]
    if not ok:
        return "float16"
    best = min(ok, key=lambda c: (c["latencyMs"], -BITS.get(c["precision"], 0)))
    return best["precision"]


def build(profile: dict, scores: dict, max_drop: float = 2.0) -> dict:
    by_model: dict[str, list[dict]] = {}
    for e in profile["models"]:
        by_model.setdefault(e["modelId"], []).append(e)
    rows = []
    for mid, entries in by_model.items():
        if mid not in scores:
            continue
        s = scores[mid]
        fl = next((e for e in entries if e["precision"] == "float16"), entries[0])
        cands = [
            {
                "precision": e["precision"],
                "score": s[e["precision"]],
                "latencyMs": e["latencyMs"],
                "inferenceJob": e.get("inferenceJob"),
            }
            for e in entries
            if e["precision"] in s
        ]
        chosen = choose(s["float"], cands, max_drop)
        cs = next((c["score"] for c in cands if c["precision"] == chosen), s["float"])
        rows.append(
            {
                "modelId": mid,
                "float": {"score": s["float"], "latencyMs": fl["latencyMs"]},
                "candidates": cands,
                "chosen": chosen,
                "delta": round(s["float"] - cs, 4),
            }
        )
    return {"models": rows}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    g = ap.add_mutually_exclusive_group()
    g.add_argument("--live", action="store_true")
    g.add_argument("--fixture", action="store_true")
    ap.add_argument("--out", default=str(HERE / "out"))
    a = ap.parse_args(argv)
    if a.live:
        raise SystemExit("live precision run needs an AI Hub token (HC-003)")
    out = Path(a.out)
    prof_path = out / "profile.json"
    if not prof_path.exists():
        prof_path = HERE / "fixtures" / "2" / "profile.json"
    profile = json.loads(prof_path.read_text(encoding="utf-8"))
    res = {"source": "fixture", **build(profile, score_adapter.fixture_scores())}
    out.mkdir(parents=True, exist_ok=True)
    (out / "precision.json").write_text(json.dumps(res, indent=1), encoding="utf-8")
    print(f"wrote {out / 'precision.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
