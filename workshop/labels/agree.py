"""Second-labeller agreement (AC-1.2-03).

Command line::

    python -m workshop.labels.agree sample --labels L --fraction 0.2 --seed N --out names.txt
    python -m workshop.labels.agree compare --official L --blind B [--out report.json]

``compare`` exits 0 if coverage >= 0.20 and disagreement rate <= 0.05, else 1; 2 on bad input.
"""

from __future__ import annotations

import argparse
import json
import math
import random
import sys
from pathlib import Path


def iou(a: dict, b: dict) -> float:
    ix = max(0, min(a["x"] + a["w"], b["x"] + b["w"]) - max(a["x"], b["x"]))
    iy = max(0, min(a["y"] + a["h"], b["y"] + b["h"]) - max(a["y"], b["y"]))
    inter = ix * iy
    union = a["w"] * a["h"] + b["w"] * b["h"] - inter
    return inter / union if union else 0.0


def sample(names: list[str], fraction: float, seed: int) -> list[str]:
    """ceil(fraction * n) names chosen with the seed, sorted."""
    k = min(len(names), math.ceil(round(fraction * len(names), 9)))
    return sorted(random.Random(seed).sample(sorted(names), k))


def _pair(official: list[dict], blind: list[dict]) -> tuple[list[float], int, int]:
    """Greedy one-to-one pairing by highest IoU (> 0): (pair IoUs, unmatched official/blind)."""
    cands = sorted(
        (
            (iou(o["rect"], b["rect"]), i, j)
            for i, o in enumerate(official)
            for j, b in enumerate(blind)
        ),
        key=lambda t: (-t[0], t[1], t[2]),
    )
    used_o: set[int] = set()
    used_b: set[int] = set()
    ious = []
    for value, i, j in cands:
        if value <= 0:
            break
        if i in used_o or j in used_b:
            continue
        used_o.add(i)
        used_b.add(j)
        ious.append(value)
    return ious, len(official) - len(used_o), len(blind) - len(used_b)


def compare(official: list[dict], blind: list[dict]) -> dict:
    """Agreement report over the images present in both label lists."""
    off = {e["image"]: e for e in official}
    bli = {e["image"]: e for e in blind}
    common = sorted(set(off) & set(bli))
    items = disagreements = 0
    for name in common:
        concepts = {b["concept"] for e in (off[name], bli[name]) for b in e["boxes"]}
        for concept in sorted(concepts):
            o = [b for b in off[name]["boxes"] if b["concept"] == concept]
            b = [x for x in bli[name]["boxes"] if x["concept"] == concept]
            ious, miss_o, miss_b = _pair(o, b)
            items += len(ious) + miss_o + miss_b
            disagreements += sum(1 for v in ious if v < 0.5) + miss_o + miss_b
    rate = disagreements / max(items, 1)
    coverage = len(common) / len(off) if off else 0.0
    return {
        "images": len(common),
        "coverage": coverage,
        "items": items,
        "disagreements": disagreements,
        "rate": rate,
        "pass": coverage >= 0.20 and rate <= 0.05,
    }


def _load(path: Path) -> list[dict]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, list):
        raise ValueError(f"{path}: not a JSON array")
    return data


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="python -m workshop.labels.agree")
    sub = p.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("sample")
    s.add_argument("--labels", type=Path, required=True)
    s.add_argument("--fraction", type=float, required=True)
    s.add_argument("--seed", type=int, required=True)
    s.add_argument("--out", type=Path, required=True)
    c = sub.add_parser("compare")
    c.add_argument("--official", type=Path, required=True)
    c.add_argument("--blind", type=Path, required=True)
    c.add_argument("--out", type=Path)
    args = p.parse_args(argv)
    try:
        if args.cmd == "sample":
            names = sample([e["image"] for e in _load(args.labels)], args.fraction, args.seed)
            args.out.parent.mkdir(parents=True, exist_ok=True)
            args.out.write_text("".join(n + "\n" for n in names), encoding="utf-8")
            print(f"sampled {len(names)} names to {args.out}")
            return 0
        report = compare(_load(args.official), _load(args.blind))
    except (OSError, ValueError, KeyError) as exc:
        print(f"bad input: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(report, indent=2))
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    return 0 if report["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
