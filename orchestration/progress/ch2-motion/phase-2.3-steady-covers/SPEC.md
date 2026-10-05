# SPEC: Phase 2.3 Steady covers (the Follower and Painter)

MODEL: claude-opus-5-5 · Status: APPROVED (orchestrator; deviations accepted: confirm looks, scene cut ends self-capture hold, 64-bit DCT hash, spider = Layer 1 stand-in, .gitattributes rule for tapes) · PLAN lines used: 553-565 (Ch 2 intro + gate), 771-876 (Phase 2.3). Builds on 2.1 SPEC section 2 (player, tape v1, synthetic truth, self-capture) and 2.2 SPEC section 2 (change, scheduler, GatekeeperPipeline, params.json).

## 1. Deviations and risks
- **DV-1 Oracle detector (Deferred: real models).** SigLIP2 is 4-6 s/screen on this CPU, so replays feed the tracker from `OracleDetector`: findings built from the synthetic per-frame truth on every gatekeeper look, with seeded misses, jitter, near-misses, false positives and a fixed latency. `--detector real` exists as a flag and exits with `DEFERRED` (item for `progress/DEFERRED.md`: one dev session with the Judge on looks only, run alone in the background).
- **DV-2 Synthetic gate (Human: real gate).** Phone not connected. AC-2.3-01..05 and the Chapter 2 gate are AUTO on synthetic test sessions (`data/ch2/synth-test/`, seeds 3 and 4, 30 s) and recorded as the *synthetic* gate decision. The same command on real frozen test recordings: **PENDING-HUMAN**.
- **DV-3 Concepts.** Active list = `cats` (Layer 2) + `spiders` as a harmless Layer 1 stand-in (layer 1, rule 7 of ground rules). Dogs are look-alikes and are never active.
- **DV-4 Confirm looks.** Balanced needs 2 sightings, but the 2.2 scheduler only looks again on change. `MotionPipeline` adds a regional *confirm look* on the union of tentative tracks when no gatekeeper look happened, `t - last_detector_start >= min_immediate_gap_ms` of the mode and the detector is idle. Logged as the frame's look record with `look:true, reason:"periodic", x.confirm:true`; counted in "share of frames analysed".
- **DV-5 Scene cut ends self-capture protection.** PLAN lists scroll-away, app change, peek, max hold. On a gatekeeper `sceneCut`, tracks lose self-capture protection (normal hold applies, so they are re-checked); otherwise a cover outlives the content it hid by up to 20 s.
- **DV-6 Whole-post covers.** `scope:"wholeElement"` uses `post_bounds` when given; synthetic sessions have none (no NodesSnapshot yet), so it is a no-op here. **Deferred** to the logger (4.2.1).
- **DV-7 Cache hash = 64-bit DCT pHash**, not dHash (synthetic canvases have per-row stripes that defeat horizontal difference hashes). Crops that are blank (grey std < 8) or >= 50% under our own covers are never looked up or stored (a painted cover would collide with every other cover). Cache is not part of golden tapes (golden tapes cover change detector, scheduler, tracker, planner per PLAN).
- **Risk:** AC-2.3-01 (p95 <= 0.3 s) and AC-2.3-04 (>= 95%) are tight with confirm-after-2 + 100 ms latency + 150 ms min gap. Thresholds are never changed; if they fail, record FAIL, run the PLAN fallback once (`--solid-only`, holds x2, rates x2 via params override, report-only) and record the gate decision either way.
- **Risk:** CRLF (`core.autocrlf=true`). 2.3.3 appends `contracts/tapes/** -text` to `veil/.gitattributes`; tape tests compare parsed JSON records, never checked-out bytes.
- **Entry:** 2.2.1/2.2.2 committed; `workshop/twin/gatekeeper.py` exists with the 2.2 signatures (`GatekeeperPipeline(mode, params, look_ms)`, `on_event`, `on_thumb`, `run_tape`, `load_params`) while 2.2.3 finishes. Builders may use the section 2 stubs until 2.2.3 is committed; final verify imports the real modules.

## 2. Interfaces shared by the sub-phases
Run Python as `powershell -NoProfile -ExecutionPolicy Bypass -File tools\with-env.ps1 uv run python ...` from `D:\iqoo finale\veil`. Times int ms; rects `{"x","y","w","h"}` ints in **screen px** (720x1600 synthetic). `tracker.py` and `planner.py`: integer only (`//`, no float literals) except one helper `_fraction(pct) -> float` (= `pct / 100`) for the contract's `selfCaptureFraction`. Tie-breaking: always sort by the stated key, never by dict/set order. Test basenames must be unique (no `__init__` in `workshop/twin/tests`).

