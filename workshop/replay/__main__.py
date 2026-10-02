"""python -m workshop.replay SESSION.session.json --out DIR [options]"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from workshop.replay.pipeline import DummyPipeline, OraclePipeline
from workshop.replay.player import replay


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="workshop.replay")
    p.add_argument("session")
    p.add_argument("--out", required=True)
    p.add_argument("--pipeline", choices=["dummy", "oracle"], default="dummy")
    p.add_argument("--realtime", action="store_true")
    p.add_argument("--speed", type=float, default=1.0)
    p.add_argument("--self-capture", action="store_true")
    p.add_argument("--markers", action="store_true")
    p.add_argument("--no-video", action="store_true")
    a = p.parse_args(argv)
    session = Path(a.session)
    if a.pipeline == "oracle":
        sid = json.loads(session.read_text(encoding="utf-8"))["sessionId"]
        pipe = OraclePipeline(session.parent / f"{sid}.truth.jsonl")
    else:
        pipe = DummyPipeline()
    r = replay(
        session, pipe, Path(a.out), realtime=a.realtime, speed=a.speed,
        self_capture=a.self_capture, markers=a.markers, video=not a.no_video,
    )  # fmt: skip
    print(
        f"REPLAY frames={r.frames} events={r.events} late={r.late_frames} maxLagMs={r.max_lag_ms}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
