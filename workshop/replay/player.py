"""Replay a session through a pipeline with a virtual clock; write tapes and covered video."""

from __future__ import annotations

import base64
import json
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path

import cv2
import numpy as np

from workshop.replay.clock import VirtualClock
from workshop.replay.pipeline import Pipeline
from workshop.replay.render import paint
from workshop.replay.tape import TapeWriter


@dataclass
class ReplayResult:
    frames: int
    events: int
    tape_in: Path
    tape_out: Path
    video: Path | None
    timing: Path
    late_frames: int
    max_lag_ms: int


class _VideoOut:
    def __init__(self, path: Path, w: int, h: int, fps: int) -> None:
        self.proc = None
        self.cv = None
        try:
            self.proc = subprocess.Popen(
                ["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "bgr24",
                 "-s", f"{w}x{h}", "-r", str(fps), "-i", "-", "-c:v", "libx264",
                 "-preset", "veryfast", "-pix_fmt", "yuv420p", "-crf", "23", str(path)],
                stdin=subprocess.PIPE,
            )  # fmt: skip
        except OSError:
            self.cv = cv2.VideoWriter(str(path), cv2.VideoWriter_fourcc(*"mp4v"), fps, (w, h))

    def write(self, img: np.ndarray) -> None:
        if self.proc is not None:
            self.proc.stdin.write(np.ascontiguousarray(img).tobytes())
        else:
            self.cv.write(img)

    def close(self) -> None:
        if self.proc is not None:
            self.proc.stdin.close()
            self.proc.wait()
        else:
            self.cv.release()


def _thumb_b64(img: np.ndarray) -> str:
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    small = cv2.resize(gray, (32, 64), interpolation=cv2.INTER_AREA)
    return base64.b64encode(small.tobytes()).decode()


def replay(
    session_json: Path,
    pipeline: Pipeline,
    out_dir: Path,
    *,
    realtime: bool = False,
    speed: float = 1.0,
    self_capture: bool = False,
    markers: bool = False,
    video: bool = True,
    solid_bgr=(40, 40, 40),
    max_frames: int | None = None,
) -> ReplayResult:
    session_json = Path(session_json)
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    s = json.loads(session_json.read_text(encoding="utf-8"))
    sid, fps, t0 = s["sessionId"], s["fps"], s["t0Ms"]
    events_path = session_json.parent / f"{sid}.events.jsonl"
    events = [json.loads(x) for x in events_path.read_text("utf-8").splitlines() if x.strip()]
    cap = cv2.VideoCapture(str(session_json.parent / s["video"]))
    n_frames = s["frameCount"] if max_frames is None else min(max_frames, s["frameCount"])

    header = {
        "kind": "header", "tMs": t0, "tapeVersion": "1", "sessionId": sid, "fps": fps,
        "width": s["width"], "height": s["height"], "screenWidth": s["screenWidth"],
        "screenHeight": s["screenHeight"], "selfCapture": self_capture, "pipeline": pipeline.name,
    }  # fmt: skip
    tin = TapeWriter(out_dir / f"{sid}.tape-in.jsonl", header)
    tout = TapeWriter(out_dir / f"{sid}.tape-out.jsonl", header)
    vid_path = out_dir / f"{sid}.covered.mp4"
    vout = _VideoOut(vid_path, s["width"], s["height"], fps) if video else None

    items = [(e["tMs"], 0, e["eventId"], e) for e in events]
    items += [(t0 + (i * 1000) // fps, 1, i, None) for i in range(n_frames)]
    items.sort(key=lambda x: x[:3])

    clock = VirtualClock(t0)
    sw = s["screenWidth"]
    prev_plan: dict | None = None
    dy_sum = 0
    scrolled_now = False
    lags: list[int] = []
    n_events = 0
    n_done = 0
    wall0 = time.perf_counter()

    def emit(recs: list[dict], t: int) -> dict | None:
        plan = None
        for r in recs:
            r = dict(r)
            r.setdefault("tMs", t)
            tout.write(r)
            if r["kind"] == "maskPlan":
                plan = r["plan"]
        return plan

    for t, kind, idx, ev in items:
        clock.advance_to(t)
        due = wall0 + (t - t0) / 1000.0 / speed
        if realtime:
            delay = due - time.perf_counter()
            if delay > 0:
                time.sleep(delay)
        if kind == 0:
            n_events += 1
            tin.write({"kind": "event", "tMs": t, "event": ev})
            if ev.get("type") == "scrolled":
                dy_sum += ev["dy"]
                scrolled_now = True
            emit(pipeline.on_event(ev), t)
            continue
        ok, raw = cap.read()
        if not ok:
            break
        n_done += 1
        if realtime:
            lags.append(max(0, int((time.perf_counter() - due) * 1000)))
        delivered = raw
        overlay: list[dict] = []
        if self_capture and prev_plan is not None:
            delivered = paint(raw, prev_plan, sw, solid_bgr)
            overlay = [m["rect"] for m in prev_plan["masks"]]
        frame = {
            "contractVersion": "1.0", "frameId": idx, "sessionId": sid, "tMs": t,
            "width": s["width"], "height": s["height"], "screenWidth": sw,
            "screenHeight": s["screenHeight"], "rotation": 0, "source": "replay",
            "ownOverlay": overlay,
        }  # fmt: skip
        tin.write(
            {"kind": "frame", "tMs": t, "frameId": idx, "thumb": _thumb_b64(delivered),
             "ownOverlay": overlay}
        )  # fmt: skip
        plan = emit(pipeline.on_frame(delivered, frame), t)
        if vout is not None:
            img = paint(raw, plan, sw, solid_bgr) if plan else raw.copy()
            if markers and scrolled_now:
                img[:6, :] = (0, 0, 255)
                cv2.putText(img, f"dy={dy_sum}", (8, 40), cv2.FONT_HERSHEY_SIMPLEX, 0.8,
                            (255, 255, 255), 2)  # fmt: skip
            vout.write(img)
        scrolled_now = False
        if plan is not None:
            prev_plan = plan
    cap.release()
    tin.close()
    tout.close()
    wall = time.perf_counter() - wall0
    if vout is not None:
        vout.close()
    timing = out_dir / f"{sid}.timing.json"
    late = sum(1 for x in lags if x > 33)
    timing.write_text(
        json.dumps(
            {"realtime": realtime, "speed": speed, "frames": n_done, "lateFrames": late,
             "maxLagMs": max(lags, default=0), "wallS": wall, "lagsMs": lags}
        ),
        encoding="utf-8",
    )  # fmt: skip
    return ReplayResult(
        n_done, n_events, tin.path, tout.path, vid_path if vout else None, timing, late,
        max(lags, default=0),
    )  # fmt: skip