**`workshop/twin/tracker.py` (2.3.1)**
```python
@dataclass(frozen=True)
class TrackParams:
    confirm_n: int; hold_ms: int; max_hold_ms: int
    park_ms: int = 3000; iou_hide_pct: int = 30; iou_keep_pct: int = 50; self_capture_pct: int = 80
TRACK_MODES = {"light": TrackParams(3, 800, 10000), "balanced": TrackParams(2, 1500, 20000),
               "strict": TrackParams(1, 3000, 30000)}
def iou_pct(a: dict, b: dict) -> int                      # inter*100 // union, 0 if no overlap
def covered_pct(r: dict, covers: list[dict]) -> int       # % of r's area under the UNION of covers (numpy bool raster of r)
class Tracker:
    def __init__(self, mode="balanced", screen_w=720, screen_h=1600, *, self_capture_rule=True,
                 params: TrackParams | None = None): ...
    def on_scroll(self, dy: int, t_ms: int) -> None       # every live track: rect.y += dy (UiEvent sign), no AI
    def on_findings(self, findings: list[dict], t_ms: int) -> None   # Finding dicts, rects already in CURRENT screen coords
    def on_scene_cut(self, t_ms: int) -> None             # DV-5
    def on_app_change(self, t_ms: int) -> None            # release all
    def on_screen_off(self, t_ms: int) -> None            # release all
    def peek(self, track_id: int, t_ms: int) -> bool      # Layer 2 confirmed -> peeked=True; Layer 1 / unknown -> False
    def tick(self, t_ms: int, own_covers: list[dict]) -> list[dict]  # hold/park/self-capture; returns live Track dicts by trackId
```
Rules: (1) **Pass 1** `decision=="hide"` findings sorted by `(layer, conceptId, rect.y, rect.x, rect.w, rect.h, findingId)`; each takes the unmatched live track (any state but released, same conceptId) with the highest `iou_pct >= iou_hide_pct`, ties -> lowest trackId. Match: `sightings += 1`, `rect = finding.rect`, `lastSeenMs = t`, `holdUntilMs = t + hold_ms`, `maxHoldUntilMs = t + max_hold_ms`, `lastFindingId`; state `confirmed` if `layer == 1 or sightings >= confirm_n` else `tentative` (a parked track comes back the same way). Unmatched hide finding -> new track, `trackId` = next int from 1 (never reused), `sightings=1`, same state rule, `scope` from the finding. (2) **Pass 2** `nearMiss` findings, same order, only against tracks still unmatched with `iou_pct >= iou_keep_pct`: `holdUntilMs = t + hold_ms` only (no sighting, never creates). `leave` ignored. (3) `tick`: track rect with no overlap with `[0,screen_w) x [0,screen_h)` -> `parked`, `parkedUntilMs = t + park_ms` set once; parked and `t >= parkedUntilMs` -> released; parked whose rect overlaps the screen again -> back to its previous state at once with `holdUntilMs = max(holdUntilMs, t + hold_ms)` (re-checked by the next look). On-screen: `pct = covered_pct(rect, own_covers)`, `selfCaptureFraction = _fraction(pct)`; if `t > holdUntilMs`: keep only when `self_capture_rule and pct >= self_capture_pct and not scene_cut_since_last_sighting and t < maxHoldUntilMs`, else released. Released tracks are dropped. `peeked` tracks stay tracked but are not drawn.

**`workshop/twin/planner.py` (2.3.2)**
```python
@dataclass(frozen=True)
class PlanParams: pad_pct: int; drop_short_px: int; layer2_style: str; max_masks: int = 24
PLAN_MODES = {"light": PlanParams(4, 32, "blur"), "balanced": PlanParams(6, 0, "blur"), "strict": PlanParams(10, 0, "solid")}
def plan(tracks: list[dict], *, t_ms: int, frame_id: int, screen_w: int, screen_h: int, mode="balanced",
         reason="look", post_bounds: list[dict] | None = None, labels=False, solid_only=False,
         params: PlanParams | None = None) -> dict          # MaskPlan v1.0 dict, planId = basedOnFrameId = frame_id, rotation 0
def pad(rect: dict, pct: int, screen_w: int, screen_h: int) -> dict | None   # + short_side*pct//100 each side, clipped; None if empty
def merge(masks: list[dict]) -> list[dict]
```
Rules: draw only `state=="confirmed" and not peeked`; Light drops tracks whose short side < 32 px (never Layer 1); `wholeElement` + post bounds -> the post rect containing the track centre; pad; **merge** masks of the same layer whose rects intersect (area > 0) into the union bbox, repeat until stable (Layer 1 and Layer 2 never merge); conceptIds sorted unique (<= 8), trackIds sorted (<= 32); if > 24 masks, repeatedly merge the same-layer pair whose union adds the least area (ties: lowest index pair) until <= 24 (nothing is ever dropped for the cap). Style: Layer 1 `solid`, `peekable:false`; Layer 2 `layer2_style` (`solid` if `solid_only`), `peekable:true`. `labels=True` -> `label = ("Hidden · " + ", ".join(conceptIds))[:64]`. Output order and maskId 1.. by `(layer, y, x, w, h)`.

