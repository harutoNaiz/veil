"""Near-duplicate check: dHash (256 bits) clusters, and a check that no pair straddles dev/test.

Command line::

    python -m workshop.eval.dupes --screens DIR --splits splits.json
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import numpy as np
from PIL import Image

from workshop.eval._common import BadInput, load_json

MAX_DIST = 20
HASH_BITS = 256


def dhash(path: Path, hash_size: int = 16) -> int:
    """Grayscale, resize to (hash_size+1) x hash_size, one bit per adjacent column pair."""
    with Image.open(path) as im:
        small = im.convert("L").resize((hash_size + 1, hash_size), Image.Resampling.BOX)
    px = np.asarray(small, dtype=np.int16)
    bits = 0
    for flag in (px[:, :-1] > px[:, 1:]).ravel():
        bits = (bits << 1) | int(flag)
    return bits


def clusters(paths: list[Path], max_dist: int = MAX_DIST) -> list[list[str]]:
    """Group images whose hashes are within max_dist bits (transitively). Includes singletons."""
    names = [Path(p).name for p in paths]
    hashes = [dhash(Path(p)) for p in paths]
    parent = list(range(len(names)))

    def find(i: int) -> int:
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i

    for i in range(len(names)):
        for j in range(i + 1, len(names)):
            if (hashes[i] ^ hashes[j]).bit_count() <= max_dist:
                parent[find(i)] = find(j)
    groups: dict[int, list[str]] = {}
    for i, n in enumerate(names):
        groups.setdefault(find(i), []).append(n)
    return sorted(sorted(g) for g in groups.values())


def straddling(cl: list[list[str]], dev: set[str], test: set[str]) -> list[list[str]]:
    return [g for g in cl if any(n in dev for n in g) and any(n in test for n in g)]


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="python -m workshop.eval.dupes")
    p.add_argument("--screens", required=True)
    p.add_argument("--splits", required=True)
    args = p.parse_args(argv)
    try:
        splits = load_json(args.splits)
        dev, test = set(splits["dev"]), set(splits["test"])  # type: ignore[index]
        max_dist = int(splits.get("maxDist", MAX_DIST))  # type: ignore[union-attr]
        paths = [Path(args.screens) / n for n in sorted(dev | test)]
        missing = [str(x) for x in paths if not x.is_file()]
        if missing:
            raise BadInput(f"missing screenshots: {missing[:3]}")
        cl = clusters(paths, max_dist)
    except (BadInput, KeyError, TypeError) as exc:
        print(f"bad input: {exc}", file=sys.stderr)
        return 2
    bad = straddling(cl, dev, test)
    dupes = [g for g in cl if len(g) > 1]
    for g in bad:
        print(f"STRADDLES dev/test: {g}")
    print(f"DUPES {'FAIL' if bad else 'OK'}: {len(paths)} images, {len(dupes)} near-dupe clusters")
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main())
