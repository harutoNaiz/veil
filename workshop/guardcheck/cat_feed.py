"""Cat-feed checker: were cat/spider items covered, and clean/lookalike items left alone?

Reads Guard debug.jsonl (lines with kind "plan", masks inside) and the Test Feed feedlog.jsonl.
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass, field

GRACE_MS = 300
MUST_COVER = {"cat", "spider"}
MUST_LEAVE = {"clean", "lookalike"}
SAMPLES = 24


def _jsonl(text: str) -> list[dict]:
    out = []
    for line in text.splitlines():
        try:
            entry = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(entry, dict):
            out.append(entry)
    return out


def parse_plans(text: str) -> list[tuple[int, list[dict]]]:
    """(tMs, mask rects) per plan line, sorted by time. Accepts a flat or a nested "plan" record."""
    plans = []
    for rec in _jsonl(text):
        body = rec.get("plan") if isinstance(rec.get("plan"), dict) else rec
        if rec.get("kind") != "plan" and "masks" not in body:
            continue
        rects = [m["rect"] for m in body.get("masks", []) if isinstance(m.get("rect"), dict)]
        plans.append((int(body.get("tMs", rec.get("tMs", 0))), rects))
    return sorted(plans, key=lambda p: p[0])


def covered_pct(rect: dict, covers: list[dict]) -> float:
    """Percent of `rect` inside the union of `covers` (grid sampling)."""
    hit = 0
    for i in range(SAMPLES):
        y = rect["y"] + (i + 0.5) * rect["h"] / SAMPLES
        for j in range(SAMPLES):
            x = rect["x"] + (j + 0.5) * rect["w"] / SAMPLES
            if any(c["x"] <= x < c["x"] + c["w"] and c["y"] <= y < c["y"] + c["h"] for c in covers):
                hit += 1
    return 100.0 * hit / (SAMPLES * SAMPLES)


@dataclass
class Report:
    problems: list[str] = field(default_factory=list)
    checked: int = 0

    @property
    def clean(self) -> bool:
        return not self.problems and self.checked > 0


def check(debug_text: str, feed_text: str) -> Report:
    plans = parse_plans(debug_text)
    report = Report()
    first_seen: dict[str, int] = {}
    for fr in _jsonl(feed_text):
        if fr.get("type") != "frame":
            continue
        t = int(fr.get("tMs", 0))
        plan = [p for p in plans if p[0] <= t]
        covers = plan[-1][1] if plan else []
        for item in fr.get("visible") or []:
            iid, kind = item.get("itemId"), item.get("kind")
            first_seen.setdefault(iid, t)
            if t - first_seen[iid] < GRACE_MS or kind not in MUST_COVER | MUST_LEAVE:
                continue
            pct = covered_pct(item["rect"], covers)
            report.checked += 1
            if kind in MUST_COVER and pct < 80:
                report.problems.append(f"t={t} {iid} ({kind}) only {pct:.0f}% covered (need 80)")
            elif kind in MUST_LEAVE and pct >= 10:
                report.problems.append(f"t={t} {iid} ({kind}) {pct:.0f}% covered (max 10)")
    if report.checked == 0:
        report.problems.append("no checkable frames")
    return report


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("debug_jsonl")
    ap.add_argument("feedlog_jsonl")
    args = ap.parse_args(argv)
    with (
        open(args.debug_jsonl, encoding="utf-8") as f1,
        open(args.feedlog_jsonl, encoding="utf-8") as f2,
    ):
        rep = check(f1.read(), f2.read())
    print(f"cat_feed: {rep.checked} item checks, {len(rep.problems)} problems")
    for p in rep.problems[:50]:
        print("  " + p)
    print("CAT FEED: " + ("CLEAN" if rep.clean else "FAIL"))
    return 0 if rep.clean else 1


if __name__ == "__main__":
    sys.exit(main())
