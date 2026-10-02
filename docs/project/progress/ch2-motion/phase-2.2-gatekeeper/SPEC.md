# SPEC: Phase 2.2 Deciding when to look (the Gatekeeper)

MODEL: claude-opus-5-5 · Status: APPROVED (orchestrator) · PLAN lines used: 553-565 (Ch 2 intro), 668-769 (Phase 2.2). Builds on 2.1 SPEC section 2 (sessions, labels, tape v1, player).

## 1. Deviations and risks
- **DV-1 Synthetic first.** Phone not connected. Every AUTO check and the tuning run on 2.1.1 synthetic sessions: dev set `data/ch2/synth-dev/` (seeds 1 and 2, 40 s each), PT on a fresh seed-22 session. AC-2.2-02/05/06 on real dev recordings: **PENDING-HUMAN**, one command (section 6).
- **DV-2 Hot / Throttled inputs.** No "almost matched" signal (judge not in the replay) and no thermal/battery API on the laptop. `Tick.hot_hint` / `Tick.throttle` are False in replays; both states are proven by unit tests only. Wiring: later phases (2.3 / Ch 4).
- **DV-3 Vertical scroll only.** Shift compensation uses `dy`; `dx`, `ContentChanged`, `NodesSnapshot` are ignored (horizontal carousels show up as changed tiles -> periodic looks). **Deferred.**
- **DV-4 Scene-cut scoring.** Recall is over `sceneCut` marks only. A detected cut that matches an `appSwitch`/`lock`/`unlock` mark is not counted as false (the whole screen really changed). Revealed (scrolled-in) tiles never count toward a cut, so a Reels swipe is a `swipe`/`revealedStrip`, not a cut.
- **DV-5 Integer boundary.** The thumbnail itself is made by OpenCV `INTER_AREA` (same call as the 2.1 player, `player._thumb_b64`). The integer-only, bit-exact contract starts at the 2048 thumbnail bytes, which tape-in carries. Kotlin port and the bit-exact cross-check: **Deferred** (Ch 4, golden tapes in 2.3).
- **DV-6 What tuning may change.** Only `tile_level`, `min_immediate_gap_ms`, `hot_ms` (PLAN 2.2.3 step 3). Rates 1/3/8 per s and check-ups 10/5/2 s stay at the PLAN starting values. If AC-2.2-05 and AC-2.2-06 cannot both pass: prefer AC-2.2-06 and propose a waiver on AC-2.2-05 (PLAN "If rejected").
- **DV-7 Bars.** Ignore thumbnail rows 0-1 (status bar) and 62-63 (nav bar), about 50 screen px each on 720x1600. Real bar heights on the phone: **Human** check.
- **DV-8 Situation breakdown** (feed scroll, Reels, video, static) uses the per-frame `scene` in `<id>.truth.jsonl`; real recordings have no truth file, so they report `all` only. **Deferred** until labels carry situations.
- **Risk:** 2.2 needs 2.1 built (player, `synth_session.generate`, labels). Builders start after 2.1's verify scripts pass. **Risk:** sub-row scroll residue (INTER_AREA) can light tiles on real video; `tile_level` gets retuned on real dev recordings.
- **Risk:** budget vs latency on scroll-heavy synthetic sessions may conflict (DV-6 rule applies). No new deps (numpy, opencv, matplotlib, pytest are in `uv.lock`).

## 2. Shared interfaces (all three Builders start from these)
Run Python as `powershell -NoProfile -ExecutionPolicy Bypass -File tools\with-env.ps1 uv run python ...` from `D:\iqoo finale\veil`. Times: int ms. Rects: `{"x","y","w","h"}` ints in **screen px**. No floats in `change.py` (except inside `thumb`) or `scheduler.py`.

