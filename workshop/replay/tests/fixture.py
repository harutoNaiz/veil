"""A 3 s, 360x800, 30 fps session built with cv2 only (moving bars + known Scrolled events)."""

from __future__ import annotations

import json
from pathlib import Path

import cv2
import numpy as np

T0 = 1000
FPS = 30
FRAMES = 90


def build(out_dir: Path, session_id: str = "fixture") -> Path:
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    w = cv2.VideoWriter(
        str(out_dir / f"{session_id}.mp4"), cv2.VideoWriter_fourcc(*"mp4v"), FPS, (360, 800)
    )
    events, y = [], 0
    for i in range(FRAMES):
        img = np.full((800, 360, 3), 60, np.uint8)
        for k in range(12):
            yy = (k * 80 + y) % 960 - 80
            cv2.rectangle(
                img,
                (20 + 20 * (k % 3), yy),
                (200 + 20 * (k % 3), yy + 40),
                (40 + 15 * k, 200, 90),
                -1,
            )
        w.write(img)
        if 30 <= i < 60:  # one scroll burst: -6 screen px per frame
            events.append(
                {"contractVersion": "1.0", "eventId": len(events), "tMs": T0 + (i * 1000) // FPS,
                 "type": "scrolled", "packageName": "com.veil.synth", "dx": 0, "dy": -6}
            )  # fmt: skip
            y -= 3
    w.release()
    (out_dir / f"{session_id}.events.jsonl").write_text(
        "".join(json.dumps(e) + "\n" for e in events), encoding="utf-8"
    )
    sess = {
        "sessionVersion": "1", "sessionId": session_id, "video": f"{session_id}.mp4", "fps": FPS,
        "frameCount": FRAMES, "t0Ms": T0, "width": 360, "height": 800, "screenWidth": 720,
        "screenHeight": 1600, "scroll": "synthetic", "source": "synthetic",
        "packageName": "com.veil.synth", "situations": {},
    }  # fmt: skip
    path = out_dir / f"{session_id}.session.json"
    path.write_text(json.dumps(sess), encoding="utf-8")
    return path
