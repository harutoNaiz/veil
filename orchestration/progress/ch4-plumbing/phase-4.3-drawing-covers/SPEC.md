# Phase 4.3 Drawing covers: SPEC
MODEL: claude-opus-5-5 · Status: APPROVED with amendment A1 (orchestrator): ONE production accessibility service only — the overlay is hosted by 4.2.1's Guard service via an OverlayHost interface; OverlayAccessibilityService may exist only in the debug source set for isolated testing · Source: PLAN.md lines 1403-1505 · Entry: 4.1 and 4.2 built (code against their SPEC §2 only)

## 1. Deviations and risks
1. **Own accessibility service.** 4.2.1 owns `GuardAccessibilityService`, so 4.3 adds `overlay/OverlayAccessibilityService` (manifest add-only, separate `res/xml/overlay_accessibility_service.xml`; enabled with `adb` on the debug build). Merging it into the Guard service is a one-line `OverlayHub.attach(this)` in a later phase (record as amendment).
2. **Taps vs long-press.** The drawing window is always `FLAG_NOT_TOUCHABLE` (pure pass-through). Only covers with `peekable=true` get a small touchable window: short taps and drags are replayed below via `dispatchGesture` (needs `canPerformGestures`), a hold ≥ 500 ms is a long-press. Risk: replayed swipes on peekable covers feel slightly late. Fallback: drop the touch windows (long-press off) and keep AC-01.
3. **ownOverlay on frames.** 4.1's `CaptureLog` writes `ownOverlay: []` and is not ours. 4.3 keeps `OwnOverlayRegistry` (rect history by `tMs`) and a joiner that fills `ownOverlay` into a copy of `frames.jsonl`. Wiring the registry into `CaptureLog` = one call, deferred to the first phase that touches it.
4. **Blur** cannot blur what is behind an overlay. Blur and mosaic both use a crop of the last captured frame (`FrameCropSource`); with no frame they draw solid. Label = optional text over the cover.
5. **Per-window screenshot** (`takeScreenshotOfWindow`) is API 34+; minSdk is 31, so guard by `SDK_INT`.
6. Phone not connected: all PHONE rows are scripts with `-Phone` (PENDING-HUMAN, F7). Drift over 30 s in 5 apps is DEFERRED-capable (F6) if > 5 min.

## 2. Shared interfaces (Wave 0: any Builder writes this file verbatim; 4.3.1 commits it; nobody edits it)
`guard/app/src/main/java/com/veil/guard/overlay/OverlayApi.kt`
```kotlin
package com.veil.guard.overlay
data class Px(val x: Int, val y: Int, val w: Int, val h: Int)
enum class CoverStyle { SOLID, BLUR, MOSAIC }
data class Cover(val maskId: Int, val rect: Px, val style: CoverStyle, val layer: Int, val peekable: Boolean, val label: String? = null)
data class CoverPlan(val planId: Long, val tMs: Long, val screenW: Int, val screenH: Int, val rotation: Int,
    val covers: List<Cover>, val reason: String)   // mirrors mask-plan.schema.json v1.0 (extra mask fields ignored)
data class DisplayState(val w: Int, val h: Int, val rotation: Int)
/** Pure. Covers that changed (added, removed, moved, restyled); empty = no redraw. */
data class PlanDelta(val added: List<Cover>, val removed: List<Int>, val changed: List<Cover>) { val isEmpty get() = added.isEmpty() && removed.isEmpty() && changed.isEmpty() }
interface OverlaySink { fun submit(plan: CoverPlan) }               // OverlayRenderer implements; any thread
fun interface FrameCropSource { fun crop(rect: Px): android.graphics.Bitmap? }
data class OwnOverlaySample(val tMs: Long, val rects: List<Px>)     // what was actually on screen from tMs on
fun interface OwnOverlayListener { fun onDrawn(sample: OwnOverlaySample) } // called after each drawn frame
sealed interface CoverGesture { val maskId: Int; val tMs: Long
    data class LongPress(override val maskId: Int, override val tMs: Long, val x: Int, val y: Int) : CoverGesture }
object OverlayHub {
    @Volatile var sink: OverlaySink? = null; @Volatile var crops: FrameCropSource? = null
    val drawnListeners = java.util.concurrent.CopyOnWriteArrayList<OwnOverlayListener>()
    val gestureListeners = java.util.concurrent.CopyOnWriteArrayList<(CoverGesture) -> Unit>()
}
```
Debug command receiver (4.3.1 registers, `android:permission="android.permission.DUMP"`, action `com.veil.guard.overlay.CMD`): extras `cmd` = `plan` (`value` = MaskPlan JSON) | `clear` | `glue` (`value`=`on|off|place:x,y`) | `peekprobe` | `selfcap` (`value`=`on|off`). 4.3.1 dispatches `glue/peekprobe/selfcap` to `OverlayHub`-registered handlers: `object OverlayCommands { val handlers = ConcurrentHashMap<String, (String?) -> Unit>() }` (in `OverlayApi.kt`, add this line).
Logs (app `files/overlay/`): `render.jsonl` `{planId,tRecvMs,tDrawnMs,vsyncPeriodMs,covers}`; `own.jsonl` `{tMs,rects}`; `glue.jsonl` `{tMs,x,y,eventDy,eventDx}`; `gestures.jsonl`; `peek.jsonl`.
Gradle: `powershell -NoProfile -ExecutionPolicy Bypass -File tools\with-env.ps1 --cd guard .\gradlew.bat --no-daemon :app:assembleDebug :app:testDebugUnitTest --tests "com.veil.guard.overlay.<Test>"` (2 GB cap already in gradle.properties). ktlint: `& "$env:JAVA_HOME\bin\java.exe" -jar "$env:VEIL_TOOLCHAIN\ktlint\ktlint.jar" <owned .kt>`. Python via `uv run --locked`, ruff on owned .py. Main code paths below are under `guard/app/src/main/java/com/veil/guard/overlay/`, tests under `guard/app/src/test/java/com/veil/guard/overlay/`.