**`workshop/twin/change.py` (2.2.1)**
```python
THUMB_W, THUMB_H, TILE = 32, 64, 8      # 4 tile cols x 8 tile rows = 32 tiles; index = row*4 + col
@dataclass(frozen=True)
class ChangeParams:
    ignore_top_rows: int = 2; ignore_bottom_rows: int = 2
    tile_level: int = 12        # tile mean |diff| (0..255) at/above which a tile is "changed"
    cut_tile_level: int = 40    # "large" tile change for the scene-cut test
    cut_pct: int = 60           # % of compared tiles that must be large (PLAN starting point: 60%)
    cut_global: int = 30        # global mean |diff| over compared pixels must also be >= this
    cut_min_tiles: int = 8      # fewer compared (non-revealed) tiles -> never a cut
@dataclass(frozen=True)
class ChangeResult:
    tile_scores: tuple[int, ...]               # 32 ints, 255 for revealed tiles
    changed_tiles: int; scene_cut: bool; score: int   # score = global mean |diff| (0..255), 0 if nothing compared
    revealed_rows: tuple[int, int] | None      # [r0, r1) thumbnail rows with no reference after the shift
    changed_box: tuple[int, int, int, int] | None   # (x0, y0, x1, y1) thumb px, bbox of changed tiles
    shift_rows: int
def thumb(frame_bgr: np.ndarray) -> np.ndarray   # (64, 32) uint8 = cv2.resize(BGR2GRAY, (32, 64), INTER_AREA)
def shift_rows(dy_screen: int, width: int, height: int, screen_width: int) -> int
    # round-half-away-from-zero of dy_screen*width*64 / (screen_width*height); synthetic 720x1600 -> dy/25
def detect(cur: np.ndarray, ref: np.ndarray | None, dy_rows: int, p: ChangeParams = ChangeParams()) -> ChangeResult
    # ref None -> every tile changed, scene_cut False, revealed_rows None
def thumb_box_to_screen(box: tuple[int, int, int, int], frame: dict) -> dict
    # x = bx*screenWidth//32 ; y = by*height*screenWidth//(64*width) ; clipped to the screen (frame = Frame contract dict)
```
Detect rules: content band = rows `[ignore_top, 64-ignore_bottom)`. Shifted reference `ref'[r] = ref[r - dy_rows]` inside the band; band rows whose source falls outside the band are **revealed**. Tile mean = `sum|cur-ref'| // n` over its non-ignored pixels (np.int32). A tile with any revealed row: score 255, changed, excluded from the cut test. `scene_cut = compared >= cut_min_tiles and large*100 >= cut_pct*compared and score >= cut_global`.

**`workshop/twin/scheduler.py` (2.2.2)**: pure, no clock, no randomness, no I/O.
```python
STATES = ("idle", "watching", "hot", "throttled")
IMMEDIATE = ("sceneCut", "appChange", "swipe", "revealedStrip")   # priority order, highest first
@dataclass(frozen=True)
class ModeParams:
    rate: int; checkup_ms: int; min_immediate_gap_ms: int
    hot_ms: int = 3000; hot_rate_mul: int = 2; throttle_div: int = 2
    burst_gap_ms: int = 150; deadline_ms: int = 200; skip_packages: tuple[str, ...] = ()
MODES = {"light": ModeParams(1, 10000, 300, deadline_ms=300),
         "balanced": ModeParams(3, 5000, 150),
         "strict": ModeParams(8, 2000, 66, deadline_ms=100)}
@dataclass(frozen=True)
class Tick:                 # one per delivered frame; events since the previous frame are folded in
    t_ms: int; frame_id: int; screen_w: int; screen_h: int
    changed_tiles: int = 0; scene_cut: bool = False
    revealed_rect: dict | None = None; changed_rect: dict | None = None
    scroll_dy: int = 0; window_changed: bool = False; package: str | None = None
    screen_on: bool | None = None          # True ScreenOn, False ScreenOff, None no event
    busy: bool = False; hot_hint: bool = False; throttle: bool = False
@dataclass(frozen=True)
class SchedState:
    phase: str = "watching"; screen_on: bool = True; package: str = ""
    last_look_ms: int = -10**9; last_immediate_ms: int = -10**9; last_checkup_ms: int = -10**9
    last_scroll_ms: int = -10**9; hot_until_ms: int = -10**9
    pending: str | None = None             # ONE slot (best unserved immediate reason). Never a list.
    skipped: int = 0; looks: int = 0; last_reason: str = "none"   # tape enum incl. "busy"
@dataclass(frozen=True)
class LookRequest:          # meaning fixed for later phases: why, where, deadline
    why: str; rect: dict; deadline_ms: int; frame_id: int; t_ms: int   # deadline_ms = t_ms + p.deadline_ms
def step(state: SchedState, tick: Tick, p: ModeParams) -> tuple[SchedState, LookRequest | None]
```
Step rules, in order: (1) phase: ScreenOff or package in `skip_packages` -> `idle` (no looks, pending cleared); ScreenOn counts as `window_changed`; else `throttled` if `throttle`; else `hot` if `hot_hint` (sets `hot_until_ms = t + hot_ms`) or `t < hot_until_ms`; else `watching`. (2) new immediate reasons: `sceneCut` if `scene_cut`; `appChange` if `window_changed`; `swipe` if `scroll_dy != 0 and t - last_scroll_ms > burst_gap_ms` (then `last_scroll_ms = t` whenever `scroll_dy != 0`); `revealedStrip` if `revealed_rect`; merge into `pending` by priority. (3) gap = `ceil(1000/rate)` watching, `ceil(1000/(rate*hot_rate_mul))` hot, `ceil(1000*throttle_div/rate)` throttled; in throttled **every** look also needs `t - last_look_ms >= gap`, and the check-up period is `checkup_ms*throttle_div`. (4) want = `pending` if `t - last_immediate_ms >= min_immediate_gap_ms`; else `checkup` if `t - last_checkup_ms >= checkup period`; else `periodic` if `changed_tiles > 0 and t - last_look_ms >= gap`; else none. (5) want and `busy` -> no request, `skipped += 1`, `last_reason = "busy"`, pending kept (never queued). (6) want and not busy -> request; rect = `revealed_rect` for revealedStrip, `changed_rect` for periodic (full screen if None), full screen otherwise; any full-screen look resets `last_checkup_ms`; pending cleared.

