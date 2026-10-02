"""Fake predictions for proving the scorer: perfect, empty and mistakes.

Command line::

    python -m workshop.eval.fake_preds perfect|empty|mistakes --labels L [--seed N] --out preds.json
"""

from __future__ import annotations

import argparse
import json
import random
import sys
from pathlib import Path

from workshop.eval._common import BadInput, load_labels


def _finding(n: int, image: str, concept: str, rect: dict, scope: str) -> dict:
    return {
        "contractVersion": "1.0",
        "findingId": f"f-{n}",
        "lookId": 0,
        "tMs": 0,
        "image": image,
        "rect": dict(rect),
        "conceptId": concept,
        "layer": 2,
        "lane": "finder",
        "decision": "hide",
        "probability": 1.0,
        "scope": scope,
    }


def make(kind: str, labels: list[dict], seed: int = 1) -> list[dict]:
    if kind == "empty":
        return []
    boxes = [(lab["image"], b) for lab in labels for b in lab["boxes"]]
    if kind == "mistakes":
        rng = random.Random(seed)
        cat_idx = [i for i, (_, b) in enumerate(boxes) if b["concept"] == "cats"]
        if len(cat_idx) < 3:
            raise BadInput("mistakes needs at least 3 cat boxes")
        drop = set(rng.sample(cat_idx, 2))
        boxes = [x for i, x in enumerate(boxes) if i not in drop]
        clean = [lab for lab in labels if lab.get("clean") is True]
        with_dog = [lab["image"] for lab in clean if "dog" in lab.get("lookalikes", [])]
        plain = [lab["image"] for lab in clean if not lab.get("lookalikes")]
        if not with_dog or not plain:
            raise BadInput("mistakes needs a clean image with a dog and one without lookalikes")
    out = [_finding(i, im, b["concept"], b["rect"], b["scope"]) for i, (im, b) in enumerate(boxes)]
    if kind == "mistakes":
        extra = {"x": 0, "y": 0, "w": 50, "h": 50}
        out.append(_finding(len(out), rng.choice(with_dog), "cats", extra, "object"))
        out.append(_finding(len(out), rng.choice(plain), "cats", extra, "object"))
    return out


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="python -m workshop.eval.fake_preds")
    p.add_argument("kind", choices=["perfect", "empty", "mistakes"])
    p.add_argument("--labels", required=True)
    p.add_argument("--seed", type=int, default=1)
    p.add_argument("--out", required=True)
    args = p.parse_args(argv)
    try:
        preds = make(args.kind, load_labels(args.labels), args.seed)
    except BadInput as exc:
        print(f"bad input: {exc}", file=sys.stderr)
        return 2
    Path(args.out).write_text(json.dumps(preds, indent=2) + "\n", encoding="utf-8")
    print(f"wrote {len(preds)} findings ({args.kind}) to {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
