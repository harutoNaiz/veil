"""Parse a raw AI Hub profile into per-unit layer counts and off-chip layers."""

from __future__ import annotations

_DYNAMIC_HINTS = ("shape", "nonzero", "dynamic")


def _cause(name: str, op: str) -> str:
    text = f"{name} {op}".lower()
    if any(h in text for h in _DYNAMIC_HINTS):
        return "dynamic shape"
    return f"unsupported op {op}" if op else "unknown"


def parse(profile: dict) -> dict:
    layers = {"npu": 0, "gpu": 0, "cpu": 0}
    off: list[dict] = []
    for item in profile.get("execution_detail", []):
        unit = str(item.get("compute_unit", "")).upper()
        key = unit.lower()
        if key not in layers:
            continue
        layers[key] += 1
        if key != "npu":
            name, op = item.get("name", ""), item.get("type", "")
            off.append({"layer": name, "op": op, "unit": unit, "cause": _cause(name, op)})
    total = sum(layers.values())
    return {
        "layers": layers,
        "npuShare": layers["npu"] / total if total else 0.0,
        "offChip": off,
    }