**`workshop/twin/gatekeeper.py` (2.2.3)**
```python
class GatekeeperPipeline:   # 2.1 Pipeline protocol; name "gatekeeper-v1"
    def __init__(self, mode: str = "balanced", params: Path | dict | None = None, look_ms: int = 0): ...
    def on_event(self, event: dict) -> list[dict]       # buffers; returns []
    def on_frame(self, frame_bgr, frame: dict) -> list[dict]   # = on_thumb(change.thumb(frame_bgr), frame)
    def on_thumb(self, th: np.ndarray, frame: dict) -> list[dict]   # emits exactly one `change` + one `look` record
def load_params(path: Path = PARAMS) -> dict[str, tuple[ChangeParams, ModeParams]]   # ignores extra keys
def run_tape(tape_in: Path, mode: str, params: dict | None = None, look_ms: int = 0) -> list[dict]  # no video decode
```
Per frame: fold buffered events into a `Tick` (`scroll_dy` = sum of Scrolled `dy`; `window_changed` = a WindowChanged whose `packageName` differs from the current one, start = session `packageName`; ScreenOff/ScreenOn -> `screen_on`); `dy_since_ref += scroll_dy`; `detect(th, ref, shift_rows(dy_since_ref, ...))`; `busy = t < busy_until`; `step`. On a request: `ref = th`, `dy_since_ref = 0`, `busy_until = t + look_ms`. A request arriving while busy would go to `self.queue` (a list); `x.queue = len(self.queue)` must always be 0.
Tape-out records (2.1 tape v1 kinds): `{"kind":"change","frameId","tMs","changedTiles","sceneCut","score","x":{"revealedRows":[r0,r1]|null,"shiftRows"}}` and `{"kind":"look","frameId","tMs","look":bool,"reason":why|"none"|"busy","state":phase,"rect"(only if look),"x":{"deadlineMs"(only if look),"queue":0,"skipped":n}}`.

**`workshop/twin/params.json`** (2.2.3 creates with the starting values above, then tuning rewrites it):
`{"params_version":"1","modes":{"light":{"change":{ChangeParams fields},"sched":{ModeParams fields}},"balanced":{...},"strict":{...}},"tuned":{"by":"2.2.3","on":[sessionIds],"metrics":{...}}}`. Field names = dataclass field names (snake_case), so `ChangeParams(**d["change"])` works. Unit tests in 2.2.1/2.2.2 use the code defaults, never the JSON.

**Stubs for 2.2.3** (`workshop/twin/tests/gk_stubs.py`, 2.2.3 owns): `detect_stub(cur, ref, dy_rows, p=None)` -> `ChangeResult` with 0 changed tiles; `step_stub(state, tick, p)` -> a full-screen `periodic` request every 10th frame. Used only while the real modules are missing; the final verify imports the real ones.

## 3. Sub-phases (all three run in parallel)