**`workshop/twin/cache.py` (2.3.2)**
```python
def phash64(crop_bgr: np.ndarray) -> int   # gray -> resize 32x32 INTER_AREA -> cv2.dct(float32) -> [0:8,0:8] > median -> 64-bit int
def hamming(a: int, b: int) -> int          # (a ^ b).bit_count()
def usable(crop_bgr) -> bool                # grey std >= 8
class FingerprintCache:                     # memory only; stores fingerprints (float16 vectors), NEVER verdicts
    def __init__(self, capacity=8000, max_dist=6, ttl_ms=60000): ...
    def get(self, h: int, t_ms: int) -> np.ndarray | None  # nearest entry with dist <= max_dist and age <= ttl; ties: smaller dist, then newest; counts hits/misses; refreshes LRU
    def put(self, h: int, fingerprint: np.ndarray, t_ms: int) -> None   # LRU eviction past capacity
    def clear(self) -> None                 # on ScreenOff (lock)
    hits: int; misses: int                  # + __len__
```

**`workshop/twin/oracle.py` + `workshop/twin/motion.py` (2.3.3)**
```python
DEFAULT_CONCEPTS = {"cats": 2, "spiders": 1}
@dataclass(frozen=True)
class OracleParams: miss_pct: int = 3; near_pct: int = 3; jitter_px: int = 4; fp_per_100_looks: int = 2
    occlude_pct: int = 50; latency_ms: int = 100; seed: int = 0
class OracleDetector:
    def __init__(self, truth_path: Path, concepts=DEFAULT_CONCEPTS, p=OracleParams()): ...
    def detect(self, frame: dict, look_rect: dict, look_id: int) -> list[dict]   # Finding v1.0 dicts at that frame's coords
class MotionPipeline:   # 2.1 Pipeline protocol; name f"motion-v1-{mode}"
    def __init__(self, session_json: Path, mode="balanced", *, detector="oracle", oracle=OracleParams(),
                 concepts=DEFAULT_CONCEPTS, self_capture_rule=True, use_cache=True, solid_only=False, labels=False): ...
    findings_log: list[dict]                # {"kind":"finding","tMs":deliveryT,"finding":F,"x":{"deliverFrameId":M}}
def run_tape(tape_in: Path, mode="balanced", **kw) -> list[dict]   # events+findings+frames from tape-in; no video, no cache
```
Oracle: truth boxes of active concepts with on-screen area >= 50% inside `look_rect` and < `occlude_pct`% under `frame["ownOverlay"]`; per box `rng = random.Random(f"{seed}:{frameId}:{key}")`: `miss_pct` -> nothing, `near_pct` -> `nearMiss` (prob 0.5), else `hide` (prob 0.9), rect jittered by `rng.randint(-j, j)` per edge (w,h >= 1); FP: `random.Random(f"{seed}:fp:{look_id}")`, `fp_per_100_looks` % chance of one `cats` hide at a random 100-250 px square inside `look_rect`. `findingId = f"o{look_id}-{k}"`, `lane:"finder"`, `scope:"object"`.
Pipeline per frame: `on_event` -> gatekeeper `on_event`; Scrolled -> `tracker.on_scroll`, add dy to `cum_dy`; WindowChanged (new package) -> `on_app_change`; ScreenOff -> `on_screen_off` + `cache.clear()`. `on_frame` -> `th = change.thumb(frame_bgr)`, then the shared core: `gk.on_thumb(th, frame)` (2 records); `sceneCut` -> `on_scene_cut`; confirm look (DV-4); on a look: `oracle.detect` queued for delivery at `t + latency_ms`; deliver due findings with `rect.y += cum_dy_now - cum_dy_at_source_frame`; `on_findings`; `tick(t, frame["ownOverlay"])`; `plan(...)`. Emits per frame, in order: `change`, `look`, `tracks`, `maskPlan` (every frame; reason priority `appChange > look > scroll > expire > clear`, else the previous reason; first frame `clear`), and `cache` {hits, misses deltas, x.situation} on look frames when `use_cache` (crops = every truth box >= 50% inside the look rect, `usable`, < 50% under own covers; miss -> `put` a deterministic 8-dim float16 vector). `GatekeeperPipeline(mode, look_ms=latency_ms)`. `detector="real"` -> `SystemExit("DEFERRED: real detector path")`.

**Stubs** (`workshop/twin/tests/motion_stubs.py`, 2.3.3 owns): `StubTracker` (every hide finding -> confirmed track, shifted by scroll, dropped after 1 s), `plan_stub(tracks, **kw)` (solid Layer-2 masks, no pad/merge), `StubCache` (always miss), `StubGatekeeper` (full-screen `periodic` look every 10th frame). Used only until the real modules exist.

