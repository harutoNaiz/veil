"""Reads the log written by the Test Feed app (guard/testfeed/README.md describes the format)."""

from __future__ import annotations

import json
from dataclasses import dataclass


@dataclass
class FeedSummary:
    frames: int
    max_scroll_y: int
    first_visible_start: str | None
    first_visible_end: str | None
    taps: int
    has_session: bool


def _first_visible(frame: dict) -> str | None:
    visible = frame.get("visible") or []
    return visible[0].get("itemId") if visible else None


def parse_feed_log(text: str) -> FeedSummary:
    """Summarise a feedlog.jsonl. Lines that are not JSON objects (e.g. a cut-off one) are skipped.

    first_visible_start / first_visible_end: the first visible item of the first and last frames.
    """
    frames = taps = 0
    max_scroll = 0
    start: str | None = None
    end: str | None = None
    has_session = False
    for line in text.splitlines():
        try:
            entry = json.loads(line)
        except json.JSONDecodeError:
            continue
        if not isinstance(entry, dict):
            continue
        kind = entry.get("type")
        if kind == "session":
            has_session = True
        elif kind == "tap":
            taps += 1
        elif kind == "frame":
            first = _first_visible(entry)
            if frames == 0:
                start = first
            end = first
            frames += 1
            max_scroll = max(max_scroll, int(entry.get("scrollY", 0)))
    return FeedSummary(frames, max_scroll, start, end, taps, has_session)


def scroll_check(s: FeedSummary, screen_height_px: int) -> tuple[bool, str]:
    """Pass iff the feed scrolled by at least 80 % of the screen height and the top item changed."""
    problems = []
    if not s.has_session:
        problems.append("no session line")
    if s.frames < 10:
        problems.append(f"only {s.frames} frames (need 10)")
    if s.max_scroll_y < 0.8 * screen_height_px:
        problems.append(f"max scrollY {s.max_scroll_y} < 80% of screen height {screen_height_px}")
    if s.first_visible_end == s.first_visible_start:
        problems.append(f"first visible item never changed ({s.first_visible_start})")
    if problems:
        return False, "; ".join(problems)
    return True, (
        f"{s.frames} frames, max scrollY {s.max_scroll_y} px, first visible "
        f"{s.first_visible_start} -> {s.first_visible_end}, {s.taps} taps"
    )
