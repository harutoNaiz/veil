"""Synthetic recording session with exact truth: tall canvases scrolled by a known script."""

from __future__ import annotations

import argparse
import json
import random
import subprocess
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

from workshop.recordings.downscale import downscale
from workshop.screens.synth import _cat, _dog, _spider

SW, SH, FPS, T0 = 720, 1600, 30, 1000
ROUND_FRAMES = 294
PKG, OTHER = "com.veil.synth", "com.veil.other"
SHAPES = {"cat": (_cat, "cats"), "spider": (_spider, "spiders"), "dog": (_dog, "dogs")}


def _box(shape: str, cx: int, cy: int, r: int) -> dict:
    if shape == "cat":
        x0, y0, x1, y1 = cx - r, cy - int(1.5 * r), cx + r, cy + r
    elif shape == "spider":
        x0, y0, x1, y1 = cx - int(1.9 * r), cy - r, cx + int(1.9 * r), cy + r
    else:
        x0, y0, x1, y1 = cx - r - 5, cy - r, cx + r + 5, cy + r
    return {"x": x0, "y": y0, "w": x1 - x0, "h": y1 - y0}


def _canvas(kind: str, height: int, seed: int) -> tuple[np.ndarray, list[dict]]:
    """Return (BGR canvas, boxes). Per-row random stripes make every row unique."""
    rng = random.Random(seed)
    img = Image.new("RGB", (SW, height), (120, 120, 130))
    d = ImageDraw.Draw(img)
    boxes: list[dict] = []

    def card(x, y, w, h, shape_r, n):
        col = tuple(rng.randint(150, 235) for _ in range(3))
        d.rectangle([x, y, x + w - 1, y + h - 1], fill=col)
        shape = rng.choice(list(SHAPES))
        cx, cy = x + w // 2, y + h // 2
        SHAPES[shape][0](d, cx, cy, shape_r, (40, 40, 50))
        key = f"{kind}-{shape}-{n}"
        boxes.append(
            {"key": key, "conceptId": SHAPES[shape][1], "rect": _box(shape, cx, cy, shape_r)}
        )

    if kind == "feed":
        for n, y in enumerate(range(20, height - 440, 440)):
            card(20, y, 680, 420, 90, n)
    elif kind == "grid":
        for n in range(((height - 20) // 240) * 3):
            card(20 + (n % 3) * 232, 20 + (n // 3) * 240, 220, 220, 45, n)
    elif kind == "reels":
        for n in range(height // SH):
            card(0, n * SH, SW, SH, 200, n)
    else:  # video A/B, other: one flat picture, no tracked boxes
        col = tuple(rng.randint(30, 220) for _ in range(3))
        d.rectangle([0, 0, SW, height], fill=col)
        SHAPES["cat"][0](d, SW // 2, height // 2, 220, tuple(255 - c for c in col))
    arr = np.asarray(img).astype(np.int16)
    stripes = np.random.default_rng(seed).integers(-25, 26, size=height)
    arr += stripes[:, None, None].astype(np.int16)
    arr = np.clip(arr, 0, 255).astype(np.uint8)[:, :, ::-1]
    return np.ascontiguousarray(arr), boxes


class _Script:
    def __init__(self, n_frames: int):
        self.n = n_frames
        self.frames: list[tuple[str, int]] = []  # (scene, dy)
        self.events: list[tuple[int, dict]] = []  # (frame, event without ids)
        self.marks: list[tuple[int, str]] = []
        self.sit: dict[str, int] = {}
        self.pending_on = False

    def add(self, count, scene, dy=0):
        for k in range(count):
            if len(self.frames) >= self.n:
                return
            i = len(self.frames)
            if self.pending_on:
                self.pending_on = False
                self.events.append((i, {"type": "screenOn", "packageName": PKG}))
                self.marks.append((i, "unlock"))
            self.frames.append((scene, dy(k) if callable(dy) else dy))

    def event(self, ev, mark=None):
        i = len(self.frames)
        if i < self.n:
            self.events.append((i, ev))
            if mark:
                self.marks.append((i, mark))

    def count(self, name):
        self.sit[name] = self.sit.get(name, 0) + 1

    def round(self):
        a = self.add
        a(15, "feed")
        self.count("slowScroll")
        a(45, "feed", -6)
        a(15, "feed")
        self.count("fling")
        a(24, "feed", lambda k: -2 * max(1, round(24 * (1 - k / 24))))
        a(15, "grid")
        self.count("exploreGrid")
        a(36, "grid", -10)
        a(15, "grid")
        a(3, "reels")
        self.count("reelsSwipe")
        a(8, "reels", -200)
        a(10, "reels")
        self.count("reelsSwipe")
        a(8, "reels", -200)
        a(15, "reels")
        self.count("videoSceneCut")
        a(15, "video0")
        self.event({"type": "contentChanged", "packageName": PKG}, "sceneCut")
        a(15, "video1")
        self.count("appSwitch")
        self.event({"type": "windowChanged", "packageName": OTHER}, "appSwitch")
        a(20, "other")
        self.event({"type": "windowChanged", "packageName": PKG}, "appSwitch")
        a(5, "feed")
        self.count("lockUnlock")
        self.event({"type": "screenOff", "packageName": PKG}, "lock")
        a(30, "off")
        self.pending_on = True


def _write(path: Path, text: str) -> None:
    Path(path).write_bytes(text.encode("utf-8"))


def generate(
    out_dir: Path,
    session_id: str = "synth-known-scroll",
    seconds: int = 20,
    seed: int = 7,
    event_offset_ms: int = 0,
) -> Path:
    out_dir = Path(out_dir)
    (out_dir / "labels").mkdir(parents=True, exist_ok=True)
    n = seconds * FPS
    sc = _Script(n)
    sc.round()
    while len(sc.frames) + ROUND_FRAMES <= n:
        sc.round()
    sc.add(n - len(sc.frames), "feed")  # pad (also flushes a pending screenOn)

    scroll = {"feed": 0, "grid": 0, "reels": 0}
    ys = []
    for scene, dy in sc.frames:
        if scene in scroll:
            scroll[scene] -= dy
        ys.append(scroll.get(scene, 0))
    canv = {}
    for k, name in enumerate(("feed", "grid", "reels", "video0", "video1", "other")):
        h = scroll.get(name, 0) + 2 * SH
        if name == "reels":
            h = ((h + SH - 1) // SH) * SH
        canv[name] = _canvas(name, h, seed * 10 + k)
    black = np.zeros((SH, SW, 3), np.uint8)

    def t_of(i):
        return T0 + (i * 1000) // FPS

    orig = out_dir / f"{session_id}.orig.mp4"
    cmd = ["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "bgr24"]
    cmd += ["-s", f"{SW}x{SH}", "-r", str(FPS), "-i", "-", "-an", "-c:v", "libx264"]
    cmd += ["-preset", "veryfast", "-crf", "12", "-pix_fmt", "yuv420p", str(orig)]
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    truth, driver = [], []
    for i, ((scene, dy), y) in enumerate(zip(sc.frames, ys, strict=True)):
        if scene == "off":
            frame, boxes = black, []
        else:
            frame = canv[scene][0][y : y + SH]
            boxes = []
            for b in canv[scene][1]:
                r = b["rect"]
                y0, y1 = max(0, r["y"] - y), min(SH, r["y"] + r["h"] - y)
                if y1 - y0 >= 8:
                    rect = {**r, "y": y0, "h": y1 - y0}
                    boxes.append({"key": b["key"], "conceptId": b["conceptId"], "rect": rect})
        proc.stdin.write(frame.tobytes())
        name = "video" if scene.startswith("video") else scene
        truth.append({"i": i, "tMs": t_of(i), "scrollY": y, "scene": name, "boxes": boxes})
        if dy:
            driver.append({"tMs": t_of(i), "dy": dy})
    proc.stdin.close()
    if proc.wait() != 0:
        raise RuntimeError("ffmpeg failed")
    downscale(orig, out_dir / f"{session_id}.mp4")

    events = list(sc.events)
    for i, (_, dy) in enumerate(sc.frames):
        if dy:
            events.append((i, {"type": "scrolled", "packageName": PKG, "dx": 0, "dy": dy}))
    events.sort(key=lambda p: p[0])  # stable: state events come before scroll at the same frame
    lines = []
    for eid, (i, ev) in enumerate(events):
        ev = {"contractVersion": "1.0", **ev, "eventId": eid, "tMs": t_of(i) + event_offset_ms}
        lines.append(json.dumps(ev, sort_keys=True))
    _write(out_dir / f"{session_id}.events.jsonl", "\n".join(lines) + "\n")
    _write(out_dir / f"{session_id}.truth.jsonl", "\n".join(json.dumps(t) for t in truth) + "\n")
    _write(out_dir / f"{session_id}.driver.json", json.dumps(driver))
    names = (
        "slowScroll",
        "fling",
        "reelsSwipe",
        "exploreGrid",
        "videoSceneCut",
        "appSwitch",
        "lockUnlock",
    )
    session = {
        "sessionVersion": "1",
        "sessionId": session_id,
        "video": f"{session_id}.mp4",
        "fps": FPS,
        "frameCount": n,
        "t0Ms": T0,
        "width": 360,
        "height": 800,
        "screenWidth": SW,
        "screenHeight": SH,
        "scroll": "synthetic",
        "source": "synthetic",
        "packageName": PKG,
        "situations": {k: sc.sit.get(k, 0) for k in names},
    }
    path = out_dir / f"{session_id}.session.json"
    _write(path, json.dumps(session, indent=1))
    label = _label(session_id, truth, sc.marks, t_of, n)
    _write(out_dir / "labels" / f"{session_id}.json", json.dumps(label))
    return path


def _label(session_id, truth, marks, t_of, n) -> dict:
    per_key: dict[str, dict] = {}
    for fr in truth:
        for b in fr["boxes"]:
            if b["conceptId"] == "dogs":  # lookalike: truth only, never a concept track
                continue
            tr = per_key.setdefault(b["key"], {"conceptId": b["conceptId"], "pts": []})
            tr["pts"].append((fr["i"], b["rect"]))
    tracks = []
    for key, tr in per_key.items():
        spans, kfs, run = [], {}, []
        pts = tr["pts"]
        for j, (i, rect) in enumerate(pts):
            run.append((i, rect))
            if j + 1 == len(pts) or pts[j + 1][0] != i + 1:
                spans.append({"startMs": t_of(run[0][0]), "endMs": t_of(run[-1][0])})
                for k, (ri, rr) in enumerate(run):
                    if k % 15 == 0 or k == len(run) - 1:
                        kfs[t_of(ri)] = rr
                run = []
        keyframes = [{"tMs": t, "rect": r} for t, r in sorted(kfs.items())]
        tracks.append(
            {"key": key, "conceptId": tr["conceptId"], "spans": spans, "keyframes": keyframes}
        )
    mk = [{"tMs": t_of(i), "type": m} for i, m in marks]
    # clean = exactly the stretches where no concept track is visible
    busy = sorted((sp["startMs"], sp["endMs"]) for tr in tracks for sp in tr["spans"])
    clean, cur = [], t_of(0)
    for st, en in busy:
        if st > cur:
            clean.append({"startMs": cur, "endMs": st})
        cur = max(cur, en)
    if t_of(n - 1) > cur:
        clean.append({"startMs": cur, "endMs": t_of(n - 1)})
    return {
        "labelVersion": "1",
        "sessionId": session_id,
        "durationMs": t_of(n) - T0,
        "screenWidth": SW,
        "screenHeight": SH,
        "labeller": "synth",
        "reviewedBy": None,
        "tracks": tracks,
        "marks": mk,
        "clean": clean,
    }


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="python -m workshop.recordings.synth_session")
    p.add_argument("--out", type=Path, required=True)
    p.add_argument("--seconds", type=int, default=20)
    p.add_argument("--session-id", default="synth-known-scroll")
    p.add_argument("--event-offset-ms", type=int, default=0)
    a = p.parse_args(argv)
    print(generate(a.out, a.session_id, a.seconds, event_offset_ms=a.event_offset_ms))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
