"""Freeze the test set: a checksum over the test PNGs and their labels, recorded in the doc.

Command line::

    python -m workshop.eval.freeze write|check --screens DIR --labels L --splits S --doc DOC

``check`` prints ``TEST SET CHANGED`` and exits 1 on a mismatch; exit 2 on bad input.
"""

from __future__ import annotations

import argparse
import datetime
import hashlib
import json
import re
import sys
from pathlib import Path

from workshop.eval._common import BadInput, load_json, load_labels

BEGIN = "<!-- veil:testset -->"
END = "<!-- /veil:testset -->"
_CHECKSUM = re.compile(r"checksum: sha256:([0-9a-f]{64})")


def checksum(screens: Path, labels: list[dict], test_names: list[str] | set[str]) -> str:
    by_name = {lab["image"]: lab for lab in labels}
    lines = []
    for name in sorted(test_names):
        png = hashlib.sha256((Path(screens) / name).read_bytes()).hexdigest()
        text = json.dumps(by_name[name], sort_keys=True, separators=(",", ":"))
        lab = hashlib.sha256(text.encode("utf-8")).hexdigest()
        lines.append(f"{name}\t{png}\t{lab}\n")
    return hashlib.sha256("".join(lines).encode("utf-8")).hexdigest()


def _block(doc_text: str) -> tuple[int, int]:
    a, b = doc_text.find(BEGIN), doc_text.find(END)
    if a < 0 or b < a:
        raise BadInput(f"doc has no {BEGIN} ... {END} block")
    return a, b + len(END)


def write(doc: Path, digest: str, test_n: int, dev_n: int, seed: int) -> None:
    text = Path(doc).read_text(encoding="utf-8")
    a, b = _block(text)
    block = (
        f"{BEGIN}\n- test images: {test_n}\n- dev images: {dev_n}\n- seed: {seed}\n"
        f"- checksum: sha256:{digest}\n- frozen: {datetime.date.today().isoformat()}\n{END}"
    )
    Path(doc).write_text(text[:a] + block + text[b:], encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="python -m workshop.eval.freeze")
    p.add_argument("mode", choices=["write", "check"])
    p.add_argument("--screens", required=True)
    p.add_argument("--labels", required=True)
    p.add_argument("--splits", required=True)
    p.add_argument("--doc", required=True)
    args = p.parse_args(argv)
    try:
        labels = load_labels(args.labels)
        splits = load_json(args.splits)
        test = list(splits["test"])  # type: ignore[index]
        known = {lab["image"] for lab in labels}
        if any(n not in known for n in test):
            raise BadInput("a test image has no label entry")
        doc = Path(args.doc)
        text = doc.read_text(encoding="utf-8")
        _block(text)
        digest = checksum(Path(args.screens), labels, test)
        if args.mode == "write":
            write(doc, digest, len(test), len(splits["dev"]), int(splits["seed"]))  # type: ignore[index]
            print(f"FROZEN {len(test)} test images, checksum sha256:{digest}")
            return 0
        a, b = _block(text)
        m = _CHECKSUM.search(text[a:b])
        if not m:
            raise BadInput("doc has no recorded checksum (PENDING-HUMAN?)")
        if m.group(1) != digest:
            print("TEST SET CHANGED")
            return 1
        print(f"FREEZE OK sha256:{digest}")
        return 0
    except (BadInput, KeyError, TypeError, OSError) as exc:
        print(f"bad input: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
