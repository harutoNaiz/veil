# SPEC: Phase 2.1 Recordings and replay

MODEL: claude-opus-5-5 · Status: APPROVED (orchestrator, tape.schema.json as an allowed 17th file noted for HC-010) · PLAN lines used: 553-666 (Ch 2 intro + Phase 2.1), skimmed 668-878 (2.2 change detector/scheduler, 2.3 tracker/planner/cache/golden tapes).

## 1. Deviations and risks
- **DV-1 Synthetic first.** Phone not connected. Builders build all tooling and prove it on SYNTHETIC sessions with exact truth. Real 10-15 min recordings, labels, second-person review: **Human** (HC item, section 6). AC-2.1-01/02/04 stay PENDING-HUMAN.
- **DV-2 Event logger.** 4.2.1 logger does not exist. `record.py` uses the frame-difference estimator (`estimated: true`) and has a `--events FILE` hook for the logger later.
- **DV-3 Tape schema location.** `contracts/tape.schema.json` is an *extra* schema, not one of the 16 contract types (no codegen, not in `TYPE_FILES`). `contracts/tests/test_schemas.py::test_exactly_16_schema_files` asserts exactly 16 files, so 2.1.3 changes it to allow `{"tape.schema.json"}` as the only extra file. Contracts v1.0 types are not changed.
- **DV-4 Recording-label schema** lives in `workshop/labels/recording-label.schema.json` (workshop format, not a contract).
- **DV-5 Working size.** Downscale = uniform scale to width 360, then pad (black, bottom) or crop to height 800. Mapping: `x_f = x_s*360//screenWidth`, `y_f = y_s*360//screenWidth`. Synthetic screen is 720x1600 (exact factor 2).
- **DV-6 Labelling tool.** Label Studio *video* labelling (VideoRectangle, native keyframes + interpolation), using the existing `tools/label-studio.ps1`, plus a converter. The 1.2 image converters do not carry box identity over time, so they are not reused.
- **Risk:** the LS video export shape is written from docs; the first real export may need a converter fix (human check). **Risk:** CRLF (`core.autocrlf=true`): tapes are written in binary with `\n`; determinism compares freshly written files, never checked-out ones.
- **Risk:** x264 output is not bit-exact across machines; determinism covers tapes only, never MP4s.
- **Deferred:** none heavy. No models in this phase (dummy pipeline only). No new deps (numpy, opencv, jsonschema present; ffmpeg on PATH via `with-env`).

## 2. Shared interfaces (all Builders start from these)
All Python runs as `powershell -NoProfile -ExecutionPolicy Bypass -File tools\with-env.ps1 uv run python ...` from `D:\iqoo finale\veil`. Times are integer ms; rects are `{x,y,w,h}` ints in **screen px** unless named `*_f` (frame px).

**Session files** (folder `data/recordings/` for real, any temp dir for tests), stem `<id>`:
- `<id>.orig.mp4` original (optional for synthetic), `<id>.mp4` 360x800 working copy.
- `<id>.events.jsonl`: one UiEvent v1.0 per line (`Scrolled`, `WindowChanged`, `ScreenOff`, `ScreenOn`, `ContentChanged`), `eventId` from 0, sorted by `(tMs, eventId)`.
- `<id>.session.json`:
```json
{"sessionVersion":"1","sessionId":"synth-known-scroll","video":"synth-known-scroll.mp4","fps":30,
 "frameCount":600,"t0Ms":1000,"width":360,"height":800,"screenWidth":720,"screenHeight":1600,
 "scroll":"synthetic|logged|estimated","source":"synthetic|phone","packageName":"com.veil.synth",
 "situations":{"slowScroll":2,"fling":2,"reelsSwipe":2,"exploreGrid":2,"videoSceneCut":2,"appSwitch":2,"lockUnlock":2}}
```
  Frame `i` is at `tMs = t0Ms + (i*1000)//fps` (same clock as events).
- Synthetic only: `<id>.truth.jsonl`, one line per frame: `{"i":0,"tMs":1000,"scrollY":0,"scene":"feed|reels|video|grid|other|off","boxes":[{"key":"cat-3","conceptId":"cats","rect":{...}}]}` and `<id>.driver.json`: `[{"tMs":..,"dy":..}]` = the known scroll script (screen px, sign as UiEvent: negative = content moved up).

