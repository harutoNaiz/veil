"""Checks on replays: self-capture position error and scroll totals per burst."""

from __future__ import annotations

import json
import sys
import tempfile
from pathlib import Path

import numpy as np

from workshop.replay.pipeline import DummyPipeline
from workshop.replay.player import replay
from workshop.replay.render import rect_to_frame

MAGENTA = (255, 0, 255)


class _Recorder:
    def __init__(self, inner) -> None:
        self.inner = inner
        self.name = inner.name
        self.rows: list[tuple[np.ndarray, list[dict]]] = []

    def on_event(self, event):
        return self.inner.on_event(event)

    def on_frame(self, frame_bgr, frame):
        out = self.inner.on_frame(frame_bgr, frame)
        rects = [m["rect"] for r in out if r["kind"] == "maskPlan" for m in r["plan"]["masks"]]
        self.rows.append((frame_bgr.copy(), rects))
        return out


def self_capture_error(session_json: Path, frames: int = 60, pipeline=None) -> int:
    """Max px error (frame px) between plan N's rects and the magenta box seen in input N+1."""
    rec = _Recorder(pipeline or DummyPipeline())
    s = json.loads(Path(session_json).read_text(encoding="utf-8"))
    with tempfile.TemporaryDirectory() as d:
        replay(
            session_json, rec, Path(d), self_capture=True, video=False, solid_bgr=MAGENTA,
            max_frames=frames,
        )  # fmt: skip
    worst = 0
    for n in range(len(rec.rows) - 1):
        img, rects = rec.rows[n + 1][0], rec.rows[n][1]
        h, w = img.shape[:2]
        ys, xs = np.nonzero((img == np.array(MAGENTA, dtype=np.uint8)).all(axis=2))
        boxes = [rect_to_frame(r, w, h, s["screenWidth"]) for r in rects]
        boxes = [b for b in boxes if b[2] > b[0] and b[3] > b[1]]
        if not boxes or not len(xs):
            if bool(boxes) != bool(len(xs)):
                worst = max(worst, 9999)
            continue
        exp = (
            min(b[0] for b in boxes), min(b[1] for b in boxes),
            max(b[2] for b in boxes), max(b[3] for b in boxes),
        )  # fmt: skip
        got = (xs.min(), ys.min(), xs.max() + 1, ys.max() + 1)
        worst = max(worst, max(abs(int(a) - int(b)) for a, b in zip(exp, got, strict=True)))
    return worst


def bursts(moves: list[tuple[int, int]], gap_ms: int = 100) -> list[int]:
    """Sum dy per burst; a new burst starts when the gap to the previous move exceeds gap_ms."""
    out: list[int] = []
    last = None
    for t, dy in moves:
        if last is None or t - last > gap_ms:
            out.append(0)
        out[-1] += dy
        last = t
    return out


def scroll_totals(tape_in: Path) -> list[int]:
    moves = []
    for line in Path(tape_in).read_text(encoding="utf-8").splitlines():
        r = json.loads(line)
        if r["kind"] == "event" and r["event"].get("type") == "scrolled" and r["event"]["dy"] != 0:
            moves.append((r["tMs"], r["event"]["dy"]))
    return bursts(moves)


def main(argv: list[str]) -> int:
    if len(argv) >= 2 and argv[0] == "self-capture":
        err = self_capture_error(Path(argv[1]))
        print(f"SELF-CAPTURE error={err}px")
        return 0 if err <= 1 else 1
    if len(argv) >= 2 and argv[0] == "scroll-totals":
        print(json.dumps(scroll_totals(Path(argv[1]))))
        return 0
    print("usage: python -m workshop.replay.checks self-capture SESSION | scroll-totals TAPE_IN")
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
