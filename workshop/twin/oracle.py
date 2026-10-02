"""Oracle detector (DV-1): findings built from the synthetic per-frame truth, with seeded noise."""

from __future__ import annotations

import json
import random
from dataclasses import dataclass
from pathlib import Path

from workshop.twin.tracker import covered_pct

DEFAULT_CONCEPTS = {"cats": 2, "spiders": 1}
SCREEN_W, SCREEN_H = 720, 1600


@dataclass(frozen=True)
class OracleParams:
    miss_pct: int = 3
    near_pct: int = 3
    jitter_px: int = 4
    fp_per_100_looks: int = 2
    occlude_pct: int = 50
    latency_ms: int = 100
    seed: int = 0


def _clip(r: dict, w: int = SCREEN_W, h: int = SCREEN_H) -> dict | None:
    x0, y0 = max(0, r["x"]), max(0, r["y"])
    x1, y1 = min(w, r["x"] + r["w"]), min(h, r["y"] + r["h"])
    if x1 <= x0 or y1 <= y0:
        return None
    return {"x": x0, "y": y0, "w": x1 - x0, "h": y1 - y0}


def _inter_area(a: dict, b: dict) -> int:
    c = _clip(a, 10**6, 10**6)
    if c is None:
        return 0
    x0, y0 = max(c["x"], b["x"]), max(c["y"], b["y"])
    x1, y1 = min(c["x"] + c["w"], b["x"] + b["w"]), min(c["y"] + c["h"], b["y"] + b["h"])
    return max(0, x1 - x0) * max(0, y1 - y0)


def load_truth(path: Path) -> dict[int, dict]:
    rows = {}
    for line in Path(path).read_text(encoding="utf-8").splitlines():
        if line.strip():
            r = json.loads(line)
            rows[r["i"]] = r
    return rows


def full_sizes(truth: dict[int, dict]) -> dict[str, tuple[int, int]]:
    """Largest (w, h) each key ever has: truth rects are clipped at the screen edge."""
    out: dict[str, tuple[int, int]] = {}
    for row in truth.values():
        for b in row["boxes"]:
            w, h = b["rect"]["w"], b["rect"]["h"]
            ow, oh = out.get(b["key"], (0, 0))
            out[b["key"]] = (max(w, ow), max(h, oh))
    return out


class OracleDetector:
    def __init__(self, truth_path: Path, concepts=DEFAULT_CONCEPTS, p: OracleParams | None = None):
        self.truth = load_truth(truth_path)
        self.sizes = full_sizes(self.truth)
        self.concepts = dict(concepts)
        self.p = p or OracleParams()

    def detect(self, frame: dict, look_rect: dict, look_id: int) -> list[dict]:
        p = self.p
        row = self.truth.get(frame["frameId"], {"boxes": []})
        own = frame.get("ownOverlay", [])
        out: list[dict] = []
        k = 0
        for b in sorted(row["boxes"], key=lambda b: b["key"]):
            cid = b["conceptId"]
            if cid not in self.concepts:
                continue
            r = b["rect"]
            fw, fh = self.sizes[b["key"]]
            if _inter_area(r, look_rect) * 2 < fw * fh:
                continue
            if covered_pct(r, own) >= p.occlude_pct:
                continue
            rng = random.Random(f"{p.seed}:{frame['frameId']}:{b['key']}")
            u = rng.random() * 100
            decision = "hide"
            prob = 0.9
            if u < p.miss_pct:
                continue
            if u < p.miss_pct + p.near_pct:
                decision, prob = "nearMiss", 0.5
            j = p.jitter_px
            x0 = r["x"] + rng.randint(-j, j)
            y0 = r["y"] + rng.randint(-j, j)
            x1 = r["x"] + r["w"] + rng.randint(-j, j)
            y1 = r["y"] + r["h"] + rng.randint(-j, j)
            rect = {"x": x0, "y": y0, "w": max(1, x1 - x0), "h": max(1, y1 - y0)}
            out.append(self._finding(frame, look_id, k, cid, rect, decision, prob))
            k += 1
        rng = random.Random(f"{p.seed}:fp:{look_id}")
        if rng.random() * 100 < p.fp_per_100_looks:
            size = min(rng.randint(100, 250), look_rect["w"], look_rect["h"])
            x = look_rect["x"] + rng.randint(0, look_rect["w"] - size)
            y = look_rect["y"] + rng.randint(0, look_rect["h"] - size)
            rect = {"x": x, "y": y, "w": size, "h": size}
            out.append(self._finding(frame, look_id, k, "cats", rect, "hide", 0.9))
        return out

    def _finding(self, frame, look_id, k, cid, rect, decision, prob) -> dict:
        return {
            "contractVersion": "1.0",
            "findingId": f"o{look_id}-{k}",
            "lookId": look_id,
            "tMs": frame["tMs"],
            "frameId": frame["frameId"],
            "rect": rect,
            "conceptId": cid,
            "layer": self.concepts[cid],
            "lane": "finder",
            "decision": decision,
            "probability": prob,
            "scope": "object",
        }