## 3. Sub-phases (all three in parallel)

### 4.3.1 Overlay window and renderer
- **Goal:** draw a `CoverPlan` above every app, keyboard and status bar, touches pass through, redraw only on change.
- **Owned:** `overlay/{OverlayApi,OverlayAccessibilityService,OverlayRenderer,CoverView,PlanDiff,CoverGeometry,MaskPlanJson,OverlayCmdReceiver,RenderTrace}.kt`, `res/xml/overlay_accessibility_service.xml`, `res/values/overlay_strings.xml`, manifest (add service + receiver only), tests `{PlanDiffTest,CoverGeometryTest,MaskPlanJsonTest}.kt`, `workshop/overlay/{__init__,render_stats}.py`, `tools/verify/4.3.1.ps1`, `tools/phone/4.3.1-phone.ps1`.
- **Steps:**
  1. Service xml: `typeViewScrolled|typeWindowStateChanged`, `canRetrieveWindowContent="true"`, `canTakeScreenshot="true"`, `canPerformGestures="true"`, `flagRetrieveInteractiveWindows`. `onServiceConnected`: create renderer, set `OverlayHub.sink`; `onUnbind`: remove windows, null the hub. `onAccessibilityEvent` forwards to `OverlayCommands.handlers["event"]` as `RawEvent` (4.2 type, fields copied) so 4.3.2 can glue.
  2. One full-screen window: `TYPE_ACCESSIBILITY_OVERLAY`, `FLAG_NOT_TOUCHABLE|FLAG_NOT_FOCUSABLE|FLAG_LAYOUT_IN_SCREEN|FLAG_LAYOUT_NO_LIMITS`, `layoutInDisplayCutoutMode=ALWAYS`, `fitInsetsTypes=0`, `TRANSLUCENT`. Window origin = display origin, so plan pixels = view pixels.
  3. `PlanDiff.diff(old: CoverPlan?, new: CoverPlan): PlanDelta` (by maskId). `submit` posts to main; empty delta → no invalidate.
  4. `CoverGeometry.toDisplay(c: Px, plan: CoverPlan, d: DisplayState, padPx: Int = 0): Px?` scales when sizes differ, rotates when rotation differs (0/90/180/270), pads, clamps to display, null if empty. Rotation and split screen need no special case because coords are full-display.
  5. `CoverView.onDraw`: SOLID `#202124` (`#E53935` when label=="glue"); MOSAIC = crop downscaled to 1/16 then upscaled without filtering; BLUR = crop drawn with `RenderEffect.createBlurEffect(25f,25f)` via a child `RenderNode`; no crop → SOLID; label centred white 14 sp. After draw, `Choreographer.postFrameCallback` writes `render.jsonl` and calls `OverlayHub.drawnListeners` with the drawn rects.
  6. `MaskPlanJson.parse(String): CoverPlan` (org.json; reject `contractVersion != "1.0"`). `OverlayCmdReceiver` handles `plan`/`clear`, forwards others to `OverlayCommands`.
  7. Tests (≈8): diff empty on identical plan, moved/added/removed/restyled; geometry scale, rotate 90/270, clamp, pad; JSON parse of a valid example from `contracts/examples` + version reject.
