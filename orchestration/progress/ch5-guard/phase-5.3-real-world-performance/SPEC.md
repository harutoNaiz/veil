# SPEC Phase 5.3 Real-world performance
MODEL: claude-opus-5-5 · Status: DRAFT (awaiting orchestrator) · PLAN.md lines 1507-1520 (Ch5 gate), 1723-1825 (5.3) · Entry: 5.2 spec-approved, NOT built; 5.2-W live wiring deferred; phone NOT connected.

## 1. Deviations and risks
- **DV-1 Tooling only.** Builders deliver capture scripts, parsers and report writers in a new Python package `workshop/perf/` (no Gradle, no Kotlin). Every on-phone number is PENDING-HUMAN; each has one ready command (§6).
- **DV-2 Stage timestamps come from the Guard's own log, not Perfetto SQL.** Perfetto traces are captured as evidence (`adb shell perfetto ... -o /data/misc/perfetto-traces/...`) but not parsed: `trace_processor` is a binary download (Deferred: "5.3-TP perfetto SQL cross-check"). Latency is computed from `debug.jsonl` `kind=stage` lines (§2) + Test Feed `feedlog.jsonl`.
- **DV-3 Emitting `kind=stage` lines + `android.os.Trace` sections in the conductor/overlay** belongs to the live wiring → appended to Deferred item "5.2-W live wiring" (≈10 lines in `LiveWiring.kt`). Until then the parsers run on synthetic fixtures only.
- **DV-4 "Fix the slowest stage" (5.3.1 step 3) and "tune default rates" (5.3.3 step 4)** need real numbers → Human/PHONE. Builders ship the stage ranking + the param-sync tool; no param values change in this phase (AC-5.3-08 checked as a no-op sync).
- **DV-5 Slow-motion filming (5.3.1 step 4)** optional → Human.
- **R-1 Phone safety (§12.8).** Against Instagram we only read: `dumpsys gfxinfo com.instagram.android [reset]` (resets frame counters only), `am start`, swipes. Never `force-stop`/`pm clear` it. Kill tests target `com.veil.guard` only. Test account only.
- **R-2 Battery A/B** = 4×30 min + Light + Strict + 15-min video ≈ 3.5 h phone time → Deferred/Human batch (F6), run in background with a log.
- **R-3 gfxinfo text format varies by Android version.** Parser keys on `Total frames rendered:` and `Janky frames:` only; fixture is a recorded-style text sample written by the Builder (no phone).
- **R-4 Disjoint paths:** each sub-phase owns one subpackage; `workshop/perf/__init__.py` and `workshop/perf/schema.py` are written verbatim from §2 by 5.3.1 in its first 2 minutes; the others may create an identical copy if absent (content is fixed, so no conflict).

## 2. Shared interfaces (verbatim)
Paths under `veil/`. Python only, run via `uv run --locked`. No new deps (stdlib + numpy if needed).
`workshop/perf/__init__.py`: empty docstring `"""Phase 5.3 real-world performance tooling."""`.
`workshop/perf/schema.py`:
```python
"""Shared shapes for Phase 5.3. Every *.json section file is {"section": str, "status": "PASS"|"FAIL"|"PENDING", "rows": [Row...], "notes": [str]}."""
from __future__ import annotations
import json
from dataclasses import asdict, dataclass, field
from pathlib import Path

STAGES = ("frame", "gate", "ai", "judge", "plan", "draw")  # kind=stage lines, in order
GUARD_PKG, FEED_PKG, IG_PKG = "com.veil.guard", "com.veil.testfeed", "com.instagram.android"

@dataclass
class Row:
    ac: str            # "AC-5.3-01" ...
    metric: str        # e.g. "p95_ms"
    value: float | str | None   # None -> PENDING
    threshold: str     # PLAN text, word for word
    ok: bool | None    # None -> PENDING

@dataclass
class Section:
    section: str       # "latency" | "smooth" | "battery"
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
```
Input log shapes (fixtures follow these exactly):
- Guard `debug.jsonl` stage line (emitted by 5.2-W): `{"kind":"stage","lookId":int,"stage":<STAGES>,"tMs":int}` (`tMs` = `SystemClock.uptimeMillis`). Plan lines: `{"kind":"plan","tMs":int,"lookId":int,"masks":[{"rect":[l,t,r,b],...}]}`. Stats lines: `{"kind":"stats","tMs":int,"phase":"active|throttled|idle|..."}` (phase from brain Scheduler, `"throttled"`).
- Test Feed `feedlog.jsonl`: as `guard/testfeed/README.md` (`type=frame`, `tMs`, `visible[{itemId,rect,...}]`). Clock alignment: both use uptime ms on the same phone.
- Sampler CSVs (5.3.2): `t_s,value` with header naming the metric, e.g. `t_s,pss_kb`, `t_s,thermal_status`.
Section files land in an evidence dir: `progress/ch5-guard/phase-5.3-real-world-performance/evidence/{latency,smooth,battery}.json`.

