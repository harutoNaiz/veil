"""Score cover predictions against screen labels (frozen metric definitions, SPEC 3.3).

Command line::

    python -m workshop.eval.score_screens --labels L --preds P [--splits S --split dev|test]
        [--ignore-tag T]... [--out score.json]
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from jsonschema.exceptions import ValidationError

from workshop.contracts.validate import validate
from workshop.eval._common import BadInput, load_json, load_labels


def _inter(a: dict, b: dict) -> int:
    w = min(a["x"] + a["w"], b["x"] + b["w"]) - max(a["x"], b["x"])
    h = min(a["y"] + a["h"], b["y"] + b["h"]) - max(a["y"], b["y"])
    return max(0, w) * max(0, h)


def iou(a: dict, b: dict) -> float:
    inter = _inter(a, b)
    union = a["w"] * a["h"] + b["w"] * b["h"] - inter
    return inter / union if union > 0 else 0.0


def contains_frac(cover: dict, label: dict) -> float:
    """Share of the label's area that lies inside the cover."""
    return _inter(cover, label) / (label["w"] * label["h"])


def hits(cover: dict, label: dict) -> bool:
    return iou(cover, label) >= 0.3 or contains_frac(cover, label) >= 0.7


def _ratio(num: int, den: int) -> float | None:
    return num / den if den else None


def score(
    labels: list[dict], findings: list[dict], ignore_tags: frozenset[str] = frozenset()
) -> dict:
    images = {lab["image"]: lab for lab in labels}
    covers: list[dict] = []
    dropped = 0
    for f in findings:
        if not f.get("image"):
            raise ValueError("finding without image")
        if f["decision"] == "hide" and f["image"] in images:
            covers.append(f)
        else:
            dropped += 1

    clean_names = {n for n, lab in images.items() if lab.get("clean") is True}
    # Counted labels and ignored ones (they leave the denominators), as (image, concept, rect).
    real: list[tuple[str, str, dict]] = []
    ignored: list[tuple[str, str, dict]] = []
    for n, lab in images.items():
        for b in lab["boxes"]:
            (ignored if b.get("tag") in ignore_tags else real).append((n, b["concept"], b["rect"]))

    names = {c for _, c, _ in real} | {c for _, c, _ in ignored} | {f["conceptId"] for f in covers}
    out: dict = {}
    for c in sorted(names):
        c_labels = [(n, r) for n, cc, r in real if cc == c]
        c_ignored = [(n, r) for n, cc, r in ignored if cc == c]
        c_covers = [f for f in covers if f["conceptId"] == c]
        hit = sum(
            1 for n, r in c_labels if any(f["image"] == n and hits(f["rect"], r) for f in c_covers)
        )
        kept = correct = 0
        for f in c_covers:
            if any(n == f["image"] and hits(f["rect"], r) for n, r in c_labels):
                kept += 1
                correct += 1
            elif any(n == f["image"] and hits(f["rect"], r) for n, r in c_ignored):
                continue  # hits only ignored labels: leaves the precision denominator
            else:
                kept += 1
        false_clean = {f["image"] for f in c_covers if f["image"] in clean_names}
        out[c] = {
            "labels": len(c_labels),
            "hit": hit,
            "covers": kept,
            "correctCovers": correct,
            "recall": _ratio(hit, len(c_labels)),
            "precision": _ratio(correct, kept),
            "cleanFalseCover": len(false_clean) / len(clean_names) if clean_names else 0.0,
        }
    any_clean = {f["image"] for f in covers if f["image"] in clean_names}
    return {
        "images": len(images),
        "cleanImages": len(clean_names),
        "cleanFalseCover": len(any_clean) / len(clean_names) if clean_names else 0.0,
        "droppedPredictions": dropped,
        "concepts": out,
    }


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="python -m workshop.eval.score_screens")
    p.add_argument("--labels", required=True)
    p.add_argument("--preds", required=True)
    p.add_argument("--splits")
    p.add_argument("--split", choices=["dev", "test"])
    p.add_argument("--ignore-tag", action="append", default=[])
    p.add_argument("--out")
    args = p.parse_args(argv)
    try:
        labels = load_labels(args.labels)
        if args.split:
            if not args.splits:
                raise BadInput("--split needs --splits")
            names = set(load_json(args.splits)[args.split])  # type: ignore[index]
            labels = [lab for lab in labels if lab["image"] in names]
        preds = load_json(args.preds)
        if not isinstance(preds, list):
            raise BadInput(f"{args.preds} is not a JSON array of Finding objects")
        for i, f in enumerate(preds):
            try:
                validate("Finding", f)
            except ValidationError as exc:
                raise BadInput(f"finding {i} invalid: {exc.message}") from exc
            if not f.get("image"):
                raise BadInput(f"finding {i} has no image")
        result = score(labels, preds, frozenset(args.ignore_tag))
    except (BadInput, KeyError, TypeError) as exc:
        print(f"bad input: {exc}", file=sys.stderr)
        return 2
    text = json.dumps(result, indent=2)
    if args.out:
        Path(args.out).write_text(text + "\n", encoding="utf-8")
    print(text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
