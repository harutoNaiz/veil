"""Chapter 5 report writer: python -m workshop.perf.report --evidence DIR --out FILE."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from workshop.perf.schema import Section, read_section

GATE = (
    "a cat in a live Instagram feed is covered within 0.3 s (95% of the time) in Balanced mode",
    "no visible stutter in Instagram with the Guard on",
    "memory under 3 GB",
    "15% or less extra battery over 30 minutes of Instagram at fixed brightness",
)
FALLBACK = "Light defaults, smaller models, fewer looks per second, UI-layout pieces plus tiles"


def _load(d: Path, name: str) -> Section:
    p = d / f"{name}.json"
    return read_section(p) if p.exists() else Section(name)


def _table(sec: Section) -> list[str]:
    if not sec.rows:
        return ["PENDING-HUMAN: no measurements yet.", ""]
    out = ["| AC | metric | value | threshold | ok |", "| --- | --- | --- | --- | --- |"]
    for r in sec.rows:
        ok = "PENDING-HUMAN" if r.ok is None else ("PASS" if r.ok else "FAIL")
        v = "PENDING-HUMAN" if r.value is None else r.value
        out.append(f"| {r.ac} | {r.metric} | {v} | {r.threshold} | {ok} |")
    out += [f"- {n}" for n in sec.notes] + [""]
    return out


def build(evidence: Path) -> str:
    secs = {n: _load(evidence, n) for n in ("latency", "smooth", "battery")}
    st = [s.status for s in secs.values()]
    if "FAIL" in st:
        gate = f"FAIL → apply Chapter 5 fallback ({FALLBACK})"
    elif all(s == "PASS" for s in st):
        gate = "PASS"
    else:
        gate = "PENDING-HUMAN"
    lines = ["# Chapter 5 report: Guard real-world performance", "", "## Summary", ""]
    lines += [f"- {n}: {s.status}" for n, s in secs.items()] + [""]
    lines += ["## Latency (time to cover) and stage breakdown", ""] + _table(secs["latency"])
    lines += ["## Smoothness, memory, heat, kills", ""] + _table(secs["smooth"])
    lines += ["## Battery per mode", ""] + _table(secs["battery"])
    lines += ["## Chapter 5 gate", ""] + [f"- {g}" for g in GATE] + ["", f"Gate: {gate}", ""]
    lines += [
        "## Deferred / human",
        "",
        "- Live on-phone numbers (5.2-W wiring), battery batch (~3.5 h), heat step, gate decision.",
        "- Run `tools\\verify\\pt-5.3.ps1` with a phone.",
        "",
    ]
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="workshop.perf.report")
    p.add_argument("--evidence", required=True)
    p.add_argument("--out", required=True)
    a = p.parse_args(argv)
    out = Path(a.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(build(Path(a.evidence)), encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