## 3. Sub-phases (all three in parallel from minute 0)

### 5.3.1 Time to cover
Goal: per-appearance time-to-cover + per-stage breakdown + slowest-stage ranking.
Owned: `workshop/perf/__init__.py`, `workshop/perf/schema.py`, `workshop/perf/latency/**`, `tools/verify/5.3.1.ps1`.
Files: `latency/__init__.py`, `latency/parse.py`, `latency/capture.py`, `latency/tests/test_latency.py`, `latency/tests/fixtures/{debug.jsonl,feedlog.jsonl}` (synthetic, ≤ 300 lines each, written by a small generator in the test or committed).
Key API:
- `appearances(feed: list[dict]) -> list[tuple[str,int,list[int]]]` → `(itemId, firstSeenTMs, rect)` for each tracked item's first visible frame (only items whose id starts with a prefix from `--targets`, default `cat,spider`).
- `time_to_cover(apps, debug: list[dict], cover_pct=80) -> list[dict]` → per appearance `{itemId, appearMs, coverMs|None, latencyMs|None}`; covered = first plan with a mask covering ≥ 80 % of the item rect at tMs ≥ appearMs (+ `draw` stage of that look if present, else plan tMs).
- `stage_breakdown(debug) -> dict[stage, {p50,p95,mean}]` of consecutive stage deltas per lookId; `slowest_stage(...) -> str`.
- `build_section(lat, breakdown, mode="balanced") -> Section` with Row `AC-5.3-01`, metric `p95_ms`, threshold `p95 ≤ 0.3 s across 100 appearances, Balanced`; ok = n ≥ 100 and p95 ≤ 300 (uncovered = +inf); n < 100 → ok False with note. Note lists slowest stage and the PLAN fix menu (smaller look area, batching, cache, model size).
- CLI: `python -m workshop.perf.latency.parse --debug D --feed F --out evidence/latency.json` (prints `P95 <ms> n=<n> slowest=<stage>`).
- `capture.py` (PHONE): `--minutes 5`: start perfetto in background (`adb shell perfetto -c - --txt` with sched/gfx/view/am categories + `atrace_apps: com.veil.guard`, 5 min), drive Test Feed (reuse `workshop.bench.drive.scroll`), pull `debug.jsonl` (run-as, `workshop.bench.adb.run_as_cat`), `feedlog.jsonl`, trace → `data/ch5/perf/<stamp>/`. Must exit 2 with `NO DEVICE` when no phone (never hang).
Steps: write §2 files first → parser + fixture (fixture: 120 appearances, known latencies so p95 = a known value; second fixture variant with p95 > 300 → FAIL) → tests → capture script with no-device guard.
Verify `5.3.1.ps1`: `uv run --locked pytest workshop/perf/latency -q`; run the CLI on the fixture and assert output line `P95` matches the expected value; `capture.py` with no device exits 2; `ruff check workshop/perf/latency workshop/perf/schema.py` → `VERIFY 5.3.1: PASS`.
Human: run capture with phone (after 5.2-W); optional slow-mo film.