### 2.2.1 Change detector
**Goal:** cheap, integer-only "how much changed since the last look", with scroll compensation and scene cuts.
**Owned:** `workshop/twin/change.py`, `workshop/twin/tests/test_change.py`, `tools/verify/2.2.1.ps1`. (Do not touch the 1.3 files in `workshop/twin/`.)
**Steps:**
1. `change.py` per section 2 (numpy int32 only; `//` only; no float literals).
2. Tests with synthetic thumbs (seeded random texture made in the test): **static** (identical) -> 0 changed, no cut; **small blink** (2x2 px, +120, one tile) -> 0 changed; **pure scroll** (band shifted by -3 rows, new rows at the bottom, `dy_rows=-3`) -> `revealed_rows == (59, 62)` and only tiles containing those rows changed; **scene cut** (two independent textures) -> `scene_cut` True; **slow fade** (ref fixed, cur = ref + 7k, k = 1..30) -> `changed_tiles > 0` at some k < 30; Reels-like shift of >= the band height -> all revealed, `scene_cut` False; status/nav rows changed only -> 0 changed.
3. `shift_rows` exact on `(25, 360, 800, 720) -> 1`, `(-12, ...) -> 0`, `(-13, ...) -> -1`, `(-1600, ...) -> -64`; `thumb_box_to_screen((0, 59, 32, 62), synthetic frame) == {"x":0,"y":1475,"w":720,"h":75}`.
4. **Integer checklist test (AC-2.2-08):** `ast` walk of `change.py` excluding the body of `thumb`: no `ast.Div`, no float constants, no names/attrs `float`, `round`, `mean`, `sqrt`, `math`, `float32`, `float64`; and `detect` returns only Python `int`/`bool`/tuples of int.
**Verify `tools/verify/2.2.1.ps1`** (< 30 s): `uv run pytest workshop/twin/tests/test_change.py -q` passes. Ends `VERIFY 2.2.1: PASS`.
**Human:** none.

### 2.2.2 Burst scheduler
**Goal:** pure `(state, tick) -> (state, request|None)` with Idle/Watching/Hot/Throttled, priorities, check-ups, never queueing.
**Owned:** `workshop/twin/scheduler.py`, `workshop/twin/tests/test_scheduler.py`, `tools/verify/2.2.2.ps1`.
**Steps:**
1. `scheduler.py` per section 2.
2. Transition tests (30 fps ticks built in the test): watching->idle on ScreenOff, idle->watching on ScreenOn with an `appChange` look; skip package -> idle; `hot_hint` -> hot for `hot_ms`, then watching, and hot looks come at twice the rate (balanced gap 167 vs 334 ms); throttle -> throttled and back; priority (scene cut + window change + scroll on one tick -> `sceneCut`); busy -> no request, `skipped` grows, the pending reason is served on the first non-busy tick; first tick -> `checkup`.
3. Rate tests: static screen 60 s -> check-up count 6 / 12 / 30 (+-1) for light / balanced / strict; continuous change, no events, 10 s -> looks <= rate*10 + check-ups; **AC-2.2-07:** continuous change + a scroll on every tick, throttled, 10 s, each mode -> looks per second <= 0.5 * rate.
4. **AC-2.2-03:** 1,000 seeded random tick sequences (50 ticks each, random fields incl. busy/hot/throttle/screen) run twice -> identical lists of (state, request); and an `ast` scan of `scheduler.py`: no import of `time`, `datetime`, `random`, `os`, `uuid`, `secrets`; no `np.random`; `pending` is never a list.
**Verify `tools/verify/2.2.2.ps1`** (< 1 min): `uv run pytest workshop/twin/tests/test_scheduler.py -q` passes. Ends `VERIFY 2.2.2: PASS`.
**Human:** none.

