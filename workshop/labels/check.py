"""Check a labels file against a screens folder (AC-1.2-02).

Command line::

    python -m workshop.labels.check --labels L --screens DIR

Prints ``LABELS OK <n>`` (exit 0) or one line per problem (exit 1); exit 2 on unreadable input.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path

from jsonschema.exceptions import ValidationError
from PIL import Image

from workshop.contracts.validate import validate


def check(labels: list[dict], screens: Path) -> list[str]:
    """Problems found (empty = ok)."""
    problems: list[str] = []
    pngs = {p.name for p in screens.glob("*.png")}
    counts = Counter(entry.get("image") for entry in labels)
    for name in sorted(pngs - set(counts)):
        problems.append(f"{name}: no label entry")
    for name, n in sorted(counts.items(), key=lambda kv: str(kv[0])):
        if name not in pngs:
            problems.append(f"{name}: label entry without a PNG")
        elif n > 1:
            problems.append(f"{name}: {n} label entries")
    for entry in labels:
        name = entry.get("image")
        try:
            validate("ScreenLabel", entry)
        except ValidationError as exc:
            problems.append(f"{name}: invalid: {exc.message}")
            continue
        if not entry.get("meta"):
            problems.append(f"{name}: meta missing")
        if name in pngs:
            with Image.open(screens / name) as im:
                size = im.size
            if (entry["width"], entry["height"]) != size:
                problems.append(
                    f"{name}: size {entry['width']}x{entry['height']} != PNG {size[0]}x{size[1]}"
                )
    return problems


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="python -m workshop.labels.check")
    p.add_argument("--labels", type=Path, required=True)
    p.add_argument("--screens", type=Path, required=True)
    args = p.parse_args(argv)
    try:
        labels = json.loads(args.labels.read_text(encoding="utf-8"))
        if not isinstance(labels, list) or not args.screens.is_dir():
            raise ValueError("labels must be a JSON array and --screens a folder")
    except (OSError, ValueError) as exc:
        print(f"bad input: {exc}", file=sys.stderr)
        return 2
    problems = check(labels, args.screens)
    print("\n".join(problems) if problems else f"LABELS OK {len(labels)}")
    return 1 if problems else 0


if __name__ == "__main__":
    raise SystemExit(main())
