"""Dev/test split: near-dupe clusters stay whole, strata are (app, primary class), 60/40.

Command line::

    python -m workshop.eval.split --labels L --screens DIR --seed 12 --out splits.json

Prints the split report; exit 1 if a group's dev share is outside 60 +/- 5 points or a cluster
spans both sides, exit 2 on bad input.
"""

from __future__ import annotations

import argparse
import json
import random
import sys
from pathlib import Path

from workshop.eval import dupes
from workshop.eval._common import (
    BadInput,
    app_of,
    is_cats,
    is_clean,
    is_spiders,
    load_labels,
    primary_class,
)

TEST_SHARE = 0.4
DEV_TARGET = 60.0
TOLERANCE = 5.0


def split(labels: list[dict], screens: Path | None, seed: int) -> dict:
    by_name = {lab["image"]: lab for lab in labels}
    names = sorted(by_name)
    if screens is not None:
        groups = dupes.clusters([Path(screens) / n for n in names], dupes.MAX_DIST)
    else:
        groups = [[n] for n in names]
    strata: dict[tuple[str, str], list[list[str]]] = {}
    for g in groups:
        lab = by_name[g[0]]
        strata.setdefault((app_of(lab), primary_class(lab)), []).append(g)
    rng = random.Random(seed)
    test: set[str] = set()
    for key in sorted(strata):
        gs = strata[key]
        size = sum(len(g) for g in gs)
        target = round(TEST_SHARE * size)
        order = list(gs)
        rng.shuffle(order)
        count = 0
        for g in order:
            if count + len(g) <= target:
                test.update(g)
                count += len(g)
    return {
        "seed": seed,
        "hashBits": dupes.HASH_BITS,
        "maxDist": dupes.MAX_DIST,
        "dev": [n for n in names if n not in test],
        "test": [n for n in names if n in test],
        "clusters": [g for g in groups if len(g) > 1],
    }


def report(labels: list[dict], splits: dict) -> dict:
    """Dev share per concept class and per app, plus problems (empty = ok)."""
    dev = set(splits["dev"])
    members: dict[str, list[str]] = {"cats": [], "spiders": [], "clean": []}
    apps: dict[str, list[str]] = {}
    for lab in labels:
        n = lab["image"]
        if is_cats(lab):
            members["cats"].append(n)
        if is_spiders(lab):
            members["spiders"].append(n)
        if is_clean(lab):
            members["clean"].append(n)
        apps.setdefault(app_of(lab), []).append(n)
    problems: list[str] = []

    def share(kind: str, groups: dict[str, list[str]]) -> dict:
        res = {}
        for name, ns in sorted(groups.items()):
            if not ns:
                continue
            pct = 100.0 * sum(1 for n in ns if n in dev) / len(ns)
            res[name] = {"n": len(ns), "devShare": round(pct, 1)}
            if abs(pct - DEV_TARGET) > TOLERANCE + 1e-9:
                problems.append(f"{kind} {name}: dev share {pct:.1f} outside 60 +/- 5")
        return res

    classes = share("class", members)
    by_app = share("app", apps)
    test = set(splits["test"])
    for g in splits.get("clusters", []):
        if any(n in dev for n in g) and any(n in test for n in g):
            problems.append(f"cluster spans dev and test: {g}")
    return {"classes": classes, "apps": by_app, "problems": problems}


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="python -m workshop.eval.split")
    p.add_argument("--labels", required=True)
    p.add_argument("--screens", required=True)
    p.add_argument("--seed", type=int, default=12)
    p.add_argument("--out", required=True)
    args = p.parse_args(argv)
    try:
        labels = load_labels(args.labels)
        for lab in labels:
            if not (Path(args.screens) / lab["image"]).is_file():
                raise BadInput(f"no screenshot for label {lab['image']}")
        result = split(labels, Path(args.screens), args.seed)
    except BadInput as exc:
        print(f"bad input: {exc}", file=sys.stderr)
        return 2
    Path(args.out).write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    rep = report(labels, result)
    print(
        f"SPLIT seed={args.seed}: dev={len(result['dev'])} test={len(result['test'])} "
        f"near-dupe clusters={len(result['clusters'])}"
    )
    for kind in ("classes", "apps"):
        for name, row in rep[kind].items():
            print(
                f"  {kind[:-2] if kind == 'classes' else 'app'} {name}: n={row['n']} "
                f"dev={row['devShare']}%"
            )
    for prob in rep["problems"]:
        print(f"PROBLEM: {prob}")
    print("SPLIT FAIL" if rep["problems"] else "SPLIT OK")
    return 1 if rep["problems"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
