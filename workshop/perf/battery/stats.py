"""Parse dumpsys battery output and judge the battery A/B runs."""

from __future__ import annotations

import re

from workshop.perf.schema import Row, Section

AC5_THRESHOLD = (
    "≤ 15% extra over 30 minutes of Instagram in Balanced; "
    "A/B run twice with the same brightness, starting charge and network"
)
AC6_THRESHOLD = "Light, Strict and a 15-minute video session measured and recorded"


def parse_level(text: str) -> int:
    m = re.search(r"^\s*level:\s*(\d+)", text, re.MULTILINE)
    if not m:
        raise ValueError("no battery level")
    return int(m.group(1))


def parse_uid(package_dump: str) -> str | None:
    """`dumpsys package` userId=10123 -> batterystats uid token u0a123."""
    m = re.search(r"userId=(\d+)", package_dump)
    if not m:
        return None
    uid = int(m.group(1))
    return f"u{uid // 100000}a{uid % 100000 - 10000}"


def parse_uid_mah(text: str, pkg: str, uid: str | None = None) -> float | None:
    """Estimated power use (mAh) of a UID line, matched by uid token (u0a123) or package."""
    for ln in text.splitlines():
        m = re.match(r"\s*Uid\s+(\S+?):\s*([\d.]+)", ln)
        if m and (m.group(1) == uid or pkg in ln):
            return float(m.group(2))
    return None


def _drop(r: dict) -> int:
    return r["startLevel"] - r["endLevel"]


def battery_table(runs: list[dict]) -> list[dict]:
    return [
        {"label": r["label"], "mode": r["mode"], "drop_pct": _drop(r), "guard_mah": r["guardMah"]}
        for r in runs
    ]


def _pairs(runs: list[dict]) -> list[tuple[dict, dict] | None]:
    by = {r["label"]: r for r in runs}
    return [
        (by[f"{p}-off"], by[f"{p}-on"]) if f"{p}-off" in by and f"{p}-on" in by else None
        for p in "AB"
    ]


def _same_conditions(off: dict, on: dict) -> bool:
    return (
        off["brightness"] == on["brightness"]
        and abs(off["startLevel"] - on["startLevel"]) <= 2
        and off["network"] == on["network"]
    )


def extra_pct(runs: list[dict]) -> float:
    vals = []
    for pair in _pairs(runs):
        if pair and _drop(pair[0]) > 0:
            vals.append((_drop(pair[1]) - _drop(pair[0])) / _drop(pair[0]) * 100)
    if not vals:
        raise ValueError("no complete A/B pair")
    return sum(vals) / len(vals)


def build_section(runs: list[dict]) -> Section:
    sec = Section("battery")
    pairs = _pairs(runs)
    if not all(pairs):
        sec.rows.append(Row("AC-5.3-05", "extra_pct", None, AC5_THRESHOLD, None))
    elif not all(_same_conditions(*p) for p in pairs if p):
        sec.rows.append(Row("AC-5.3-05", "extra_pct", "conditions differ", AC5_THRESHOLD, False))
        sec.notes.append("conditions differ")
    else:
        pct = round(extra_pct(runs), 2)
        sec.rows.append(Row("AC-5.3-05", "extra_pct", pct, AC5_THRESHOLD, pct <= 15))
    have = {r["label"] for r in runs}
    need = {"light", "strict", "video15"}
    sec.rows.append(
        Row(
            "AC-5.3-06",
            "recorded",
            ",".join(sorted(have & need)) or None,
            AC6_THRESHOLD,
            True if need <= have else None,
        )
    )
    return sec.finish()