### 5.3.2 Smoothness, memory, heat, kills
Goal: frame stats on/off, PSS over 30 min, thermal + throttled phase, kill recovery.
Owned: `workshop/perf/smooth/**`, `tools/verify/5.3.2.ps1`.
Files: `smooth/__init__.py`, `smooth/gfx.py`, `smooth/sample.py`, `smooth/kill.py`, `smooth/section.py`, `smooth/tests/test_smooth.py`, `smooth/tests/fixtures/{gfxinfo_on.txt,gfxinfo_off.txt,meminfo.txt,thermal.txt,pss.csv,thermal.csv,stats.jsonl,kills.jsonl}`.
Key API:
- `gfx.parse_gfxinfo(text) -> {"total": int, "janky": int, "rate_pct": float}`; `gfx.compare(on, off) -> float` (abs diff, percentage points).
- `sample.parse_meminfo_pss_kb(text) -> int` (`TOTAL PSS:` or `TOTAL` row); `sample.parse_thermal_status(text) -> int` (`Thermal Status: N` from `dumpsys thermalservice`); `sample.run(serial, minutes, every_s=10, out_dir)` (PHONE) writes `pss.csv`, `thermal.csv`.
- `throttle_cycle(stats: list[dict]) -> bool`: true iff some `phase=="throttled"` run is followed later by a non-throttled phase.
- `kill.run(serial, times=5)` (PHONE): `adb shell am kill com.veil.guard` is not enough for a foreground service → `adb shell run-as com.veil.guard kill -9 <pidof>`; poll every 250 ms up to 5 s for (pid back AND `dumpsys activity services com.veil.guard` shows the capture service) OR the "Resume Veil" notification (`dumpsys notification --noredact` contains `Resume Veil`); append `{"i","recoveredMs"|null,"how"}` to `kills.jsonl`. `kill.judge(rows) -> bool` = 5/5 with recoveredMs ≤ 5000.
- `section.build(gfx_on, gfx_off, pss_csv, stats, kills) -> Section` rows: AC-5.3-02 (`≤ 1 percentage point`), AC-5.3-03 (max PSS ≤ 3 GB = 3·1024·1024 kB and growth = (mean last 10 % − mean first 10 %)/mean first 10 % ≤ 5 %), AC-5.3-04, AC-5.3-07; missing inputs → PENDING rows.
- CLIs: `python -m workshop.perf.smooth.section --dir <run dir> --out evidence/smooth.json`; `python -m workshop.perf.smooth.sample|kill --serial ...` (exit 2 `NO DEVICE` without phone).
Steps: fixtures (hand-written text in realistic dumpsys format; one passing set + one failing PSS growth case) → parsers → section → PHONE scripts with no-device guard.
Verify `5.3.2.ps1`: pytest `workshop/perf/smooth`; section CLI on fixture dir → status PASS; failing fixture → FAIL; `sample` and `kill` without device exit 2; ruff → `VERIFY 5.3.2: PASS`.
Human: 30-min sessions on/off; heat the phone (e.g. camera + Guard Strict) to trigger throttling.