**Recording label** `data/labels/recordings/<id>.json` (schema `workshop/labels/recording-label.schema.json`, 2.1.2 owns; 2.1.1 writes it for synthetic sessions):
```json
{"labelVersion":"1","sessionId":"..","durationMs":20000,"screenWidth":720,"screenHeight":1600,
 "labeller":"synth","reviewedBy":null,
 "tracks":[{"key":"cat-3","conceptId":"cats","spans":[{"startMs":1000,"endMs":4200}],
            "keyframes":[{"tMs":1000,"rect":{"x":..,"y":..,"w":..,"h":..}}]}],
 "marks":[{"tMs":9000,"type":"sceneCut|appSwitch|lock|unlock"}],
 "clean":[{"startMs":..,"endMs":..}]}
```
Keyframes: at each span start and end and at most 500 ms apart inside spans; boxes in between are linearly interpolated with integer floor. `workshop.labels.recordings.boxes_at(label: dict, t_ms: int) -> list[dict]` (key, conceptId, rect).

**Tape v1** (`contracts/tape.schema.json`, 2.1.3 owns). Two JSONL files per replay: `<id>.tape-in.jsonl` (inputs) and `<id>.tape-out.jsonl` (expected outputs). Every line: `{"kind":..,"seq":int,"tMs":int,...}`, `seq` from 0 per file. Serialised with `json.dumps(obj, sort_keys=True, separators=(",",":"), ensure_ascii=False) + "\n"`, file opened `wb`. No wall-clock values, paths or hostnames in tapes. Kinds:
- in: `header` {tapeVersion:"1", sessionId, fps, width, height, screenWidth, screenHeight, selfCapture, pipeline}; `event` {event: UiEvent ($ref)}; `frame` {frameId, thumb: base64 of 32x64 (w x h) grayscale uint8 = 2048 bytes, `cv2.INTER_AREA` from the delivered frame, ownOverlay: [Rect]}; `finding` {finding: Finding}; `fingerprint` {embedding: Embedding}.
- out: `header` (same); `change` {frameId, changedTiles:int, sceneCut:bool, score:int}; `look` {frameId, look:bool, reason: enum sceneCut|appChange|swipe|revealedStrip|periodic|checkup|none|busy, state: enum idle|watching|hot|throttled, rect?: Rect}; `tracks` {frameId, tracks:[Track]}; `maskPlan` {frameId, plan: MaskPlan}; `cache` {frameId, hits:int, misses:int}.
- Every kind may carry `"x": {}` (free object) for stage-specific extras; nothing else is free. Contract types are `$ref`ed from the existing schemas.

**Pipeline protocol** (`workshop/replay/pipeline.py`, 2.1.3):
```python
class Pipeline(Protocol):
    name: str
    def on_event(self, event: dict) -> list[dict]: ...            # out records (no seq)
    def on_frame(self, frame_bgr: np.ndarray, frame: dict) -> list[dict]: ...  # frame = Frame contract dict
class DummyPipeline:   # name "dummy-v1": one fixed solid cover (screen px) shifted by every Scrolled dy;
    def __init__(self, rect: dict | None = None): ...  # emits one maskPlan per frame (reason "look" first, then "scroll"/"look")
class OraclePipeline:  # name "oracle-v1": maskPlan = truth boxes of that frame (needs <id>.truth.jsonl), solid
    def __init__(self, truth_path: Path): ...
```
**Player** (`workshop/replay/player.py`):
```python
def replay(session_json: Path, pipeline: Pipeline, out_dir: Path, *, realtime=False, speed=1.0,
           self_capture=False, markers=False, video=True, solid_bgr=(40,40,40)) -> ReplayResult
@dataclass class ReplayResult: frames:int; events:int; tape_in:Path; tape_out:Path; video:Path|None;
           timing:Path; late_frames:int; max_lag_ms:int
```
Rules: merge events and frames by `(tMs, 0 for event / 1 for frame, eventId|frameId)` so events at t come before the frame at t. `VirtualClock` (`clock.py`: `now()`, `advance_to(t)`; never goes back). Realtime: sleep until `wall0 + (t - t0)/speed`, log lag per frame to `<id>.timing.json`. Self-capture: the frame given to the pipeline at N+1 has plan N's covers painted (solid, `solid_bgr`) and `ownOverlay` = plan N rects. Covered video `<id>.covered.mp4` = frame N with plan N painted (+ markers: a 6 px red bar at the top and text `dy=<sum>` on every frame that got a Scrolled event). MP4 via ffmpeg pipe (`rawvideo bgr24 -> libx264 -pix_fmt yuv420p -crf 23`), fallback cv2 `mp4v`.
**Renderer** (`render.py`): `paint(frame_bgr, plan: dict, screen_width: int, solid_bgr) -> np.ndarray` (solid fill / Gaussian blur / mosaic by `style`).
**CLIs:** `python -m workshop.replay SESSION.session.json --out DIR [--pipeline dummy|oracle] [--realtime] [--self-capture] [--markers] [--no-video]`; `python -m workshop.replay.tape validate FILE...` (prints `OK <file> <n> lines` / `INVALID <file>:<line>: <msg>`, exit 0 only if all valid).

