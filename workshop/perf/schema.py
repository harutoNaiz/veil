"""Shared shapes for Phase 5.3.

Every *.json section file is
{"section": str, "status": "PASS"|"FAIL"|"PENDING", "rows": [Row...], "notes": [str]}.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path

STAGES = ("frame", "gate", "ai", "judge", "plan", "draw")  # kind=stage lines, in order
GUARD_PKG, FEED_PKG, IG_PKG = "com.veil.guard", "com.veil.testfeed", "com.instagram.android"


@dataclass
class Row:
    ac: str  # "AC-5.3-01" ...
    metric: str  # e.g. "p95_ms"
    value: float | str | None  # None -> PENDING
    threshold: str  # PLAN text, word for word
    ok: bool | None  # None -> PENDING


@dataclass
class Section:
    section: str  # "latency" | "smooth" | "battery"
    status: str = "PENDING"
    rows: list[Row] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)

    def finish(self) -> Section:
        oks = [r.ok for r in self.rows]
        self.status = "PENDING" if not oks or None in oks else ("PASS" if all(oks) else "FAIL")
        return self

    def write(self, path: Path) -> None:
        path.write_text(json.dumps(asdict(self), indent=1), encoding="utf-8")


def read_section(path: Path) -> Section:
    d = json.loads(path.read_text(encoding="utf-8"))
    return Section(d["section"], d["status"], [Row(**r) for r in d["rows"]], d["notes"])


def jsonl(path: Path) -> list[dict]:
    """Tolerant JSONL reader: skips blank / cut-off / non-object lines."""
    out = []
    for ln in path.read_text(encoding="utf-8").splitlines():
        try:
            o = json.loads(ln)
        except json.JSONDecodeError:
            continue
        if isinstance(o, dict):
            out.append(o)
    return out
