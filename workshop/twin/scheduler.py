"""Burst scheduler (2.2.2): pure (state, tick) -> (state, look request | None). Never queues."""

from __future__ import annotations

from dataclasses import dataclass, replace

STATES = ("idle", "watching", "hot", "throttled")
IMMEDIATE = ("sceneCut", "appChange", "swipe", "revealedStrip")  # highest priority first
_NEVER = -(10**9)


@dataclass(frozen=True)
class ModeParams:
    rate: int
    checkup_ms: int
    min_immediate_gap_ms: int
    hot_ms: int = 3000
    hot_rate_mul: int = 2
    throttle_div: int = 2
    burst_gap_ms: int = 150
    deadline_ms: int = 200
    skip_packages: tuple[str, ...] = ()


MODES = {
    "light": ModeParams(1, 10000, 300, deadline_ms=300),
    "balanced": ModeParams(3, 5000, 150),
    "strict": ModeParams(8, 2000, 66, deadline_ms=100),
}


@dataclass(frozen=True)
class Tick:
    t_ms: int
    frame_id: int
    screen_w: int
    screen_h: int
    changed_tiles: int = 0
    scene_cut: bool = False
    revealed_rect: dict | None = None
    changed_rect: dict | None = None
    scroll_dy: int = 0
    window_changed: bool = False
    package: str | None = None
    screen_on: bool | None = None
    busy: bool = False
    hot_hint: bool = False
    throttle: bool = False


@dataclass(frozen=True)
class SchedState:
    phase: str = "watching"
    screen_on: bool = True
    package: str = ""
    last_look_ms: int = _NEVER
    last_immediate_ms: int = _NEVER
    last_checkup_ms: int = _NEVER
    last_scroll_ms: int = _NEVER
    hot_until_ms: int = _NEVER
    pending: str | None = None
    skipped: int = 0
    looks: int = 0
    last_reason: str = "none"


@dataclass(frozen=True)
class LookRequest:
    why: str
    rect: dict
    deadline_ms: int
    frame_id: int
    t_ms: int


def _cdiv(a: int, b: int) -> int:
    return -(-a // b)


def _better(a: str | None, b: str) -> str:
    if a is None or IMMEDIATE.index(b) < IMMEDIATE.index(a):
        return b
    return a


def step(state: SchedState, tick: Tick, p: ModeParams) -> tuple[SchedState, LookRequest | None]:
    t = tick.t_ms
    screen_on = state.screen_on if tick.screen_on is None else tick.screen_on
    package = state.package if tick.package is None else tick.package
    window_changed = tick.window_changed or tick.screen_on is True
    scrolled = tick.scroll_dy != 0
    last_scroll = t if scrolled else state.last_scroll_ms
    hot_until = state.hot_until_ms

    # (1) phase
    if not screen_on or package in p.skip_packages:
        ns = replace(
            state,
            phase="idle",
            screen_on=screen_on,
            package=package,
            pending=None,
            last_scroll_ms=last_scroll,
            last_reason="none",
        )
        return ns, None
    if tick.throttle:
        phase = "throttled"
    elif tick.hot_hint or t < hot_until:
        phase = "hot"
        if tick.hot_hint:
            hot_until = t + p.hot_ms
    else:
        phase = "watching"

    # (2) new immediate reasons, merged into the single pending slot
    pending = state.pending
    if tick.scene_cut:
        pending = _better(pending, "sceneCut")
    if window_changed:
        pending = _better(pending, "appChange")
    if scrolled and t - state.last_scroll_ms > p.burst_gap_ms:
        pending = _better(pending, "swipe")
    if tick.revealed_rect:
        pending = _better(pending, "revealedStrip")

    # (3) gaps
    if phase == "hot":
        gap = _cdiv(1000, p.rate * p.hot_rate_mul)
    elif phase == "throttled":
        gap = _cdiv(1000 * p.throttle_div, p.rate)
    else:
        gap = _cdiv(1000, p.rate)
    checkup_period = p.checkup_ms * (p.throttle_div if phase == "throttled" else 1)

    # (4) what do we want
    want: str | None = None
    if pending is not None and t - state.last_immediate_ms >= p.min_immediate_gap_ms:
        want = pending
    elif t - state.last_checkup_ms >= checkup_period:
        want = "checkup"
    elif tick.changed_tiles > 0 and t - state.last_look_ms >= gap:
        want = "periodic"
    if want is not None and phase == "throttled" and t - state.last_look_ms < gap:
        want = None

    base = replace(
        state,
        phase=phase,
        screen_on=screen_on,
        package=package,
        pending=pending,
        last_scroll_ms=last_scroll,
        hot_until_ms=hot_until,
        last_reason="none",
    )
    if want is None:
        return base, None
    # (5) busy: never queue, keep the pending reason
    if tick.busy:
        return replace(base, skipped=state.skipped + 1, last_reason="busy"), None

    # (6) emit
    full = {"x": 0, "y": 0, "w": tick.screen_w, "h": tick.screen_h}
    if want == "revealedStrip":
        rect = tick.revealed_rect or full
    elif want == "periodic":
        rect = tick.changed_rect or full
    else:
        rect = full
    ns = replace(
        base,
        pending=None,
        looks=state.looks + 1,
        last_look_ms=t,
        last_immediate_ms=t if want in IMMEDIATE else state.last_immediate_ms,
        last_checkup_ms=t if rect == full else state.last_checkup_ms,
        last_reason=want,
    )
    return ns, LookRequest(want, dict(rect), t + p.deadline_ms, tick.frame_id, t)
