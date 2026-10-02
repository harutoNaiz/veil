"""Stand-ins for the tracker, planner, cache and gatekeeper (kept for 2.3.3 unit tests only)."""

from __future__ import annotations

import numpy as np


class StubTracker:
    """Every hide finding becomes a confirmed track, shifted by scroll, dropped after 1 s."""

    def __init__(self) -> None:
        self.tracks: list[dict] = []
        self.next_id = 1

    def on_scroll(self, dy: int, t_ms: int) -> None:
        for t in self.tracks:
            t["rect"]["y"] += dy

    def on_findings(self, findings: list[dict], t_ms: int) -> None:
        for f in findings:
            if f["decision"] == "hide":
                self.tracks.append(
                    {"trackId": self.next_id, "conceptId": f["conceptId"], "layer": f["layer"],
                     "rect": dict(f["rect"]), "state": "confirmed", "born": t_ms}
                )  # fmt: skip
                self.next_id += 1

    def tick(self, t_ms: int, own_covers: list[dict]) -> list[dict]:
        self.tracks = [t for t in self.tracks if t_ms - t["born"] <= 1000]
        return [dict(t) for t in self.tracks]


def plan_stub(tracks: list[dict], **kw) -> dict:
    masks = [
        {"maskId": i + 1, "rect": dict(t["rect"]), "style": "solid", "layer": t["layer"],
         "peekable": True, "conceptIds": [t["conceptId"]], "trackIds": [t["trackId"]]}
        for i, t in enumerate(tracks)
    ]  # fmt: skip
    return {"masks": masks, **{k: v for k, v in kw.items() if k in ("t_ms", "frame_id")}}


class StubCache:
    hits = 0
    misses = 0

    def get(self, h: int, t_ms: int, sig=None) -> np.ndarray | None:
        self.misses += 1
        return None

    def put(self, h: int, fingerprint, t_ms: int, sig=None) -> None:
        return None

    def clear(self) -> None:
        return None


class StubGatekeeper:
    """A full-screen periodic look every 10th frame."""

    def on_frame_look(self, frame: dict) -> dict | None:
        if frame["frameId"] % 10:
            return None
        return {"x": 0, "y": 0, "w": frame["screenWidth"], "h": frame["screenHeight"]}