- **Verify `4.3.1.ps1`:** ktlint → gradle build + 3 tests → manifest grep `OverlayAccessibilityService` and `canPerformGestures` → `VERIFY 4.3.1: PASS`. Phone script: install, enable service via `settings put secure enabled_accessibility_services` (appending, never removing), push 3-cover plan, open Instagram/YouTube/Chrome/keyboard, `screencap` each, `input tap` under a cover in 5 apps (testfeed log confirms its tap), pull `render.jsonl`, `render_stats.py` prints p95 `(tDrawnMs - tRecvMs)` vs `vsyncPeriodMs`.

### 4.3.2 Glued test box
- **Goal:** a red box placed at a point follows content from scroll events alone; drift table.
- **Owned:** `overlay/glue/{GluedBox,GlueController}.kt`, test `glue/GluedBoxTest.kt`, `workshop/overlay/{drift,glue_run}.py`, `workshop/overlay/tests/test_drift.py`, `tools/verify/4.3.2.ps1`, `tools/phone/4.3.2-phone.ps1`.
- **Steps:**
  1. `GluedBox(start: Px)` pure: `apply(d: ScrollDelta, nowMs: Long)` shifts by `(dx, dy)` (content-moved sign from 4.2) only when the box centre lies in `containerRect` (or rect is null); `position(): Px`. Unknown container while a box is placed → ignore and count `mismatch`.
  2. `GlueController` registers `OverlayCommands.handlers["glue"]` and `["event"]`; feeds `RawEvent`s through 4.2's `ScrollTracker()` (`ScrollNormaliser`); submits a `CoverPlan` with one SOLID cover (maskId 9001, label "glue") drawn solid red (colour chosen by `label=="glue"` in CoverView, 4.3.1); logs `glue.jsonl`.
  3. `drift.py --testfeed <feedlog> <glue.jsonl>`: item under the start point from the feed log; drift = |box.y − item.y| at each feed frame (nearest glue sample by tMs); prints max/p95. `--frames <dir> <glue.jsonl>`: tracks a 64×64 patch next to (not under) the box with numpy SAD search ±48 px across saved frames; drift = |box shift − patch shift| scaled to screen px.
  4. Tests: Kotlin (≈5) sign, accumulation over 100 events, container mismatch, nested container ignored, reset. Python (≈3) drift on a synthetic feedlog = 0, a shifted one = known value, SAD tracker on a synthetic image.
- **Verify `4.3.2.ps1`:** ktlint, ruff, gradle `GluedBoxTest`, pytest → `VERIFY 4.3.2: PASS`. Phone script: place box, `glue_run.py` drives 30 s scrolls in Test Feed, Instagram, YouTube, Chrome, Reddit, writes `veil/data/ch4/drift.md` table (app, max, p95, mismatches).

### 4.3.3 Self-capture, own-cover reporting, peek, long-press
- **Goal:** prove whether covers are captured, report own covers per frame, test per-window screenshots, catch long-press.
- **Owned:** `overlay/self/{OwnOverlayRegistry,PeekProbe,SelfCapture}.kt`, `overlay/touch/{LongPressDetector,TouchReplay,CoverTouchLayer}.kt`, tests `{OwnOverlayRegistryTest,LongPressDetectorTest,TouchReplayTest}.kt`, `workshop/overlay/{own_join,selfcap_check}.py`, `workshop/overlay/tests/test_own_join.py`, `docs/reports/ch4-plumbing.md` (`## Phase 4.3` and `## Chapter 4 gate` sections only, append), `tools/verify/4.3.3.ps1`, `tools/verify/pt-4.3.ps1`, `tools/phone/4.3.3-phone.ps1`.
- **Steps:**
  1. `OwnOverlayRegistry(capacity=256)`: listener on `drawnListeners`, `at(tMs): List<Px>` = latest sample with `sample.tMs ≤ tMs`; `scaled(rects, screen, capture)` rounds outward (so ≤ 2 px at capture scale). Writes `own.jsonl`.
  2. `own_join.py frames.jsonl own.jsonl -o frames_own.jsonl`: fills `ownOverlay` (screen px) per frame by tMs, validates with `workshop.contracts.validate --type Frame`. `selfcap_check.py`: for saved PNGs, checks pixels inside each reported rect (scaled) match the cover colour (≥ 90 %) → "covers captured: yes/no", and edge alignment ≤ 2 px.
  3. `PeekProbe` (cmd `peekprobe`): if `SDK_INT ≥ 34`, for the active app window call `takeScreenshotOfWindow` 20 times as fast as allowed, log successes, error codes, min interval; save one PNG and check its pixels in a cover rect are NOT the cover colour. Else log `unavailable`.
  4. `LongPressDetector(longMs=500, slopPx)` pure: events down/move/up/cancel → `Tap(x,y)`, `Drag(points)`, or `LongPress`. `TouchReplay.toStrokes(...)`: pure → list of `(path points, startMs, durationMs)` for `GestureDescription`. `CoverTouchLayer`: one touchable `TYPE_ACCESSIBILITY_OVERLAY` window per peekable cover; on Tap/Drag set it `NOT_TOUCHABLE`, `dispatchGesture`, restore on callback; LongPress → `gestureListeners` + `gestures.jsonl`.
  5. Report: self-capture result with 2 example frames, chosen mitigation (ownOverlay = "unknown"; peek if available), peek rate, drift table link, gate decision vs §4.
  6. Tests (≈9): registry lookup before/between/after samples, scaling within 2 px; detector tap, drag past slop, long-press at 500 ms, cancel; replay timing and coordinates.