**Metric definitions (frozen by 2.3.3, reused in Ch 5).** Boxes per frame: `<id>.truth.jsonl` when present (exact), else `boxes_at(label, tMs)`; only active concepts. Plan in effect at frame N = latest maskPlan with `frameId <= N`. *Visible*: >= 50% of the box area on screen. *Covered*: >= 80% of its on-screen area under the plan's masks. *Appearance*: a key's not-visible -> visible transition (incl. first frame). *Time to cover*: first covered frame of that visible run minus onset; never covered in the run = miss (infinity). Median and p95 nearest-rank (`sorted[ceil(0.95n)-1]`). *Coverage*: covered visible box-frames / visible box-frames. *Flicker*: same key covered at frame a, uncovered at a+1..b-1 while visible in all of them, covered at b, `t_b - t_(a+1) <= 1000`. *Clean stretches*: label `clean` spans, else frames with no visible active box. *Wrong cover*: a mask (by trackIds) on a clean frame overlapping no visible active box by >= 10% of the mask area; count contiguous episodes; per minute of clean time; also wrong-cover seconds per minute. *Glue*: frames with a Scrolled event since the previous frame; each fully on-screen covered box with a single-track mask: `max(|dcx|, |dcy|)` between mask and box centres; median. *Analysed*: look:true records / frames. *Re-cover*: appearances whose key was covered within the previous 3 s -> time to cover.

## 3. Sub-phases (all three run in parallel)

### 2.3.1 Tracker
**Goal:** sightings -> stable tracks that follow their item. **Owned:** `workshop/twin/tracker.py`, `workshop/twin/tests/test_tracker.py`, `tools/verify/2.3.1.ps1`.
**Steps:** 1. `tracker.py` per section 2. 2. Tests (hand-made Finding dicts): two-pass match (hide at IoU 0.3 matches, 0.29 makes a new track; nearMiss at 0.5 keeps alive without a sighting, 0.49 does not, nearMiss never creates); tie-break (two equal-IoU tracks -> lower trackId); confirm after 3/2/1 sightings per mode and Layer 1 confirmed on the first sighting in Light; scroll shift exact (dy -37 -> y - 37); hold 800/1500/3000 then released; **self-capture**: own cover over >= 80% keeps the track past hold until `maxHoldUntilMs` (10/20/30 s), 79% does not, `self_capture_rule=False` does not, scene cut ends it; parked: scrolled fully off -> `parked`, back within 3 s -> previous state on the same tick, after 3 s -> released; app change / screen off release all; peek: Layer 2 -> True + not drawn, Layer 1 -> False; every `tick` output validates as `Track` (`workshop.contracts.validate`); **AC-2.3-06 + integer check**: `ast` walk of `tracker.py` outside `_fraction`: no `ast.Div`, no float constants, no `float`/`round`/`math`; 200 seeded random finding/scroll sequences run twice -> identical outputs.
**Verify `tools/verify/2.3.1.ps1`** (< 30 s): `uv run pytest workshop/twin/tests/test_tracker.py -q`; `uv run --locked ruff check workshop/twin/tracker.py workshop/twin/tests/test_tracker.py`. Ends `VERIFY 2.3.1: PASS`.
**Human:** none.

### 2.3.2 Mask planner and memory
**Goal:** tracks -> clean MaskPlans; a picture-hash fingerprint cache. **Owned:** `workshop/twin/planner.py`, `workshop/twin/cache.py`, `workshop/twin/tests/test_planner.py`, `workshop/twin/tests/test_cache.py`, `tools/verify/2.3.2.ps1`.
**Steps:** 1. `planner.py` per section 2. Tests: only confirmed, non-peeked drawn; pad 4/6/10% of the short side (200x100 balanced -> +6 each side), clipped; Light drops a 20x40 Layer 2 track but keeps a 20x40 Layer 1; overlapping same-layer masks merge, L1/L2 never merge; 40 scattered tracks -> exactly 24 masks and every track rect still inside some mask; styles: L1 solid/not peekable in all modes, L2 blur/blur/solid, `solid_only` -> solid; label text; `post_bounds` used for `wholeElement`; every plan validates as `MaskPlan`; same `ast` integer check as 2.3.1. 2. `cache.py` per section 2. Tests (**AC-2.3-07**): 1,000 different crops = the first 1,000 non-overlapping 128x128 windows passing `usable`, cut from `workshop.recordings.synth_session._canvas("feed", 12800, seed)` for seeds 1.. (read-only use of the private helper; if it is gone, use any seeded textured image); put all with fingerprints tagged by index; query each exact crop and a near-duplicate (2 px shift + brightness +4): wrong reuse (returned tag != own index) must be 0 of 2,000 (< 0.1%), print near-duplicate hit rate; if wrong reuse > 0, lower `max_dist` (not below 2) and record the value; LRU eviction at capacity (use capacity 10 in the test); `ttl_ms` expiry; `clear()` empties; **fingerprints not verdicts**: entries hold only the vector, and a toy verdict `cos(fp, concept) >= thr` flips when the concept list changes, with no cache clear.
**Verify `tools/verify/2.3.2.ps1`** (< 1 min): pytest both test files (print the hit rate line `CACHE near-dup hit <pct>% wrong <n>/2000`); `uv run --locked ruff check workshop/twin/planner.py workshop/twin/cache.py workshop/twin/tests/test_planner.py workshop/twin/tests/test_cache.py`. Ends `VERIFY 2.3.2: PASS`.
**Human:** none.