### 5.3.3 Battery, chapter report, twin sync, proof-test driver
Goal: measured battery per mode, `docs/reports/ch5-guard.md` with gate decision, params kept in step, `pt-5.3.ps1`.
Owned: `workshop/perf/battery/**`, `workshop/perf/report.py`, `workshop/perf/tune.py`, `workshop/perf/tests/test_report_tune.py`, `docs/reports/ch5-guard.md`, `tools/verify/5.3.3.ps1`, `tools/verify/pt-5.3.ps1`.
Files: `battery/__init__.py`, `battery/stats.py`, `battery/session.py`, `battery/tests/test_battery.py`, `battery/tests/fixtures/{batterystats_off.txt,batterystats_on.txt,battery_start.txt,battery_end.txt,runs.json}`.
Key API:
- `stats.parse_level(text) -> int` (`dumpsys battery` `level:`); `stats.parse_uid_mah(text, pkg) -> float | None` (`dumpsys batterystats --charged` "Estimated power use" UID line for the Guard uid; uid from `dumpsys package` `userId=`).
- Run record (`runs.json` list): `{"label":"A-off|A-on|B-off|B-on|light|strict|video15","mode":"off|light|balanced|strict","minutes":30|15,"brightness":int,"startLevel":int,"endLevel":int,"network":str,"guardMah":float|null}`.
- `stats.battery_table(runs) -> list[dict]` (drop %, guard mAh per run); `stats.extra_pct(runs) -> float` = mean over A,B of (on drop − off drop)/off drop × 100; guard: same brightness/startLevel(±2)/network within each pair else row FAIL "conditions differ".
- `stats.build_section(runs) -> Section`: AC-5.3-05 (`≤ 15% extra over 30 minutes of Instagram in Balanced; A/B run twice with the same brightness, starting charge and network`), AC-5.3-06 (`Light, Strict and a 15-minute video session measured and recorded`).
- `session.run(serial, label, mode, minutes, brightness)` (PHONE, background-friendly): `dumpsys batterystats --reset`, records level, sets mode via the Guard's adb command receiver (4.1.3) `am broadcast -n com.veil.guard/... --es mode <m>` (Builder reads the receiver for the exact action), opens Instagram, scrolls at human pace (`drive.scroll` every 3-8 s random, seed fixed), ends with level + batterystats dump → appends to `runs.json`. No device → exit 2.
- `report.py`: `python -m workshop.perf.report --evidence <dir> --out docs/reports/ch5-guard.md`: reads the three section files (missing → PENDING), writes: summary, latency table + stage breakdown, smoothness/memory/heat, battery table per mode, Chapter 5 gate (4 lines copied from PLAN 1513-1516) with decision `PASS|FAIL → apply Chapter 5 fallback|PENDING-HUMAN`, deferred/human list.
- `tune.py`: `python -m workshop.perf.tune [--set mode.group.key=value ...] --check`: applies changes to `workshop/twin/params.json` and copies to `guard/app/src/androidTest/assets/params.json`; `--check` exits 1 if the two files differ. Golden tapes: verify runs `uv run --locked pytest workshop/replay -q` (twin tapes); `:brain:tapeTest` runs in pt-5.3 only (Gradle mutex, `-Pveil.brainOnly=true`).
Steps: fixtures (passing A/B: off 6 %/on 6.6 % twice; failing: on 8 %) → stats + tests → report from fixture evidence + from empty dir (all PENDING) → tune `--check` → generate `docs/reports/ch5-guard.md` from an EMPTY evidence dir (all PENDING-HUMAN; fixture numbers never go in the real report) → pt-5.3.ps1.
Verify `5.3.3.ps1`: pytest `workshop/perf/battery workshop/perf/tests`; `tune --check` exit 0; `pytest workshop/replay -q`; report on fixture dir contains `Gate: PASS`, on empty dir contains `PENDING-HUMAN`; `session` without device exits 2; ruff → `VERIFY 5.3.3: PASS`.
Human: the battery batch (≈3.5 h) and the gate decision.

## 4. Acceptance criteria
| AC | Now | How checked | Pass threshold (PLAN, verbatim) |
| --- | --- | --- | --- |
| AC-5.3-01 | AUTO (parser on fixture) + PHONE | `latency.parse` on capture after 5.2-W | p95 ≤ 0.3 s across 100 appearances, Balanced |
| AC-5.3-02 | AUTO (parser) + PHONE | `smooth.gfx` on/off | Instagram dropped-frame rate with the Guard on vs off differs by ≤ 1 percentage point |
| AC-5.3-03 | AUTO (parser) + PHONE | `smooth.sample` 30 min | App memory (PSS) ≤ 3 GB throughout 30 minutes; growth ≤ 5% |
| AC-5.3-04 | AUTO (parser) + PHONE/HUMAN | stats `throttled` cycle + thermal.csv | The Throttled state is entered when the phone is hot and left when it cools |
| AC-5.3-05 | AUTO (calc) + DEFERRED/HUMAN | `battery.session` A/B ×2 | ≤ 15% extra over 30 minutes of Instagram in Balanced; A/B run twice with the same brightness, starting charge and network |
| AC-5.3-06 | DEFERRED/HUMAN | runs.json light/strict/video15 | Light, Strict and a 15-minute video session measured and recorded |
| AC-5.3-07 | AUTO (judge) + PHONE | `smooth.kill` | Back to running, or showing "Resume Veil", within 5 s, 5 out of 5 times |
| AC-5.3-08 | AUTO | `tune --check` + `pytest workshop/replay`; `:brain:tapeTest` in pt | Every tuned parameter is updated in the twin, and the golden tapes still pass |
Chapter gate (PLAN 1513-1516, verbatim): a cat in a live Instagram feed is covered within **0.3 s** (95% of the time) in Balanced mode; no visible stutter in Instagram with the Guard on; memory under **3 GB**; **15% or less extra battery** over 30 minutes of Instagram at fixed brightness. Fail → Light defaults, smaller models, fewer looks per second, and UI-layout pieces plus tiles instead of the object finder.

