"""Join own.jsonl (cover rects by time) into frames.jsonl as ownOverlay."""

from __future__ import annotations

import argparse
import bisect
import json
from pathlib import Path

from workshop.contracts.validate import validate


def read_jsonl(path: Path) -> list[dict]:
    lines = path.read_text(encoding="utf-8").splitlines()
    return [json.loads(line) for line in lines if line.strip()]


def join(frames: list[dict], own: list[dict]) -> list[dict]:
    """Fill ownOverlay per frame from the latest own sample with tMs <= frame tMs."""
    samples = sorted(own, key=lambda s: s["tMs"])
    times = [s["tMs"] for s in samples]
    out = []
    for frame in frames:
        i = bisect.bisect_right(times, frame["tMs"]) - 1
        rects = samples[i]["rects"] if i >= 0 else []
        row = dict(frame)
        row["ownOverlay"] = [{"x": r["x"], "y": r["y"], "w": r["w"], "h": r["h"]} for r in rects]
        validate("Frame", row)
        out.append(row)
    return out


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("frames", type=Path)
    p.add_argument("own", type=Path)
    p.add_argument("-o", "--out", type=Path, required=True)
    a = p.parse_args(argv)
    rows = join(read_jsonl(a.frames), read_jsonl(a.own))
    a.out.write_text("".join(json.dumps(r) + "\n" for r in rows), encoding="utf-8")
    print(f"joined {len(rows)} frames")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