### 2.3.3 Motion evaluation and golden tapes
**Goal:** wire it all into the 2.1 player, score, apply the gate, freeze golden tapes. **Owned:** `workshop/twin/oracle.py`, `workshop/twin/motion.py`, `workshop/twin/motion_synth.py`, `workshop/twin/goldens.py`, `workshop/twin/tests/motion_stubs.py`, `workshop/twin/tests/test_motion.py`, `workshop/eval/score_motion.py`, `workshop/eval/tests/test_score_motion.py`, `contracts/tapes/**`, `veil/.gitattributes` (one appended line), `docs/reports/ch2-motion.md` (append section `## Steady covers (Phase 2.3)` only), `docs/reports/media/ch2-*.mp4`, `tools/verify/2.3.3.ps1`, `tools/verify/pt-2.3.ps1`. Do not edit `workshop/replay/`, `workshop/recordings/` or 2.2 files.
**Steps:**
1. `oracle.py`, `motion.py` per section 2. CLI `python -m workshop.twin.motion eval --sessions DIR... --out DIR [--modes light,balanced,strict] [--rule on|off] [--detector oracle|real] [--solid-only] [--video balanced|none]`: replays each session per mode with `self_capture=True, markers=False`, writes `scores.json` and, for Balanced, side-by-side `<id>.sbs.mp4` (ffmpeg `hstack` of `<id>.mp4` and `<id>.covered.mp4`); prints `AC-2.3-01..05: PASS|FAIL <value>` (Balanced, aggregated over sessions; 02 per session) and `GATE ch2 (synthetic): PASS|FAIL` (the four Chapter 2 gate lines).
2. `motion_synth.py`: `generate(out_dir, script, seed) -> Path` with scripts `feed` (6 s: cats and a spider in a feed, slow scroll down then fling back and forth twice), `reels` (6 s: fast Reels swipes, -1600 over 4 frames, cat on every other card), `video` (6 s: flat scene, hard cut onto a cat, ContentChanged event), `torture` (24 s: fling back and forth over a cat 10 times, 6 fast Reels swipes, 3 cuts from a scene onto a cat). Same file set as 2.1.1 (`.mp4` 360x800 via `workshop.recordings.downscale`, `.events.jsonl`, `.session.json`, `.truth.jsonl`, label with keyframes <= 500 ms and `clean` spans). Reuse 2.1.1 drawing helpers read-only, or draw with cv2. `ensure_test_set("data/ch2/synth-test")`: `synth_session.generate(..., "synth-test-3", seconds=30, seed=3)` and seed 4, plus `torture` seed 22, skipped when present.
3. `score_motion.py`: `score(session_json, tape_out, label) -> dict` per section 2 metric definitions (keys `appearances, ttc_median_ms, ttc_p95_ms, coverage_pct, flicker, flicker_per_min, wrong_covers, wrong_per_min, wrong_sec_per_min, clean_min, glue_median_px, analysed_pct, recover_max_ms, cache:{situation:{hits,misses,hit_pct}}`; situation per frame as 2.2.3 budget: feed/grid + Scrolled within +-300 ms = `feedScroll`, `reels`, `video`, else `static`), `marks(...) -> list[dict]` (every late cover > 300 ms, flicker, slide = glue > 16 px, wrong cover, with tMs), CLI `python -m workshop.eval.score_motion SESSION TAPE_OUT LABEL`. Tests on hand-built mini tapes: one flicker counted, a 1.2 s gap not counted, a hidden-run miss is infinity, a wrong cover on a clean frame counted once.
4. `goldens.py`: `freeze(out="contracts/tapes")`: for `feed`, `reels`, `video` (seeds 31/32/33): Balanced replay, self-capture on, oracle seed 0, `use_cache=False`, `video=False`; tape-in = player tape-in + `findings_log` merged (each finding record placed right before its delivery frame, `seq` renumbered); writes `contracts/tapes/{feed-scroll,reels,video}.tape-{in,out}.jsonl` and `tapes.json` (name, sessionId, mode, oracle params, frames, sha256 of both files). `check(dir) -> bool`: every line validates (`workshop.replay.tape`), `run_tape` twice == stored tape-out records (kinds change/look/tracks/maskPlan, ignoring `seq`), and == each other. CLI `freeze|check`.
5. Tests: `run_tape` on a fresh replay == live tape-out; `findings_log` merge order; stub-free import of real tracker/planner/cache/gatekeeper.
6. Report: append `## Steady covers (Phase 2.3)` with per-mode table (5 PLAN metrics + glue), cache hit rate per situation, PT-2.3 torture numbers, the synthetic gate decision (PASS or FAIL + fallback run numbers), DV list, links to 3 videos `docs/reports/media/ch2-{feed,reels,video}.mp4` (sbs of the golden sessions, `-crf 30`, each <= 1 MB).
**Verify `tools/verify/2.3.3.ps1`** (< 5 min): pytest `test_motion.py` + `test_score_motion.py`; `ensure_test_set`; `motion eval` on `synth-test-3`, `synth-test-4` (all 3 modes, Balanced video) -> prints the AC lines and a `GATE ch2 (synthetic):` line (the script passes on the gate being *recorded* in scores.json and the report, not on its value); `goldens check contracts/tapes` OK with >= 3 tapes; `uv run --locked ruff check` on all owned `.py` files. Ends `VERIFY 2.3.3: PASS`.
**Human:** reviewer pass (section 5), real recordings (section 6).

