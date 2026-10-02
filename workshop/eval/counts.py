"""Count report against the AC-1.2-01 thresholds.

Command line::

    python -m workshop.eval.counts --labels L [--require]

``--require`` exits 1 if any count is LOW.
"""

from __future__ import annotations

import argparse
import sys

from workshop.eval._common import (
    BadInput,
    app_of,
    is_cats,
    is_clean,
    is_hard,
    is_spiders,
    load_labels,
)


def _landscape(lab: dict) -> bool:
    orient = lab.get("meta", {}).get("orientation")
    return orient == "landscape" if orient else lab["width"] > lab["height"]


def counts(labels: list[dict]) -> list[tuple[str, float, float | None]]:
    """Rows of (name, value, threshold); threshold None means informational."""
    n = len(labels)
    dark = sum(1 for lab in labels if lab.get("meta", {}).get("mode") == "dark")
    return [
        ("total", n, 300),
        ("cats", sum(is_cats(lab) for lab in labels), 100),
        ("spiders", sum(is_spiders(lab) for lab in labels), 50),
        ("clean", sum(is_clean(lab) for lab in labels), 150),
        ("hard", sum(is_hard(lab) for lab in labels), 30),
        ("apps", len({app_of(lab) for lab in labels}), 5),
        ("dark share", dark / n if n else 0.0, 0.20),
        ("landscape", sum(_landscape(lab) for lab in labels), None),
    ]


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="python -m workshop.eval.counts")
    p.add_argument("--labels", required=True)
    p.add_argument("--require", action="store_true")
    args = p.parse_args(argv)
    try:
        labels = load_labels(args.labels)
    except BadInput as exc:
        print(f"bad input: {exc}", file=sys.stderr)
        return 2
    low = False
    for name, value, need in counts(labels):
        shown = f"{value:.2f}" if isinstance(value, float) else str(value)
        if need is None:
            print(f"{name}: {shown} (info, a few expected)")
            continue
        ok = value >= need
        low = low or not ok
        print(f"{name}: {shown} (>= {need}) {'OK' if ok else 'LOW'}")
    return 1 if (args.require and low) else 0


if __name__ == "__main__":
    raise SystemExit(main())
