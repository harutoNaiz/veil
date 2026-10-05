"""Parse `dumpsys gfxinfo` frame counters."""

from __future__ import annotations

import re


def _num(text: str, key: str) -> int:
    m = re.search(re.escape(key) + r"\s*:?\s*(\d+)", text)
    return int(m.group(1)) if m else 0


def parse_gfxinfo(text: str) -> dict:
    total = _num(text, "Total frames rendered")
    janky = _num(text, "Janky frames")
    return {"total": total, "janky": janky, "rate_pct": 100.0 * janky / total if total else 0.0}


def compare(on: dict, off: dict) -> float:
    return abs(on["rate_pct"] - off["rate_pct"])
