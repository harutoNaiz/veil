"""2.2.2 burst scheduler tests (AC-2.2-03, AC-2.2-07)."""

import ast
import random
from dataclasses import replace
from pathlib import Path

from workshop.twin.scheduler import MODES, SchedState, Tick, step

SRC = Path(__file__).resolve().parents[1] / "scheduler.py"
B = MODES["balanced"]


def tk(i, **kw):
    return Tick(t_ms=i * 1000 // 30, frame_id=i, screen_w=720, screen_h=1600, **kw)


def run(n, mk, p=B, state=None):
    s = state or SchedState()
    out = []
    for i in range(n):
        s, r = step(s, mk(i), p)
        out.append((s, r))
    return out


def test_first_tick_is_checkup():
    _, r = step(SchedState(), tk(0), B)
    assert r and r.why == "checkup" and r.deadline_ms == r.t_ms + 200


def test_screen_off_idle_then_on_appchange_and_skip_pkg():
    s, _ = step(SchedState(), tk(0, screen_on=False, changed_tiles=5), B)
    assert s.phase == "idle"
    s, r = step(s, tk(1, changed_tiles=5), B)
    assert r is None and s.phase == "idle"
    s, r = step(s, tk(2, screen_on=True), B)
    assert s.phase == "watching" and r and r.why == "appChange"
    p = replace(B, skip_packages=("com.x",))
    s, r = step(SchedState(), tk(0, package="com.x", changed_tiles=3), p)
    assert s.phase == "idle" and r is None


def test_hot_doubles_rate_then_expires():
    st = SchedState(last_checkup_ms=0)

    def times(hot):
        res = run(60, lambda i: tk(i, changed_tiles=1, hot_hint=hot), state=st)
        return [r.t_ms for _, r in res if r]

    th, tw = times(True), times(False)
    gh = [b - a for a, b in zip(th, th[1:], strict=False)]
    gw = [b - a for a, b in zip(tw, tw[1:], strict=False)]
    assert min(gh) >= 167 and max(gh) < 250
    assert min(gw) >= 334
    res = run(150, lambda i: tk(i, hot_hint=i == 0))
    assert res[10][0].phase == "hot" and res[149][0].phase == "watching"


def test_throttle_and_back():
    res = run(20, lambda i: tk(i, throttle=i < 10))
    assert res[5][0].phase == "throttled" and res[15][0].phase == "watching"


def test_priority_and_busy_pending():
    s = SchedState(last_checkup_ms=0)
    s, r = step(s, tk(1, scene_cut=True, window_changed=True, scroll_dy=40, busy=True), B)
    assert r is None and s.skipped == 1 and s.last_reason == "busy" and s.pending == "sceneCut"
    s, r = step(s, tk(2), B)
    assert r and r.why == "sceneCut" and s.pending is None


def test_checkup_counts_static_60s():
    for name, exp in (("light", 6), ("balanced", 12), ("strict", 30)):
        n = sum(1 for _, r in run(1800, lambda i: tk(i), p=MODES[name]) if r)
        assert abs(n - exp) <= 1, (name, n)


def test_throttled_rate_ac_2_2_07():
    for p in MODES.values():
        res = run(300, lambda i: tk(i, changed_tiles=4, scroll_dy=30, throttle=True), p=p)
        n = sum(1 for _, r in res if r)
        assert n / 10 <= 0.5 * p.rate + 1e-9, (p, n)


def _random_seq(rng):
    t = 0
    seq = []
    for i in range(50):
        t += rng.randint(1, 400)
        seq.append(
            Tick(
                t,
                i,
                720,
                1600,
                changed_tiles=rng.randint(0, 3),
                scene_cut=rng.random() < 0.1,
                revealed_rect={"x": 0, "y": 5, "w": 9, "h": 9} if rng.random() < 0.1 else None,
                scroll_dy=rng.choice([0, 0, 25, -50]),
                window_changed=rng.random() < 0.05,
                screen_on=rng.choice([None, None, None, False, True]),
                busy=rng.random() < 0.3,
                hot_hint=rng.random() < 0.1,
                throttle=rng.random() < 0.2,
            )
        )
    return seq


def _go(seq):
    s, out = SchedState(), []
    for tick in seq:
        s, r = step(s, tick, B)
        assert s.pending is None or isinstance(s.pending, str)
        out.append((s, r))
    return out


def test_pure_and_deterministic_ac_2_2_03():
    rng = random.Random(7)
    seqs = [_random_seq(rng) for _ in range(1000)]
    assert [_go(q) for q in seqs] == [_go(q) for q in seqs]
    bad = {"time", "datetime", "random", "os", "uuid", "secrets"}
    for n in ast.walk(ast.parse(SRC.read_text())):
        if isinstance(n, ast.Import):
            assert not bad & {a.name.split(".")[0] for a in n.names}
        if isinstance(n, ast.ImportFrom):
            assert (n.module or "").split(".")[0] not in bad
        if isinstance(n, ast.Attribute):
            assert n.attr != "random"
