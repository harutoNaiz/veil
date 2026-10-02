"""Stand-ins for change.detect / scheduler.step, used only while the real modules were missing."""

from __future__ import annotations

from workshop.twin.change import ChangeResult
from workshop.twin.scheduler import LookRequest


def detect_stub(cur, ref, dy_rows, p=None) -> ChangeResult:
    return ChangeResult((0,) * 32, 0, False, 0, None, None, dy_rows)


def step_stub(state, tick, p):
    """A full-screen periodic request every 10th frame."""
    if tick.frame_id % 10 != 0:
        return state, None
    rect = {"x": 0, "y": 0, "w": tick.screen_w, "h": tick.screen_h}
    return state, LookRequest("periodic", rect, tick.t_ms + 200, tick.frame_id, tick.t_ms)
