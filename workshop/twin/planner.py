"""Mask planner (2.3.2): tracks -> MaskPlan v1.0 dicts. Integer geometry only."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class PlanParams:
    pad_pct: int
    drop_short_px: int
    layer2_style: str
    max_masks: int = 24


PLAN_MODES = {
    "light": PlanParams(4, 32, "blur"),
    "balanced": PlanParams(6, 0, "blur"),
    "strict": PlanParams(10, 0, "solid"),
}


def pad(rect: dict, pct: int, screen_w: int, screen_h: int) -> dict | None:
    p = min(rect["w"], rect["h"]) * pct // 100
    x0 = max(0, rect["x"] - p)
    y0 = max(0, rect["y"] - p)
    x1 = min(screen_w, rect["x"] + rect["w"] + p)
    y1 = min(screen_h, rect["y"] + rect["h"] + p)
    if x1 <= x0 or y1 <= y0:
        return None
    return {"x": x0, "y": y0, "w": x1 - x0, "h": y1 - y0}


def _meets(a: dict, b: dict) -> bool:
    return (
        a["x"] < b["x"] + b["w"]
        and b["x"] < a["x"] + a["w"]
        and a["y"] < b["y"] + b["h"]
        and b["y"] < a["y"] + a["h"]
    )


def _union(a: dict, b: dict) -> dict:
    x0 = min(a["x"], b["x"])
    y0 = min(a["y"], b["y"])
    x1 = max(a["x"] + a["w"], b["x"] + b["w"])
    y1 = max(a["y"] + a["h"], b["y"] + b["h"])
    return {"x": x0, "y": y0, "w": x1 - x0, "h": y1 - y0}


def _join(a: dict, b: dict) -> dict:
    return {
        "layer": a["layer"],
        "rect": _union(a["rect"], b["rect"]),
        "conceptIds": sorted(set(a["conceptIds"]) | set(b["conceptIds"])),
        "trackIds": sorted(set(a["trackIds"]) | set(b["trackIds"])),
    }


def _key(m: dict) -> tuple:
    r = m["rect"]
    return (m["layer"], r["y"], r["x"], r["w"], r["h"])


def merge(masks: list[dict]) -> list[dict]:
    """Merge same-layer masks whose rects intersect (area > 0) until stable."""
    cur = sorted((dict(m) for m in masks), key=_key)
    changed = True
    while changed:
        changed = False
        for i in range(len(cur)):
            for j in range(i + 1, len(cur)):
                if cur[i]["layer"] == cur[j]["layer"] and _meets(cur[i]["rect"], cur[j]["rect"]):
                    cur[i] = _join(cur[i], cur[j])
                    del cur[j]
                    changed = True
                    break
            if changed:
                break
    return sorted(cur, key=_key)


def _area(r: dict) -> int:
    return r["w"] * r["h"]


def _cap(masks: list[dict], limit: int) -> list[dict]:
    cur = list(masks)
    while len(cur) > limit:
        best = None
        for i in range(len(cur)):
            for j in range(i + 1, len(cur)):
                if cur[i]["layer"] != cur[j]["layer"]:
                    continue
                u = _area(_union(cur[i]["rect"], cur[j]["rect"]))
                cost = u - _area(cur[i]["rect"]) - _area(cur[j]["rect"])
                if best is None or cost < best[0]:
                    best = (cost, i, j)
        if best is None:
            break
        _, i, j = best
        cur[i] = _join(cur[i], cur[j])
        del cur[j]
        cur = merge(cur)
    return cur


def plan(
    tracks: list[dict],
    *,
    t_ms: int,
    frame_id: int,
    screen_w: int,
    screen_h: int,
    mode: str = "balanced",
    reason: str = "look",
    post_bounds: list[dict] | None = None,
    labels: bool = False,
    solid_only: bool = False,
    params: PlanParams | None = None,
) -> dict:
    p = params or PLAN_MODES[mode]
    raw: list[dict] = []
    for t in sorted(tracks, key=lambda t: t["trackId"]):
        if t["state"] != "confirmed" or t.get("peeked"):
            continue
        rect = t["rect"]
        if t["layer"] != 1 and min(rect["w"], rect["h"]) < p.drop_short_px:
            continue
        if t.get("scope") == "wholeElement" and post_bounds:
            cx = rect["x"] + rect["w"] // 2
            cy = rect["y"] + rect["h"] // 2
            for pb in post_bounds:
                if pb["x"] <= cx < pb["x"] + pb["w"] and pb["y"] <= cy < pb["y"] + pb["h"]:
                    rect = pb
                    break
        padded = pad(rect, p.pad_pct, screen_w, screen_h)
        if padded is None:
            continue
        raw.append(
            {
                "layer": t["layer"],
                "rect": padded,
                "conceptIds": [t["conceptId"]],
                "trackIds": [t["trackId"]],
            }
        )
    masks = _cap(merge(raw), p.max_masks)
    out = []
    for i, m in enumerate(masks, 1):
        layer = m["layer"]
        style = "solid" if layer == 1 else ("solid" if solid_only else p.layer2_style)
        mask = {
            "contractVersion": "1.0",
            "maskId": i,
            "rect": dict(m["rect"]),
            "style": style,
            "layer": layer,
            "peekable": layer != 1,
            "conceptIds": m["conceptIds"][:8],
            "trackIds": m["trackIds"][:32],
        }
        if labels:
            mask["label"] = ("Hidden · " + ", ".join(m["conceptIds"]))[:64]
        out.append(mask)
    return {
        "contractVersion": "1.0",
        "planId": frame_id,
        "tMs": t_ms,
        "screenWidth": screen_w,
        "screenHeight": screen_h,
        "rotation": 0,
        "masks": out,
        "basedOnFrameId": frame_id,
        "reason": reason,
    }