## 3. Sub-phases (all three run in parallel)

### 2.1.1 Record sessions (tooling + synthetic sessions)
**Goal:** phone recording tooling for the human, and a synthetic session generator with exact truth.
**Owned:** `workshop/recordings/**`, `tools/verify/2.1.1.ps1`.
**Files:** `workshop/recordings/{__init__,synth_session,estimate,downscale,record,index,sync_check}.py`, `workshop/recordings/tests/test_recordings.py`.
**Steps:**
1. `synth_session.py`: `generate(out_dir, session_id="synth-known-scroll", seconds=20, seed=7, event_offset_ms=0) -> Path` (session.json). Render at 720x1600, 30 fps, deterministic: a tall feed canvas of cards (reuse the shape drawers in `workshop/screens/synth.py`, cats/spiders/dogs, harmless), then a script: pause 1 s; slow scroll (dy -6/frame) 2 s; pause; fling (decelerating, even dy); pause; Explore-like grid scroll; Reels swipe (full-screen card, -1600 over 8 frames) x2; "video" scene with a hard scene cut (ContentChanged event + label mark); app switch (WindowChanged to `com.veil.other` and back); lock/unlock (ScreenOff, 1 s black, ScreenOn). Each situation at least twice when `seconds >= 20`. One Scrolled event per moved frame, `tMs` = that frame's time + `event_offset_ms`. Writes `.orig.mp4` (x264 `-crf 12`), runs `downscale`, writes `.events.jsonl`, `.session.json`, `.truth.jsonl`, `.driver.json`, and the recording label to `<out_dir>/labels/<id>.json` (keyframes every 500 ms). CLI `python -m workshop.recordings.synth_session --out DIR [--seconds N] [--event-offset-ms N]`.
2. `downscale.py`: `downscale(src, dst, width=360, height=800)` with ffmpeg (`scale=360:-2`, pad/crop to 800, keep original).
3. `estimate.py`: `estimate_scroll(video, screen_width, package) -> list[dict]` Scrolled events with `estimated: true`; row-profile shift search on consecutive grey frames (integer dy in frame px, x screen factor); no event when the best shift is 0 or the match is poor.
4. `sync_check.py`: `check(session_json, samples=10) -> dict`: pick 10 scroll bursts evenly, find visible-movement onset with the estimator, offset = logged tMs - onset; writes `<id>.sync.csv`; pass iff every |offset| <= 33 ms. CLI prints `SYNC <id>: PASS|FAIL max=<ms>`.
5. `record.py` (phone, human-run): `--name N --seconds S [--situations a,b] [--events FILE] [--out data/recordings] [--dry-run]`. Phone uptime at start -> `t0Ms`; `adb shell screenrecord --bit-rate 8000000 --time-limit 180` in segments; pull; ffmpeg concat; downscale; events from `--events` (logger) else `estimate.py` (`scroll:"estimated"`); writes session.json. `--dry-run` prints the adb/ffmpeg commands only.
6. `index.py`: scans a folder of `*.session.json`, writes `index.json`, prints AC-2.1-01 (total >= 600 s, each of 7 situations >= 2) and AC-2.1-02 (>= 3 `logged`) as PASS/FAIL.
**Verify `tools/verify/2.1.1.ps1`** (< 2 min): pytest the tests; generate a 20 s session in a temp dir; every events line validates as UiEvent (`workshop.contracts.validate --type UiEvent --jsonl`); working copy is 360x800 with 600 frames (ffprobe); estimator dy within +-1 frame px of truth on >= 90% of moved frames and 0 events in pauses; sync check PASS on offset 0 and FAIL on `--event-offset-ms 100`; `record.py --dry-run` prints `screenrecord`; index reports the synthetic situations correctly. Ends `VERIFY 2.1.1: PASS`.
**Human:** real recordings (section 6).