## 4. Acceptance criteria
| AC | Kind | How checked | Threshold (PLAN, word for word) |
| --- | --- | --- | --- |
| AC-2.3-01 | AUTO (synthetic) / PENDING-HUMAN (real) | `motion eval` Balanced | Time to cover, p95 ≤ 0.3 s (Balanced, test recordings) |
| AC-2.3-02 | AUTO (synthetic) / PENDING-HUMAN (real) | `motion eval`, per session | 0 flicker events in every test session with self-capture on |
| AC-2.3-03 | AUTO (synthetic) / PENDING-HUMAN (real) | `motion eval` | ≤ 1 wrong cover per minute on clean stretches |
| AC-2.3-04 | AUTO (synthetic) / PENDING-HUMAN (real) | `motion eval` | ≥ 95% of the time a concept is visible, it is covered |
| AC-2.3-05 | AUTO (synthetic) / PENDING-HUMAN (real) | `motion eval` glue | Median gap between cover and labelled box ≤ 8 px during scrolls |
| AC-2.3-06 | AUTO | 2.3.1 + 2.3.2 unit tests | Layer 1 covers are solid, appear on first sighting, and cannot be peeked |
| AC-2.3-07 | AUTO | 2.3.2 cache test; report table | On 1,000 different crops, wrong reuse < 0.1%; hit rate reported per situation |
| AC-2.3-08 | AUTO | `goldens check` | ≥ 3 tapes (feed scroll, Reels, video); each validates and replays to identical outputs twice |
| GATE ch2 | AUTO (synthetic) / PENDING-HUMAN (real) | `motion eval` Balanced on test sessions | every concept appearance is covered within **0.3 s** of becoming visible (95% of appearances); **zero flicker events** (a cover disappearing and reappearing on the same item within 1 s); fewer than **one wrong cover per minute** on clean recordings; the system analyses fewer than **15% of frames**. |
| PT-2.3 | AUTO (machine) / HUMAN (reviewer) / PENDING-HUMAN (phone torture) | section 5 | The reviewer's marks agree with the motion scorer, and AC-2.3-01 to AC-2.3-05 hold. |

## 5. Proof test PT-2.3 "Watch it like a user"
**Machine part, `tools/verify/pt-2.3.ps1`** (< 4 min, run after 2.3.3 passes): `ensure_test_set`; `motion eval` Balanced on `synth-test-3`, `synth-test-4` and `torture-22` with self-capture on -> sbs videos for every session in `progress/ch2-motion/phase-2.3-steady-covers/evidence/pt-2.3/` (gitignored data stays out of git) + `marks-machine.csv` from `score_motion.marks`; checks on torture: `flicker == 0` ("No flicker anywhere"), `glue_median_px <= 8` on fling frames ("Covers stay glued during fast flings"), `recover_max_ms <= 34` ("A cat scrolled away and back is covered again immediately"), `ttc_median_ms <= 300` ("Covers usually appear before the reviewer can make out the cat"); then the same torture with `--rule off` and prints `INFO rule-off flicker=<n>` (shows the self-capture rule matters; informational). Prints `PT-2.3 machine: PASS|FAIL`.
**Human part (about 15 min):** a reviewer who did not build the Follower opens the sbs videos at normal speed (synth-test-3, synth-test-4, torture-22), writes `marks-human.csv` (`tMs,session,type` with type late|flicker|slide|wrong), then runs `uv run python -m workshop.eval.score_motion agree marks-machine.csv marks-human.csv` (match = same type within 500 ms; 2.3.3 adds this subcommand). Pass = every human mark matched and no machine flicker/wrong mark the human disagrees with. Real torture recording on the phone: PENDING-HUMAN.

## 6. Human items (paste into HUMAN_CHECKS.md)
```
- [ ] HC-2.3 Steady covers (Phase 2.3)
  1. Reviewer pass (~15 min, laptop): someone who did not build the Follower watches
     progress/ch2-motion/phase-2.3-steady-covers/evidence/pt-2.3/*.sbs.mp4 at normal speed,
     writes marks-human.csv (tMs,session,late|flicker|slide|wrong) and runs
     tools\with-env.ps1 uv run python -m workshop.eval.score_motion agree <machine.csv> <human.csv>
  2. PENDING-HUMAN (phone): record a torture session (fling back and forth over a cat 10 times,
     swipe Reels fast, cut from a scene onto a cat) with workshop.recordings.record, label it,
     then run: tools\with-env.ps1 uv run python -m workshop.twin.motion eval --sessions data/recordings --modes balanced
  3. PENDING-HUMAN (real gate): same command on the frozen real test recordings; record the real
     Chapter 2 gate decision next to the synthetic one in docs/reports/ch2-motion.md.
  4. DEFERRED: --detector real (Judge on looks only) on one dev session, alone, in the background.
```