### 2.2.3 Gatekeeper pipeline, look budget, tuning, timeline
**Goal:** plug 2.2.1 + 2.2.2 into the 2.1 player, measure the budget per mode and situation, tune, write params.json and the report section, and the PT tooling.
**Owned:** `workshop/twin/gatekeeper.py`, `workshop/twin/budget.py`, `workshop/twin/timeline.py`, `workshop/twin/params.json`, `workshop/twin/tests/test_gatekeeper.py`, `workshop/twin/tests/gk_stubs.py`, `docs/reports/ch2-motion.md`, `docs/reports/img/ch2-look-budget.png`, `tools/verify/2.2.3.ps1`, `tools/verify/pt-2.2.ps1`.
**Steps:**
1. `gatekeeper.py` per section 2 + CLI `python -m workshop.twin.gatekeeper replay SESSION.session.json --out DIR [--mode balanced] [--look-ms 0]` (calls `workshop.replay.player.replay(..., pipeline, video=False)`; does not edit `workshop/replay/`).
2. `budget.py`:
   - `ensure_dev_set(dir="data/ch2/synth-dev")`: if missing, `synth_session.generate(dir, "synth-dev-1", seconds=40, seed=1)` and `synth-dev-2` (seed 2).
   - `evaluate(session_json, label, tape_in, mode, params, look_ms=0) -> dict`: frames, looks, looks/min, % frames analysed (`looks*100/frames`), new content = every label track span start; a look "sees" it if its rect is full screen or covers >= 50% of the box's on-screen area (`boxes_at(label, look.tMs)`); latency = first seeing look tMs - span start (no look inside the span = miss); `pct_within_200ms`, p95 latency; scene cuts: flagged frames grouped (gap <= 500 ms = one cut), matched to marks within [mark - 50, mark + 300] ms; recall over `sceneCut` marks, false cuts per minute (DV-4); skipped. Breakdown by situation from truth `scene`: feed/grid + a Scrolled event within +-300 ms = `feedScroll`, `reels`, `video`, other feed/grid = `static`; no truth file = `all`.
   - CLI `eval --sessions DIR --labels DIR [--split dev] --out DIR` (uses `split.json` when present; makes tape-in once per session via the player, then all runs use `run_tape`), prints `AC-2.2-02/05/06: PASS|FAIL <value>`.
   - CLI `tune`: per mode, grid `tile_level in {8,12,16,24}` x `min_immediate_gap_ms in {100,150,200,250}` (`hot_ms` stays 3000: no hot signal in replay, DV-2); pick the combo with the lowest % frames analysed among those with `pct_within_200ms >= 95`, else the highest `pct_within_200ms`. Writes `params.json`, the chart (looks per minute vs p95 time-to-first-look, one point per combo, colour per mode, chosen default ringed; matplotlib Agg) and the `## Look budget (Phase 2.2)` section of `docs/reports/ch2-motion.md` (tables per mode and situation, scene-cut line, chosen params, waiver note if DV-6 applies).
3. `timeline.py`: `pad_idle(session_json, out_dir, idle_ms=30000) -> Path` (ffmpeg `tpad=start_duration=30:start_mode=clone` on `<id>.mp4`; shift events, truth, driver and label times by +idle_ms; prepend truth lines copying frame 0; tracks starting at the original `t0Ms` keep starting at `t0Ms`; `frameCount` += 900; id `<id>-idle`); `chart(tape_in, tape_out, session_json, png)`: lanes = changed tiles per frame, Scrolled dy stems, looks as markers coloured by reason, truth scene band + label marks; `pt_checks(...) -> dict` (section 5); CLI `python -m workshop.twin.timeline pt --out DIR [--session S --idle-start-ms A --idle-end-ms B]`.
4. Tests (on the 3 s session from `workshop.replay.tests.fixture.build`, for speed): `change.thumb(frame) == base64-decoded tape-in thumb` for the same frame; `run_tape(balanced)` records == player tape-out records (ignoring `seq`/header); every tape line validates (`python -m workshop.replay.tape validate`); `look_ms=500` replay: look:true records >= 500 ms apart, `x.queue == 0` everywhere, busy count == final `skipped` > 0; `load_params` round-trips params.json, rates 1/3/8 and check-ups 10000/5000/2000.
**Verify `tools/verify/2.2.3.ps1`** (< 3 min): pytest the tests; `budget eval` on the synthetic dev set prints AC-2.2-02 PASS, AC-2.2-06 PASS, and AC-2.2-05 PASS or `WAIVER-PROPOSED` (DV-6); `budget tune` writes params.json and the PNG; the report section exists. Ends `VERIFY 2.2.3: PASS`.
**Human:** run the eval on real dev recordings when they exist (section 6).