### 2.1.2 Label recordings (format, tools, split and freeze)
**Goal:** a labelling path for humans and the checks behind AC-2.1-04.
**Owned:** `workshop/labels/recordings.py`, `workshop/labels/recording-label.schema.json`, `workshop/labels/ls_video_config.xml`, `workshop/labels/tests/test_recordings.py`, `workshop/labels/tests/fixtures/ls-video-*.json`, `tools/verify/2.1.2.ps1`.
**Steps:**
1. Schema (section 2 shape, `additionalProperties:false`, ints, `type` enums) + `validate(label) -> list[str]` rule errors: keyframes sorted and inside spans, gap <= 500 ms, span start/end keyed, clean stretches do not overlap spans.
2. `boxes_at(label, t_ms)` with integer linear interpolation.
3. `ls_video_config.xml` (Video + VideoRectangle, labels = concept ids from `docs/labelling-rules.md`; TimelineLabels/Choices for marks and clean) and `from_ls(export: dict, session_json) -> dict` (LS percent boxes -> screen px; frame -> tMs; keep LS keyframes; resample so gaps <= 500 ms).
4. `agree(a, b) -> float` disagreement: sample every 500 ms over the session; boxes match if same concept and IoU >= 0.5; disagreement = unmatched / total boxes (both sides); plus marks more than 500 ms apart count as unmatched.
5. `split_freeze(labels_dir, recordings_dir) -> dict`: sorted sessionIds, sha256-ranked; test = round(n/3) (>= 1), rest dev; writes `split.json` and `FROZEN.sha256` (sha256 of each test session's `.mp4`, `.events.jsonl`, label json). `check_frozen(...) -> bool`.
6. CLI `python -m workshop.labels.recordings validate|agree|from-ls|split-freeze|check-frozen ...`.
**Verify `tools/verify/2.1.2.ps1`** (< 1 min): pytest: valid + 2 invalid hand fixtures; interpolation exact at keyframes and midpoint; agree = 0.0 on identical, expected value on a fixture with 1 of 10 boxes moved; split of 6 fake sessions = 4 dev / 2 test; check-frozen passes, fails after one byte is changed; `from-ls` on the fixture produces a label that validates. Ends `VERIFY 2.1.2: PASS`.
**Human:** label real sessions in Label Studio; second person reviews one full session.

### 2.1.3 Replay harness and tape v1
**Goal:** player with a virtual clock, cover renderer, self-capture, tape v1 + writer + validator.
**Owned:** `workshop/replay/**`, `contracts/tape.schema.json`, `contracts/examples-tape/` (2 valid + 2 invalid lines), `contracts/tests/test_schemas.py` (extra-file allowance only), `tools/verify/2.1.3.ps1`, `tools/verify/pt-2.1.ps1`.
**Files:** `workshop/replay/{__init__,__main__,clock,pipeline,player,render,tape,checks}.py`, `workshop/replay/tests/{fixture,test_replay}.py`.
**Steps:**
1. `tape.schema.json` (draft 2020-12, `oneOf` by `kind`, `$ref` to existing schemas; validator builds a registry from `workshop.contracts.validate.registry()` plus the tape schema). `TapeWriter(path, header)` with `.write(record)` assigning `seq`.
2. `clock.py`, `pipeline.py`, `render.py`, `player.py`, `__main__.py` per section 2.
3. `checks.py`: `self_capture_error(session_json, frames=60) -> int` (wraps the pipeline, captures the frames it receives, finds the bbox of `solid_bgr=(255,0,255)` pixels in input N+1, returns max px error vs plan N rects in frame px); `scroll_totals(tape_in) -> list[int]` (summed dy per scroll burst); CLI `python -m workshop.replay.checks self-capture|scroll-totals ...`.
4. `tests/fixture.py`: builds a 3 s, 360x800, 30 fps session (moving bars, known Scrolled events) with cv2 only, so 2.1.3 does not wait for 2.1.1.
5. `pt-2.1.ps1` (section 5); it needs 2.1.1's generator, so run it once both exist.
**Verify `tools/verify/2.1.3.ps1`** (< 2 min): pytest: event at t delivered before frame at t; two full-speed replays -> identical sha256 of both tape files; `self_capture_error <= 1`; every tape line validates and the invalid examples fail; realtime run of the 3 s fixture: wall time <= 3.5 s and >= 95% of frames within 33 ms of due time; covered MP4 exists and ffprobe frame count = 90. Also `uv run pytest contracts -q` passes. Ends `VERIFY 2.1.3: PASS`.
**Human:** watch one covered video (section 6).

## 4. Acceptance criteria
| AC | Status | How it is checked | Threshold (PLAN, word for word) |
| --- | --- | --- | --- |
| AC-2.1-01 | PENDING-HUMAN | `index.py` on `data/recordings/` after human recording; tool proven on synthetic | ≥ 10 minutes total; every listed situation (slow scroll, fling, Reels swipe, Explore grid, video with a scene cut, app switch, lock/unlock) appears at least twice |
| AC-2.1-02 | PENDING-HUMAN (needs 4.2.1 logger) | `index.py` counts `scroll:"logged"` | ≥ 3 sessions have logged (not estimated) scroll events |
| AC-2.1-03 | AUTO (synthetic) + PENDING-HUMAN (real) | `sync_check.py` sheet; negative control at +100 ms must fail | On 10 sampled scrolls per session, the logged time is within ± 1 frame (33 ms) of the visible movement |
| AC-2.1-04 | AUTO (tools) + PENDING-HUMAN | `recordings.py agree/split-freeze/check-frozen` | 100% of sessions labelled; review disagreement ≤ 5%; test sessions frozen with a checksum |
| AC-2.1-05 | AUTO | sha256 of tape files, 2 runs (3 in PT) | Replaying the same session twice at full speed gives byte-identical tapes |
| AC-2.1-06 | AUTO | `<id>.timing.json`: wall ≤ duration + 0.5 s and ≥ 95% frames within 33 ms | Real-time mode keeps pace with the video using a dummy pipeline |
| AC-2.1-07 | AUTO | `checks.self_capture_error` unit test | With the option on, frame N+1 contains the covers from plan N, positioned within 1 px |
| AC-2.1-08 | AUTO | `python -m workshop.replay.tape validate` | Every tape line validates against the tape schema |

## 5. Proof test PT-2.1 "Known scroll replay"
**Machine part** `tools/verify/pt-2.1.ps1` (< 3 min), on a synthetic 60 s "known scroll" session:
1. `synth_session --seconds 60 --out data/evidence/pt-2.1/session` (driver script = `.driver.json`).
2. `sync_check` -> `SYNC: PASS` (AC-2.1-03); repeat with `--event-offset-ms 100` -> must FAIL.
3. Replay 3x full speed, `--pipeline oracle --markers`; sha256 of the 3 tape-in and 3 tape-out files identical (AC-2.1-05); write `hashes.txt`.
4. `checks scroll-totals` on the tape == the driver script per scroll, exactly.
5. Replay once with `--self-capture`; `self_capture_error <= 1` (AC-2.1-07).
6. `tape validate` on all tapes (AC-2.1-08); `recordings.py validate` on the synthetic label.
7. Evidence: `data/evidence/pt-2.1/{marked.covered.mp4,hashes.txt,sync.csv}`. Ends `PT 2.1: PASS`.
**Human part** (~20 min, phone + Test Feed): (a) install Test Feed; (b) `record.py --name pt21 --seconds 60` while in a second shell `python -m workshop.bench.drive` does known swipes (log its swipes); (c) run `sync_check` and the 3 replays with `--markers` on `pt21`; (d) watch `pt21.covered.mp4`: markers line up with movement within 1 frame; replayed dy totals match the Test Feed `feedlog.jsonl` scrollY changes. PT passes when AC-2.1-03, -05, -07 hold on this session.

## 6. Human items (paste into HUMAN_CHECKS.md)
```
HC-2.1 Recordings and replay (phone + test accounts only, ~2.5 h total)
[ ] Record >= 6 sessions, >= 10 min total: python -m workshop.recordings.record --name <n> --seconds <s> --situations ...
    Cover twice each: slow scroll, fling, Reels swipe, Explore grid, YouTube cat video with a scene cut,
    app switch, lock/unlock; plus pauses and a news site. Test accounts only, nothing explicit.
[ ] python -m workshop.recordings.index data/recordings  -> AC-2.1-01 PASS (AC-2.1-02 waits for the 4.2.1 logger)
[ ] python -m workshop.recordings.sync_check on every session -> SYNC PASS (AC-2.1-03)
[ ] Label every session in Label Studio (tools\label-studio.ps1, config workshop/labels/ls_video_config.xml),
    keyframes every 0.5 s, mark scene cuts, app switches, clean stretches; convert with recordings.py from-ls
[ ] A second person labels one full session; recordings.py agree A B -> <= 5% (AC-2.1-04)
[ ] recordings.py split-freeze, then check-frozen -> OK
[ ] PT-2.1 human part (SPEC section 5, ~20 min)
[ ] Watch one covered.mp4 from the synthetic PT run: covers sit on the shapes, markers on scroll frames
```