## Amendment A1 (gate repair)
MODEL: claude-opus-5-5 (Repair Refiner) · 2026-10-02 · Earlier text unchanged. Experiments: in-memory monkeypatches of `MotionPipeline`/`Tracker`, replayed on synth-test-3+4 Balanced (`video=False`, `use_cache=False`). The baseline came out identical to the Builder's run (cov 74.97%, wrong 8, analysed 11.0%). No repo file was edited except this one.

### A1.1 Root causes (evidence)
1. **RC-1: self-capture drops covers on the first scroll frame (tracker bug, 2.3.1).** `tick` compares the track rect, *already shifted* by `on_scroll`, with `frame["ownOverlay"]`, which is the *previous* plan and is not shifted. At synth-test-3 t=3500 (dy -48), spider track 1 and cat track 3 fall to 76-78% self-covered. That is below 80 and past their hold, so both are released. The swipe look at 3500 cannot see them (oracle: >= 50% under our own cover counts as hidden), and the next looks are bottom strips, so feed-cat-3 stays uncovered. This breaks PLAN 2.3.1 rule 5 ("stays covered until the item scrolls away"). This fix on its own lifts coverage from 74.97% to 76.32%.
2. **RC-2: the confirm look is starved (motion bug, 2.3.3). This is the real form of Builder cause (a).** DV-4 confirm looks wait `min_immediate_gap_ms` (250) after *any* look, and they never fire on a frame where the gatekeeper already looked. Gatekeeper strip looks do not include the tentative track. Example: synth-test-3 feed-cat-4 (onset 3566, visible 733 ms) is sighted by the 3766 strip and is tentative from 3866. The next looks are the 4033 strip (y 1375-1600, which misses it) and the 4300 scene cut, so it is never covered (INF). Same pattern: feed-cat-6 @13366, feed-cat-8 @23166, grid-cat-23 @5433, grid-spider-27/29 @15666. On grid/feed cuts the 1st look is at t, the track is tentative at t+100 and the confirm look only comes at t+266, giving ttc 366 (the median). I also tested lowering `min_immediate_gap_ms` to 150 instead: analysed rose to 15.33% (gate needs < 15%) and p95 did not improve. **params.json stays at 250, so no 2.2 AC needs re-checking.**
3. **RC-3: covers outlive a hard scene switch (tracker rule, 2.3.1 / DV-5). This confirms Builder cause (b).** Wrong-cover episodes s3 16300/17766/27566 and s4 6500/16300/26100/27566 all come from tracks of the previous scene that keep their normal 1.5 s hold. Example: grid tracks 47-51 (y 1285-1528) survive the grid->reels cut @16300, then Reels swipes drag them across clean frames. This explains 6 of the 8 episodes.
4. **RC-4: the scorer counts never-covered short runs as infinity (definition gap, 2.3.3).** After the RC-1..3 fixes, 15 of the 18 remaining INF appearances are visible runs of 166-199 ms (an app peek before screen-off @9633/19433/29233, Reels @26100). With confirm-after-2 and 100 ms latency, a Layer 2 item cannot be covered in under 233 ms. So these runs can never score, while a cover that arrives 600 ms late gets a finite score. This is not a tracker bug: the frozen definition is harsher than PLAN's wording requires.
5. **RC-5: oracle noise is independent per look (harsh, contributing).** The 3% miss and 3% nearMiss are redrawn on every frame, so P(2 consecutive hides) = 0.94^2 = 0.88. About 12% of appearances therefore need a 3rd look (>= 366 ms), which alone exceeds the 5% budget for p95. An ideal oracle (0/0/0) only raises the share covered within 300 ms from 80.9% to 85.8%. The noise contributes but is not the main cause.
6. **Not a bug, but decisive: clean time is only 0.343 min.** "< 1 wrong cover/min" therefore means **zero** episodes across both sessions (a single episode = 2.9/min).
7. **Open (not root-caused within the time box):** the remaining wrong episodes s3 6700 and s4 7300/17100 (Reels). At s3 6500 I saw a grid->reels switch with 31 changed tiles but no `sceneCut`, so stale self-captured grid tracks survive into Reels. A motion-side "big change = cut" rule (>= 28 tiles, no scroll) did not remove them. The Builder should inspect this; do not tune further.

