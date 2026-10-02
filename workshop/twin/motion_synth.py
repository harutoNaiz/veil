"""Motion test sessions (2.3.3): feed, reels, video and torture scripts, same file set as 2.1.1."""

from __future__ import annotations

import json
import random
import subprocess
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

from workshop.recordings.downscale import downscale
from workshop.recordings.synth_session import FPS, PKG, SH, SW, T0, _box, _label, _write
from workshop.screens.synth import _cat, _dog, _spider

DRAW = {"cat": (_cat, "cats"), "spider": (_spider, "spiders"), "dog": (_dog, "dogs")}
FEED_CYCLE = ("cat", "dog", "spider", "cat", "cat", "dog", "spider", "cat")
SCRIPTS = ("feed", "reels", "video", "torture")


def _canvas(kind: str, height: int, seed: int) -> tuple[np.ndarray, list[dict]]:
    rng = random.Random(seed)
    img = Image.new("RGB", (SW, height), (120, 120, 130))
    d = ImageDraw.Draw(img)
    boxes: list[dict] = []

    def card(x, y, w, h, shape, r, n):
        col = tuple(rng.randint(150, 235) for _ in range(3))
        d.rectangle([x, y, x + w - 1, y + h - 1], fill=col)
        cx, cy = x + w // 2, y + h // 2
        DRAW[shape][0](d, cx, cy, r, (40, 40, 50))
        boxes.append(
            {
                "key": f"{kind}-{shape}-{n}",
                "conceptId": DRAW[shape][1],
                "rect": _box(shape, cx, cy, r),
            }
        )

    if kind == "feed":
        for n, y in enumerate(range(20, height - 440, 440)):
            card(20, y, 680, 420, FEED_CYCLE[n % len(FEED_CYCLE)], 90, n)
    elif kind == "reels":
        for n in range(height // SH):
            card(0, n * SH, SW, SH, "cat" if n % 2 == 0 else "dog", 200, n)
    else:  # video0: flat, nothing; video1: flat with a cat
        col = tuple(rng.randint(30, 220) for _ in range(3))
        d.rectangle([0, 0, SW, height], fill=col)
        if kind == "video1":
            ink = tuple(255 - c for c in col)
            _cat(d, SW // 2, height // 2, 220, ink)
            boxes.append(
                {
                    "key": "video-cat-0",
                    "conceptId": "cats",
                    "rect": _box("cat", SW // 2, height // 2, 220),
                }
            )
    arr = np.asarray(img).astype(np.int16)
    stripes = np.random.default_rng(seed).integers(-25, 26, size=height)
    arr += stripes[:, None, None].astype(np.int16)
    arr = np.clip(arr, 0, 255).astype(np.uint8)[:, :, ::-1]
    return np.ascontiguousarray(arr), boxes


class _S:
    def __init__(self) -> None:
        self.frames: list[tuple[str, int]] = []
        self.events: list[tuple[int, dict]] = []
        self.marks: list[tuple[int, str]] = []

    def hold(self, n: int, scene: str) -> None:
        self.frames += [(scene, 0)] * n

    def move(self, scene: str, dys: list[int]) -> None:
        self.frames += [(scene, dy) for dy in dys]

    def cut(self, scene: str, n: int) -> None:
        self.events.append((len(self.frames), {"type": "contentChanged", "packageName": PKG}))
        self.marks.append((len(self.frames), "sceneCut"))
        self.hold(n, scene)


def _fling(k: int = 14, v: int = 120, step: int = 8) -> list[int]:
    return [-(v - step * i) for i in range(k)]


def _script(name: str) -> _S:
    s = _S()
    if name == "feed":
        s.hold(20, "feed")
        s.move("feed", [-6] * 60)
        s.hold(10, "feed")
        for _ in range(2):
            s.move("feed", _fling(10, 80, 6))
            s.hold(8, "feed")
            s.move("feed", [-d for d in _fling(10, 80, 6)])
            s.hold(8, "feed")
        s.hold(180 - len(s.frames), "feed")
    elif name == "reels":
        s.hold(20, "reels")
        for _ in range(4):
            s.move("reels", [-400] * 4)
            s.hold(30 if _ < 3 else 10, "reels")
        s.hold(180 - len(s.frames), "reels")
    elif name == "video":
        s.hold(60, "video0")
        s.cut("video1", 120)
    else:  # torture, 24 s
        s.hold(15, "feed")
        for _ in range(10):
            s.move("feed", _fling())
            s.hold(4, "feed")
            s.move("feed", [-d for d in _fling()])
            s.hold(6, "feed")
        s.hold(15, "reels")
        for _ in range(6):
            s.move("reels", [-400] * 4)
            s.hold(10, "reels")
        s.hold(15, "video0")
        for scene in ("video1", "video0", "video1", "video0", "video1"):
            s.cut(scene, 30)
        s.hold(720 - len(s.frames), "video1")
    return s


def generate(out_dir: Path, script: str, seed: int, session_id: str | None = None) -> Path:
    out_dir = Path(out_dir)
    sid = session_id or f"{script}-{seed}"
    (out_dir / "labels").mkdir(parents=True, exist_ok=True)
    s = _script(script)
    n = len(s.frames)
    cum: dict[str, list[int]] = {}
    pos: dict[str, int] = {}
    for scene, dy in s.frames:
        pos[scene] = pos.get(scene, 0) - dy
        cum.setdefault(scene, []).append(pos[scene])
    start = {k: max(0, -min(v)) for k, v in cum.items()}
    canv = {}
    for k, name in enumerate(sorted(cum)):
        h = max(cum[name]) + start[name] + SH
        kind = "feed" if name == "feed" else name
        if name == "reels":
            h = ((h + SH - 1) // SH) * SH
        canv[name] = _canvas(kind, max(h, 2 * SH), seed * 10 + k)
    run = {k: start[k] for k in cum}
    ys = []
    for scene, dy in s.frames:
        run[scene] -= dy
        ys.append(run[scene])

    def t_of(i: int) -> int:
        return T0 + (i * 1000) // FPS

    orig = out_dir / f"{sid}.orig.mp4"
    cmd = ["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "bgr24"]
    cmd += ["-s", f"{SW}x{SH}", "-r", str(FPS), "-i", "-", "-an", "-c:v", "libx264"]
    cmd += ["-preset", "veryfast", "-crf", "12", "-pix_fmt", "yuv420p", str(orig)]
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    truth, driver = [], []
    for i, ((scene, dy), y) in enumerate(zip(s.frames, ys, strict=True)):
        img, cboxes = canv[scene]
        proc.stdin.write(img[y : y + SH].tobytes())
        boxes = []
        for b in cboxes:
            r = b["rect"]
            y0, y1 = max(0, r["y"] - y), min(SH, r["y"] + r["h"] - y)
            if y1 - y0 >= 8:
                boxes.append({**b, "rect": {**r, "y": y0, "h": y1 - y0}})
        name = "video" if scene.startswith("video") else scene
        truth.append({"i": i, "tMs": t_of(i), "scrollY": y, "scene": name, "boxes": boxes})
        if dy:
            driver.append({"tMs": t_of(i), "dy": dy})
    proc.stdin.close()
    if proc.wait() != 0:
        raise RuntimeError("ffmpeg failed")
    downscale(orig, out_dir / f"{sid}.mp4")
    evs = list(s.events)
    for i, (_, dy) in enumerate(s.frames):
        if dy:
            evs.append((i, {"type": "scrolled", "packageName": PKG, "dx": 0, "dy": dy}))
    evs.sort(key=lambda p: p[0])
    lines = []
    for eid, (i, ev) in enumerate(evs):
        lines.append(
            json.dumps(
                {"contractVersion": "1.0", **ev, "eventId": eid, "tMs": t_of(i)}, sort_keys=True
            )
        )
    _write(out_dir / f"{sid}.events.jsonl", "\n".join(lines) + "\n")
    _write(out_dir / f"{sid}.truth.jsonl", "\n".join(json.dumps(t) for t in truth) + "\n")
    _write(out_dir / f"{sid}.driver.json", json.dumps(driver))
    session = {
        "sessionVersion": "1", "sessionId": sid, "video": f"{sid}.mp4", "fps": FPS,
        "frameCount": n, "t0Ms": T0, "width": 360, "height": 800, "screenWidth": SW,
        "screenHeight": SH, "scroll": "synthetic", "source": "synthetic", "packageName": PKG,
        "situations": {"script": script},
    }  # fmt: skip
    path = out_dir / f"{sid}.session.json"
    _write(path, json.dumps(session, indent=1))
    _write(out_dir / "labels" / f"{sid}.json", json.dumps(_label(sid, truth, s.marks, t_of, n)))
    return path


def ensure_test_set(out: str | Path = "data/ch2/synth-test") -> Path:
    from workshop.recordings.synth_session import generate as gen_session

    d = Path(out)
    for sid, seed in (("synth-test-3", 3), ("synth-test-4", 4)):
        if not (d / f"{sid}.session.json").exists():
            gen_session(d, sid, seconds=30, seed=seed)
    if not (d / "torture-22.session.json").exists():
        generate(d, "torture", 22)
    return d