- **Verify `4.3.3.ps1`:** ktlint, ruff, gradle 3 tests, pytest (join on synthetic frames + own logs, schema-valid) → `VERIFY 4.3.3: PASS`. Phone script: `save_frames=true`, push plan, scroll, pull frames + own.jsonl, run join + `selfcap_check.py`, `peekprobe`, long-press via `input swipe x y x y 800` on a peekable cover, then `input tap` on it (Test Feed logs tap).

## 4. Acceptance (PLAN thresholds word for word)
| ID | Criterion | Pass threshold | Sub | How |
| --- | --- | --- | --- | --- |
| AC-4.3-01 | On top, not in the way | Covers draw above apps, the keyboard and the status bar; taps pass through in 5 apps | 4.3.1 | PHONE `4.3.1-phone.ps1` |
| AC-4.3-02 | Fast drawing | A new cover plan is visible within 1 display frame (p95) | 4.3.1 | PHONE `render_stats.py` |
| AC-4.3-03 | Glued | Drift ≤ 8 px over 30 s of scrolling in the main apps | 4.3.2 | PHONE drift table (DEFERRED if > 5 min) |
| AC-4.3-04 | Self-capture settled | Whether our covers appear in our own capture is proven with example frames | 4.3.3 | PHONE `selfcap_check.py` + report |
| AC-4.3-05 | Own covers reported | Every frame captured while covers are visible carries their positions, accurate to within 2 px at capture scale | 4.3.3 | JVM/pytest now, PHONE join |
| AC-4.3-06 | Peek known | Per-window screenshot availability and rate limit documented; if available, shown to exclude our covers | 4.3.3 | PHONE `peekprobe` + report |
| AC-4.3-07 | Long-press works | A long-press on a cover is detected, and normal taps still reach the app below | 4.3.3 | JVM now, PHONE gestures + feed log |
Chapter 4 gate: decided in the report from the 4.1, 4.2 and 4.3 AC rows; if rejected, "Apply the Chapter 4 fallback, and if self-capture cannot be handled, switch to solid covers with longer holds (as in the Chapter 2 fallback)."

## 5. Proof test "Sticky note" (`tools/verify/pt-4.3.ps1`, `-Phone`, written by 4.3.3)
Without `-Phone`: runs the three verify scripts. With `-Phone`: start scrcpy recording to `veil/data/ch4/sticky.mp4`; open Test Feed; push a plan with 3 covers on 3 items from the feed log (one peekable); glue them; `drive.py` scrolls up/down 30 s, flings, stops; `input tap` through a cover onto an item; long-press the peekable cover; pull feedlog, glue/own/gestures logs, frames. Checks: drift per cover ≤ 8 px vs feed truth; tap logged by Test Feed with the right itemId; one `LongPress` in `gestures.jsonl`; `selfcap_check.py` result and ≤ 2 px rect alignment. Ends `PT 4.3: PASS` when AC-4.3-01 to 07 hold. Evidence in `veil/data/ch4/`.

## 6. Human checklist (PENDING-HUMAN, one sitting about 15 min)
- [ ] Connect the iQOO, run the three `tools/phone/4.3.*-phone.ps1` scripts and `pt-4.3.ps1 -Phone`.
- [ ] Look: covers over Instagram, YouTube, Chrome, keyboard and status bar; nothing feels blocked.
- [ ] Scroll with a peekable cover under the finger: replay delay acceptable?
- [ ] Read the drift table and the self-capture frames; sign the Chapter 4 gate line in the report.

## Amendment A1 (orchestrator)
One production accessibility service only. `overlay/` exposes an `OverlayHost` interface (attach(service: AccessibilityService), detach(), render(plan)) that 4.2.1's Guard accessibility service calls on connect/disconnect (a one-line hook added in a later phase). `OverlayAccessibilityService` is allowed only in `src/debug/` for isolated testing and must not appear in the release manifest.
