"""Build evidence/smooth.json from a run directory."""

from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

from workshop.perf.schema import Row, Section, jsonl
from workshop.perf.smooth import gfx
from workshop.perf.smooth.kill import judge
from workshop.perf.smooth.sample import throttle_cycle

PSS_MAX_KB = 3 * 1024 * 1024


def _pss(path: Path | None) -> list[float]:
    if path is None or not path.exists():
        return []
    with path.open(encoding="utf-8") as f:
        return [float(r[1]) for r in list(csv.reader(f))[1:] if len(r) >= 2]


def build(gfx_on, gfx_off, pss_csv, stats, kills) -> Section:
    s = Section("smooth")
    if gfx_on is None or gfx_off is None:
        s.rows.append(Row("AC-5.3-02", "jank_diff_pp", None, "<= 1 percentage point", None))
    else:
        d = gfx.compare(gfx_on, gfx_off)
        s.rows.append(
            Row("AC-5.3-02", "jank_diff_pp", round(d, 3), "<= 1 percentage point", d <= 1)
        )
    v = _pss(pss_csv)
    if len(v) < 10:
        s.rows.append(Row("AC-5.3-03", "max_pss_kb", None, "<= 3 GB", None))
        s.rows.append(Row("AC-5.3-03", "growth_pct", None, "<= 5 % over 30 min", None))
    else:
        k = max(1, len(v) // 10)
        first, last = sum(v[:k]) / k, sum(v[-k:]) / k
        g = 100 * (last - first) / first
        s.rows.append(Row("AC-5.3-03", "max_pss_kb", max(v), "<= 3 GB", max(v) <= PSS_MAX_KB))
        s.rows.append(Row("AC-5.3-03", "growth_pct", round(g, 2), "<= 5 % over 30 min", g <= 5))
    if stats is None:
        s.rows.append(Row("AC-5.3-04", "throttle_cycle", None, "throttled then recovers", None))
    else:
        c = throttle_cycle(stats)
        s.rows.append(Row("AC-5.3-04", "throttle_cycle", c, "throttled then recovers", c))
    if not kills:
        s.rows.append(Row("AC-5.3-07", "kills_recovered", None, "5/5 within 5 s", None))
    else:
        n = sum(1 for r in kills if (r.get("recoveredMs") or 10**9) <= 5000)
        s.rows.append(Row("AC-5.3-07", "kills_recovered", n, "5/5 within 5 s", judge(kills)))
    return s.finish()


def _gfx(p: Path):
    return gfx.parse_gfxinfo(p.read_text(encoding="utf-8")) if p.exists() else None


def _jl(p: Path):
    return jsonl(p) if p.exists() else None


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dir", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    a = ap.parse_args()
    d = a.dir
    s = build(
        _gfx(d / "gfxinfo_on.txt"),
        _gfx(d / "gfxinfo_off.txt"),
        d / "pss.csv",
        _jl(d / "stats.jsonl"),
        _jl(d / "kills.jsonl"),
    )
    a.out.parent.mkdir(parents=True, exist_ok=True)
    s.write(a.out)
    print(s.status)
    return 0


if __name__ == "__main__":
    sys.exit(main())