## 4. Acceptance criteria
| AC | Status | How it is checked | Threshold (PLAN, word for word) |
| --- | --- | --- | --- |
| AC-2.2-01 | AUTO | `test_change.py` synthetic cases | Static: no change. Blink: below threshold. Pure scroll: only the revealed strip. Scene cut: flagged. Slow fade: triggers before the fade ends |
| AC-2.2-02 | AUTO (synthetic) + PENDING-HUMAN (real dev recordings) | `budget eval` cut matching (DV-4) | ≥ 90% of labelled cuts detected; ≤ 1 false cut per minute |
| AC-2.2-03 | AUTO | `test_scheduler.py` property test + `ast` purity scan | 1,000 random input sequences run twice give identical outputs; the code has no wall clock or randomness |
| AC-2.2-04 | AUTO | `look_ms=500` replay in `test_gatekeeper.py` and PT slow run | With looks forced to take 500 ms, the pending queue is always empty and skipped frames are counted |
| AC-2.2-05 | AUTO (synthetic) + PENDING-HUMAN (real) | `budget eval`, Balanced | Balanced analyses < 15% of frames on dev recordings |
| AC-2.2-06 | AUTO (synthetic) + PENDING-HUMAN (real) | `budget eval`, Balanced, label span starts | 95% of new content gets a look within 0.2 s of video time (Balanced) |
| AC-2.2-07 | AUTO | `test_scheduler.py` throttled rate test | In Throttled, looks per second ≤ 50% of the Watching rate |
| AC-2.2-08 | AUTO | `test_change.py` `ast` integer checklist (DV-5 boundary) | The change detector uses integer maths only |

Done-when extras: 2.2.2 "a replay shows sensible look timing on every recording type" = PT timeline (synthetic AUTO, real HUMAN). Bit-exact Kotlin match: DEFERRED (DV-5).

## 5. Proof test PT-2.2 "Look timeline"
**Machine part** `tools/verify/pt-2.2.ps1` (< 5 min), fresh synthetic session, Balanced:
1. Delete `data/evidence/pt-2.2/`; `generate(..., "pt22", seconds=150, seed=22)` (never used for tuning); `pad_idle` -> 180 s session `pt22-idle` (30 s doing nothing, then slow scroll, fling, Reels swipes, video with scene cuts, app switch, lock/unlock).
2. Replay with `look_ms=0` and again with `look_ms=500` (player + `GatekeeperPipeline`); `tape validate` all four tapes.
3. Checks (`pt_checks`, each printed PASS/FAIL):
   - idle `[t0Ms, t0Ms+30000)`: every look has reason `checkup`, count 6 or 7;
   - every scroll burst start (Scrolled gap > 150 ms) and every `sceneCut` / `appSwitch` / `unlock` mark has a look within 200 ms (normal run) and within 700 ms (slow run);
   - in truth `scene == "video"`: every sliding 1 s window has `periodic` + `revealedStrip` looks <= 3 (Balanced cap);
   - slow run: look:true records >= 500 ms apart, `x.queue == 0` on every line, busy records == `skipped` > 0 (AC-2.2-04);
   - AC-2.2-05 and AC-2.2-06 values on this session (reported; FAIL only if AC-2.2-06 fails).
4. Evidence: `data/evidence/pt-2.2/{timeline.png,timeline-slow.png,looks.csv,pt.json}`. Ends `PT 2.2: PASS (machine)`.

**Human part** (~5 min now, ~30 min when the phone is back): open both PNGs; confirm no missed trigger and no idle looks beyond check-ups; write 3-5 lines of reviewer notes. Phone later: record a fresh 3-minute session with the PLAN mix, run `tools\verify\pt-2.2.ps1 -Session <id>.session.json -IdleStartMs A -IdleEndMs B` (truth-based checks are skipped without truth), review the chart.

## 6. Human items (paste into HUMAN_CHECKS.md)
```
HC-2.2 Gatekeeper (laptop now ~5 min; phone later ~45 min)
[ ] Open data/evidence/pt-2.2/timeline.png and timeline-slow.png: no missed swipe / scene cut / app switch,
    no looks in the first 30 s except check-ups, nothing piles up in the slow run. Write 3-5 lines of notes.
[ ] Glance at docs/reports/ch2-motion.md "Look budget": chosen params per mode look sane; note any waiver on AC-2.2-05.
[ ] Phone: on a real screenshot, check the status bar fits in the top 2 and the nav bar in the bottom 2
    of 64 thumbnail rows (about 50 screen px each on 720x1600); else set ignore_*_rows in params.json.
[ ] After HC-2.1 recordings + labels exist: python -m workshop.twin.budget eval --sessions data/recordings
    --labels data/labels/recordings --split dev --out data/ch2/look-budget  -> AC-2.2-02/05/06 on real data
    (then budget tune on the same set if they fail).
[ ] PT-2.2 human part on a fresh 3-minute phone recording (SPEC section 5), reviewer notes saved with the chart.
```
