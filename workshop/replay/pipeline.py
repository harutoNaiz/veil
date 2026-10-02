"""Pipeline protocol and the two built-in test pipelines."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Protocol

import numpy as np

CV = "1.0"


class Pipeline(Protocol):
    name: str

    def on_event(self, event: dict) -> list[dict]: ...

    def on_frame(self, frame_bgr: np.ndarray, frame: dict) -> list[dict]: ...


def _plan_record(frame: dict, rects: list[dict], reason: str, session: dict) -> dict:
    masks = [
        {
            "contractVersion": CV,
            "maskId": i + 1,
            "rect": r,
            "style": "solid",
            "layer": 2,
            "peekable": True,
            "conceptIds": ["dummy"],
            "trackIds": [i + 1],
        }
        for i, r in enumerate(rects)
    ]
    plan = {
        "contractVersion": CV,
        "planId": frame["frameId"],
        "tMs": frame["tMs"],
        "screenWidth": frame["screenWidth"],
        "screenHeight": frame["screenHeight"],
        "rotation": 0,
        "masks": masks,
        "basedOnFrameId": frame["frameId"],
        "reason": reason,
    }
    return {"kind": "maskPlan", "tMs": frame["tMs"], "frameId": frame["frameId"], "plan": plan}


class DummyPipeline:
    """One fixed solid cover (screen px), shifted by every Scrolled dy."""

    name = "dummy-v1"

    def __init__(self, rect: dict | None = None) -> None:
        self.rect = dict(rect or {"x": 72, "y": 400, "w": 576, "h": 400})
        self._scrolled = False
        self._first = True

    def on_event(self, event: dict) -> list[dict]:
        if event.get("type") == "scrolled":
            self.rect["x"] += event["dx"]
            self.rect["y"] += event["dy"]
            self._scrolled = True
        return []

    def on_frame(self, frame_bgr: np.ndarray, frame: dict) -> list[dict]:
        reason = "scroll" if self._scrolled and not self._first else "look"
        self._first = False
        self._scrolled = False
        return [_plan_record(frame, [dict(self.rect)], reason, {})]


class OraclePipeline:
    """maskPlan = the truth boxes of that frame (solid)."""

    name = "oracle-v1"

    def __init__(self, truth_path: Path) -> None:
        self.truth = {}
        for line in Path(truth_path).read_text(encoding="utf-8").splitlines():
            if line.strip():
                row = json.loads(line)
                self.truth[row["i"]] = row

    def on_event(self, event: dict) -> list[dict]:
        return []

    def on_frame(self, frame_bgr: np.ndarray, frame: dict) -> list[dict]:
        row = self.truth.get(frame["frameId"], {})
        rects = [dict(b["rect"]) for b in row.get("boxes", [])][:24]
        return [_plan_record(frame, rects, "look", {})]
