"""Tracker (2.3.1): sightings -> stable tracks that follow their item.

Integer geometry only (the Kotlin port must match exactly); the single float is
``_fraction`` for the contract's ``selfCaptureFraction``. Ties are always broken
by an explicit sort key, never by dict or set order.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class TrackParams:
    confirm_n: int
    hold_ms: int
    max_hold_ms: int
    park_ms: int = 3000
    iou_hide_pct: int = 30
    iou_keep_pct: int = 50
    self_capture_pct: int = 80


TRACK_MODES = {
    "light": TrackParams(3, 800, 10000),
    "balanced": TrackParams(2, 1500, 20000),
    "strict": TrackParams(1, 3000, 30000),
}


def _fraction(pct: int) -> float:
    return pct / 100


def _inter(a: dict, b: dict) -> int:
    w = min(a["x"] + a["w"], b["x"] + b["w"]) - max(a["x"], b["x"])
    h = min(a["y"] + a["h"], b["y"] + b["h"]) - max(a["y"], b["y"])
    if w <= 0 or h <= 0:
        return 0
    return w * h


def iou_pct(a: dict, b: dict) -> int:
    inter = _inter(a, b)
    if inter == 0:
        return 0
    union = a["w"] * a["h"] + b["w"] * b["h"] - inter
    return inter * 100 // union


def covered_pct(r: dict, covers: list[dict]) -> int:
    """Percent of the area of r under the union of covers."""
    area = r["w"] * r["h"]
    if area <= 0:
        return 0
    raster = np.zeros((r["h"], r["w"]), dtype=bool)
    for c in covers:
        x0 = max(c["x"], r["x"]) - r["x"]
        y0 = max(c["y"], r["y"]) - r["y"]
        x1 = min(c["x"] + c["w"], r["x"] + r["w"]) - r["x"]
        y1 = min(c["y"] + c["h"], r["y"] + r["h"]) - r["y"]
        if x1 > x0 and y1 > y0:
            raster[y0:y1, x0:x1] = True
    return int(np.count_nonzero(raster)) * 100 // area


class _T:
    def __init__(self, track_id: int, f: dict, t: int):
        self.track_id = track_id
        self.concept_id = f["conceptId"]
        self.layer = f["layer"]
        self.scope = f.get("scope", "object")
        self.first_seen = t
        self.sightings = 0
        self.state = "tentative"
        self.prev_state = "tentative"
        self.parked_until: int | None = None
        self.peeked = False
        self.cut = False
        self.rect = dict(f["rect"])
        self.last_seen = t
        self.hold_until = t
        self.max_hold_until = t
        self.finding_id: str | None = None
        self.pct = 0


class Tracker:
    def __init__(
        self,
        mode: str = "balanced",
        screen_w: int = 720,
        screen_h: int = 1600,
        *,
        self_capture_rule: bool = True,
        params: TrackParams | None = None,
    ):
        self.p = params or TRACK_MODES[mode]
        self.w = screen_w
        self.h = screen_h
        self.rule = self_capture_rule
        self.tracks: list[_T] = []
        self.next_id = 1

    def on_scroll(self, dy: int, t_ms: int) -> None:
        for tr in self.tracks:
            tr.rect["y"] += dy

    def _sight(self, tr: _T, f: dict, t: int) -> None:
        p = self.p
        tr.sightings += 1
        tr.rect = dict(f["rect"])
        tr.last_seen = t
        tr.hold_until = t + p.hold_ms
        tr.max_hold_until = t + p.max_hold_ms
        tr.finding_id = f.get("findingId")
        tr.cut = False
        tr.parked_until = None
        confirmed = tr.layer == 1 or tr.sightings >= p.confirm_n
        tr.state = "confirmed" if confirmed else "tentative"

    def _best(self, f: dict, used: set[int], min_pct: int) -> _T | None:
        best = None
        best_key = None
        for tr in self.tracks:
            if tr.track_id in used or tr.concept_id != f["conceptId"]:
                continue
            v = iou_pct(tr.rect, f["rect"])
            if v < min_pct:
                continue
            key = (-v, tr.track_id)
            if best_key is None or key < best_key:
                best, best_key = tr, key
        return best

    def on_findings(self, findings: list[dict], t_ms: int) -> None:
        def key(f: dict) -> tuple:
            r = f["rect"]
            return (
                f["layer"],
                f["conceptId"],
                r["y"],
                r["x"],
                r["w"],
                r["h"],
                f.get("findingId", ""),
            )

        used: set[int] = set()
        for f in sorted((f for f in findings if f["decision"] == "hide"), key=key):
            tr = self._best(f, used, self.p.iou_hide_pct)
            if tr is None:
                tr = _T(self.next_id, f, t_ms)
                self.next_id += 1
                self.tracks.append(tr)
            used.add(tr.track_id)
            self._sight(tr, f, t_ms)
        for f in sorted((f for f in findings if f["decision"] == "nearMiss"), key=key):
            tr = self._best(f, used, self.p.iou_keep_pct)
            if tr is not None:
                used.add(tr.track_id)
                tr.hold_until = t_ms + self.p.hold_ms

    def on_scene_cut(self, t_ms: int) -> None:
        for tr in self.tracks:
            tr.cut = True

    def on_app_change(self, t_ms: int) -> None:
        self.tracks = []

    def on_screen_off(self, t_ms: int) -> None:
        self.tracks = []

    def peek(self, track_id: int, t_ms: int) -> bool:
        for tr in self.tracks:
            if tr.track_id == track_id:
                if tr.layer == 2 and tr.state == "confirmed":
                    tr.peeked = True
                    return True
                return False
        return False

    def _on_screen(self, r: dict) -> bool:
        return _inter(r, {"x": 0, "y": 0, "w": self.w, "h": self.h}) > 0

    def tick(self, t_ms: int, own_covers: list[dict]) -> list[dict]:
        p = self.p
        keep: list[_T] = []
        for tr in sorted(self.tracks, key=lambda x: x.track_id):
            if not self._on_screen(tr.rect):
                if tr.state != "parked":
                    tr.prev_state = tr.state
                    tr.state = "parked"
                    tr.parked_until = t_ms + p.park_ms
                if tr.parked_until is not None and t_ms >= tr.parked_until:
                    continue
                keep.append(tr)
                continue
            if tr.state == "parked":
                tr.state = tr.prev_state
                tr.parked_until = None
                tr.hold_until = max(tr.hold_until, t_ms + p.hold_ms)
            tr.pct = covered_pct(tr.rect, own_covers)
            if t_ms > tr.hold_until:
                alive = (
                    self.rule
                    and tr.pct >= p.self_capture_pct
                    and not tr.cut
                    and t_ms < tr.max_hold_until
                )
                if not alive:
                    continue
            keep.append(tr)
        self.tracks = keep
        out = []
        for tr in keep:
            d = {
                "contractVersion": "1.0",
                "trackId": tr.track_id,
                "conceptId": tr.concept_id,
                "layer": tr.layer,
                "rect": dict(tr.rect),
                "state": tr.state,
                "sightings": tr.sightings,
                "firstSeenMs": tr.first_seen,
                "lastSeenMs": tr.last_seen,
                "holdUntilMs": tr.hold_until,
                "maxHoldUntilMs": tr.max_hold_until,
                "selfCaptureFraction": _fraction(tr.pct),
                "peeked": tr.peeked,
                "scope": tr.scope,
            }
            if tr.parked_until is not None:
                d["parkedUntilMs"] = tr.parked_until
            if tr.finding_id is not None:
                d["lastFindingId"] = tr.finding_id
            out.append(d)
        return out
