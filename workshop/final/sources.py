"""One loader per result source. Rows: (id, claim, value, status, conditions, source)."""

from __future__ import annotations

import json
from pathlib import Path

MEASURED = "measured"
PENDING = "PENDING-HUMAN"
DASH = "—"
MODES = ("light", "balanced", "strict")

Row = tuple[str, str, str, str, str, str]


def _load(root: Path, rel: str):
    p = root / rel
    if not p.is_file():
        return None
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None


def _get(d, *keys):
    for k in keys:
        if not isinstance(d, dict) or k not in d:
            return None
        d = d[k]
    return d


def _row(rid: str, claim: str, value, cond: str, src: str, fmt: str = "{}") -> Row:
    if value is None:
        return (rid, claim, DASH, PENDING, cond, src)
    return (rid, claim, fmt.format(value), MEASURED, cond, src)


def ch1(root: Path) -> list[Row]:
    src = "data/ch1/results-public.json"
    d = _load(root, src)
    cond = "public sample, not the frozen set; laptop, balanced mode"
    out = []
    for i, c in enumerate(("cats", "spiders")):
        base = ("test", "balanced", c)
        r = _get(d, *base, "recall")
        f = _get(d, *base, "cleanFalseCover")
        out.append(_row(f"F-{3 + 2 * i:02d}", f"{c} recall", r, cond, src, "{:.2f}"))
        out.append(_row(f"F-{4 + 2 * i:02d}", f"{c} clean false covers", f, cond, src, "{:.2f}"))
    return out


def ch2(root: Path) -> list[Row]:
    src = "data/ch2/motion-eval/scores.json"
    d = _load(root, src)
    a = _get(d, "modes", "balanced", "aggregate") or {}
    c = "laptop replay of recorded sessions (synthetic test sessions), balanced mode"
    p95 = a.get("ttc_p95_ms")
    if p95 is not None and p95 >= 1e9:
        p95 = None  # sentinel: some appearances never covered
    return [
        _row("F-07", "time to cover p95 ms (laptop replay)", p95, c, src),
        _row("F-08", "frames analysed %", a.get("analysed_pct"), c, src, "{:.1f}"),
        _row("F-09", "wrong covers per minute", a.get("wrong_per_min"), c, src, "{:.1f}"),
    ]


def ch3(root: Path) -> list[Row]:
    src = "docs/reports/ch3-profile.md"
    cond = "profile table values are fixtures, not a phone run"
    return [
        ("F-10", "AI latency per model on the NPU", DASH, PENDING, cond, src),
        ("F-11", "NPU share per model", DASH, PENDING, cond, src),
    ]


def packs(root: Path) -> list[Row]:
    out = []
    d = root / "workshop/packs/reports"
    files = sorted(d.glob("*.json")) if d.is_dir() else []
    n = 20
    for f in files[:5]:
        rel = f"workshop/packs/reports/{f.name}"
        j = _load(root, rel) or {}
        cond = f"{j.get('testSet', 'unknown set')}; status {j.get('status', 'unknown')}"
        out.append(_row(f"F-{n:02d}", f"{f.stem} recall", j.get("recall"), cond, rel, "{:.2f}"))
        rate = j.get("cleanFalseCoverRate")
        claim = f"{f.stem} clean false covers"
        out.append(_row(f"F-{n + 1:02d}", claim, rate, cond, rel, "{:.2f}"))
        n += 2
    if not out:
        out.append(("F-20", "pack results", DASH, PENDING, "no pack reports", "workshop/packs"))
    return out


def phone(root: Path) -> list[Row]:
    """F-01 is time to cover p95 and F-02 is Balanced battery per hour (cited by the demo)."""
    src = "data/final/phone-metrics.json"
    d = _load(root, src)
    cond = _get(d, "conditions") or "phone run"
    items = [
        ("F-01", "time to cover p95 ms (phone)", _get(d, "timeToCoverMsP95")),
        ("F-31", "looks per second", _get(d, "looksPerSecond")),
        ("F-32", "AI ms per look p95", _get(d, "aiMsPerLookP95")),
        ("F-33", "memory MB peak", _get(d, "memoryMbPeak")),
        ("F-34", "battery % per hour (light)", _get(d, "batteryPctPerHour", "light")),
        ("F-02", "battery % per hour (balanced)", _get(d, "batteryPctPerHour", "balanced")),
        ("F-36", "battery % per hour (strict)", _get(d, "batteryPctPerHour", "strict")),
    ]
    return [_row(i, c, v, cond, src) for i, c, v in items]


AREAS = [
    ("Phone", phone),
    ("Chapter one: seeing", ch1),
    ("Chapter two: motion", ch2),
    ("Chapter three: on-device profile", ch3),
    ("Packs", packs),
]