### A1.2 Exact changes (one Sonnet Builder, ~15 min)
- **2.3.1 `workshop/twin/tracker.py`**
  - (a) RC-1: in `__init__`, set `self._dy = 0`. In `on_scroll`, add `self._dy += dy` after shifting tracks. In `tick`, make the first line `own_covers = [dict(c, y=c["y"] + self._dy) for c in own_covers]; self._dy = 0`.
  - (b) RC-3: `on_scene_cut` sets `self.tracks = []`, which releases all tracks, Layer 1 included. This replaces the `cut` flag behaviour. Amended DV-5: a scene cut ends every cover, and the cut look re-finds whatever is still there.
  - Tests in `test_tracker.py`: a scroll of dy -48 with our own cover at the old position keeps a self-captured track; after a scene cut, `tick` returns []. The determinism and integer AST checks are unchanged.
- **2.3.3 `workshop/twin/motion.py` `_step`** (RC-2)
  - Compute these once: `rect = self._confirm_rect(frame)` and `fresh = any(tr.state == "tentative" and tr.last_seen > self.last_start for tr in self.tracker.tracks)`.
  - If there is no gatekeeper look, fire a confirm look when `rect and fresh and t >= self.gk.busy_until`. This drops the `min_immediate_gap_ms` test.
  - If a gatekeeper look happened and `rect` is not None, set `look["rect"] = union_bbox(look["rect"], rect)`. This piggybacks on the existing look and adds no extra look.
  - New DV-4 text: "confirm look as soon as the detector is idle after a new tentative sighting; gatekeeper looks are widened to include tentative tracks".
  - Tracks and looks change, so the golden tapes must be re-frozen (`goldens freeze`, then `check`) and AC-2.3-08 re-checked.
- **2.3.3 `workshop/eval/score_motion.py`** (RC-4, **only if the user accepts the definition change**): a visible run that ends uncovered scores `ttc = run end - onset` (uncovered exposure) instead of infinity. A run that is never covered and still visible at session end stays infinity. Report both p95s (old and new definition) in `ch2-motion.md`.
- **2.2.3 `params.json`**: no change (gap 150 was tested and rejected). AC-2.2-05/06 are unaffected.

### A1.3 Predicted Balanced numbers after A1.2 (measured in the experiments)
| Metric | Before | After RC-1..3 fixes | Ideal oracle (bound) | Gate |
| --- | --- | --- | --- | --- |
| ttc median | 366 ms | 233 ms | 233 ms | - |
| ttc p95 (frozen def.) | INF (37 INF) | INF (18 INF) | INF | <= 300 ms |
| ttc p95 (exposure def., RC-4) | - | 600 ms (80.9% <= 300) | 434 ms (85.8%) | <= 300 ms |
| coverage | 74.97% | 82.8% | 83.7% | >= 95% |
| flicker | 0 | 0 (torture-22: 5 -> 0) | 0 | 0 |
| wrong / min | 23.3 (8) | 8.7 (3) | 8.7 (3) | < 1 |
| analysed | 11.0% | 12.7% | 12.4% | < 15% |
| glue median | 2 px | 2 px (torture 3 px) | 2 px | <= 8 px |

torture-22 re-cover max: 367 -> 234 ms (PT limit is 34 ms, so still FAIL).

### A1.4 Honest verdict
**The Chapter 2 gate cannot be met on these synthetic sessions with Balanced as PLAN defines it.**
- The floor for a Layer 2 cover is first look + 100 ms + one frame + 100 ms = 233 ms, and that is for an item already inside a look.
- Items scrolling in wait up to 250 ms for the next strip look.
- Oracle noise forces a third look on about 12% of appearances.

So even with a perfect detector, 14% of appearances take longer than 0.3 s (the gate needs 95% within it), and coverage tops out near 84% (the gate needs 95%). Zero wrong covers in 0.343 clean minutes leaves no margin. The PLAN fallback (solid, holds x2, rates x2) does not change this floor (measured: 300 ms median, 77.8% coverage). Thresholds are not changed here.

The smallest honest options for the user to decide:
- **W1 (recommended):** apply A1.2, since RC-1 (which breaks PLAN rule 5), RC-2 and RC-3 are real bugs. Re-run, and record the synthetic gate as **FAIL with known floor**. Let the **real-recording gate (PENDING-HUMAN)** decide. Mark the synthetic gate as informational (DV-2), because the 100 ms oracle latency is an assumption, not a measurement ("Out of scope: real phone timing").
- **W2 (design change to PLAN 2.3.1 rule 3):** Balanced covers on the first `hide` sighting when probability >= 0.9 (a provisional cover); confirm-after-2 applies only to lower-confidence findings. This would lower the floor to about 133 ms. It must be re-measured for wrong covers and flicker before adoption, and it needs the user's sign-off because it changes a PLAN rule.
- **W3 (measurement):** accept RC-4's exposure definition, which needs sign-off because metric definitions are frozen for Ch 5. Also lengthen the clean stretches in `synth_session` to at least 3 clean minutes, so "< 1 per minute" can be measured instead of meaning "zero events".