## 5. Proof test "A day in 30 minutes"
Machine part (now): the three verify scripts (fixtures) = parsers, judges and report proven.
`tools/verify/pt-5.3.ps1` (PHONE, needs 5.2-W built + installed; Gradle mutex for install/tapeTest): checks one device → `:brain:tapeTest` → sets fixed brightness (`settings put system screen_brightness_mode 0` + level, listed by this spec; restored at end) → for run in A-off, A-on, B-off, B-on: `battery.session` 30 min; during "on" runs, background `smooth.sample` + `gfxinfo reset/dump` (off runs too) → `latency.capture` 5 min on Test Feed (Balanced, ≥ 100 appearances) → `smooth.kill --times 5` → light/strict/video15 sessions → the three section CLIs → `report.py` → evidence in `progress/ch5-guard/phase-5.3-real-world-performance/evidence/`. Prints `PT 5.3: PASS|FAIL|PENDING`. Logs to `data/ch5/perf/pt.log`; runs in background (§12.11).
Human part: charge to 100 % (or the same level ±2 %) before each pair, same Wi-Fi, Instagram test account logged in, phone unplugged during runs (adb over Wi-Fi: `adb tcpip 5555; adb connect <ip>`), phone not touched. Heat step for AC-5.3-04 (Strict + camera app 10 min). Time: ≈ 4 h unattended + 20 min hands-on.

## 6. Human checklist (paste into HUMAN_CHECKS.md)
- [ ] HC-5.3-a Prereq: 5.2-W live wiring built (incl. `kind=stage` lines + Trace sections), Guard + Test Feed installed, Instagram test account.
- [ ] HC-5.3-b Latency: `uv run python -m workshop.perf.latency.capture --minutes 5` then `uv run python -m workshop.perf.latency.parse --debug <dir>\debug.jsonl --feed <dir>\feedlog.jsonl --out <evidence>\latency.json` → p95 ≤ 0.3 s; if not, note slowest stage + fix.
- [ ] HC-5.3-c Optional: film the screen with a second phone in slow motion; compare 3 appearances to the report.
- [ ] HC-5.3-d Smoothness/memory: during a 30-min Guard-on Instagram run `uv run python -m workshop.perf.smooth.sample --minutes 30`; gfxinfo on vs off; then `... smooth.section --dir <dir> --out <evidence>\smooth.json`.
- [ ] HC-5.3-e Heat: warm the phone (Strict + camera), confirm `throttled` appears then clears in stats.
- [ ] HC-5.3-f Kills: `uv run python -m workshop.perf.smooth.kill --times 5` → 5/5 within 5 s.
- [ ] HC-5.3-g Battery batch (≈3.5 h, Deferred): `powershell -NoProfile -ExecutionPolicy Bypass -File tools\verify\pt-5.3.ps1` with fixed brightness, same start charge, same network; verifier A repeats the A/B independently.
- [ ] HC-5.3-h If over budget: tune rates via `uv run python -m workshop.perf.tune --set balanced.sched.rate=<n> --check`, re-run tapes, re-measure; then make the Chapter 5 gate decision in `docs/reports/ch5-guard.md`.
