# SPEC 5.2-W Live wiring
MODEL: claude-opus-5-5 · Status: DRAFT for orchestrator · PLAN.md 1507-1722 · Entry: 5.2.1-5.2.3 committed (Conductor, Thumbs, RegionLane, Layer1Lane, TextLane, NudeDecode, MlKitOcr exist); 4.1/4.2/4.3/5.1 committed; phone NOT connected.
Goal: capture (4.1) + signals (4.2) → Conductor + lanes (5.2) → brain (5.1) → covers (4.3) run inside the real Guard. Laptop proof = assembleDebug + JVM tests with fakes; everything on-phone is PENDING-HUMAN.

## 1. Risks and deferrals
- **R-1 Nothing starts frames today.** `CaptureService` never creates a `FrameSource` (4.1 left "source" unwired). W.1 creates `MediaProjectionScreenSource` on consent and the a11y fallback on `source a11y`.
- **R-2 One clock.** All live times are `SystemClock.uptimeMillis()` (a11y `eventTime`, renderer, touch, 5.3 stage contract). `FrameAdapter` re-stamps every frame at receipt; `CapturedFrame.tMs` (elapsedRealtime) is never used.
- **R-3 Threads.** BrainPipeline is not thread-safe. Conductor `onEvent`/`pump` and AI `done` callbacks all run on ONE `HandlerThread("veil-conductor")`; `ThreadWorker` posts `done` back to it. `offer` is the only cross-thread call (5.2.1's 1-slot mailbox).
- **R-4 Frames must close fast** (ImageReader holds 2): `FrameAdapter` copies to a 360-wide `IntArray` and closes the frame in `finally` before handing it on. The HW→software copy is CPU; GPU crop/resize is DEFERRED (D-5.2W-gpu).
- **R-5 ONNX:** `onnxruntime-android:1.22.0` is already in `:app`, so the Describer (SigLIP2 image b1/b4/b16) and NudeNet 320n/640m adapters are REAL (CPU EP). Models are pushed by hand to `/sdcard/Android/media/com.veil.guard/models/`; a missing model drops its lane and logs `kind=warn`. ORT cannot run in JVM tests → adapters are compile-checked only; their pre-processing is unit-tested. QNN/NNAPI EP → 3.3 ResidentModels (DEFERRED D-5.2W-ep).
- **R-6 Stubbed, recorded in DEFERRED.md by the orchestrator:** object Finder (YOLOE) → `finder = null` (D-5.2W-finder); toxicity → `tox = null` (tokenizer, same as 5.1/DV-2); Teacher `ConceptRegistry` live swap → `concepts` reload command only (D-5.2W-teach); 6.1 console bridge is a separate APK with `NoGuardBackend` and the Guard receivers are DUMP-protected → real `GuardBackend` DEFERRED (D-5.2W-console); 5.3 `tune.py` must also sync the new `app/src/main/assets/params.json` (D-5.2W-params).
- **R-7 Log shapes.** `files/debug.jsonl` plan lines must satisfy both readers: `latency/parse.py` (top-level `lookId`, `masks[].rect=[l,t,r,b]`) and `guardcheck/cat_feed.py` (nested `plan.masks[].rect={x,y,w,h}`). `JsonlDebugLog` writes both (§2).
- **R-8 Self-capture.** MediaProjection sees our own covers; `SelfCapture` reporting is forced ON at connect and `FrameMeta.ownOverlay` = `SelfCapture.current?.at(t)` (screen px). The debug `OverlayAccessibilityService` must stay disabled when the Guard service is on (two hosts = two windows).

## 2. Shared interfaces (Wave 0: every Builder writes its own §2 signatures with `TODO()` bodies in its first 3 min; nobody compiles before all §2 files exist)
Package `com.veil.guard.wire` = `veil/guard/app/src/main/java/com/veil/guard/wire/` (5.2.3's `MlKitOcr.kt` already lives there; do not touch it).
`wire/WireHub.kt` (W.1 writes verbatim; nobody else edits):
```kotlin
package com.veil.guard.wire
import com.veil.brain.contract.UiEvent
import com.veil.conductor.DebugLog
import com.veil.conductor.Frame
import com.veil.conductor.LayoutNode
import com.veil.conductor.OverlayPort
/** Process-wide seams between W.1 (runtime), W.2 (pixels, models) and W.3 (signals, overlay). */
object WireHub {
    @Volatile var frames: ((Frame) -> Unit)? = null        // W.1 sets; W.2 FrameAdapter calls (capture thread)
    @Volatile var events: ((UiEvent) -> Unit)? = null      // W.1 sets; W.3 a11y service calls (main thread)
    @Volatile var drawn: ((Long) -> Unit)? = null          // W.1 sets; W.3 LiveOverlay calls with uptime of first draw after a submit
    @Volatile var log: DebugLog? = null                    // W.1 sets; anyone writes {"kind":"warn",...}
    @Volatile var overlay: OverlayPort? = null             // W.3 sets on a11y connect, null on unbind
    @Volatile var layout: () -> List<LayoutNode> = { emptyList() } // W.3 sets (LayoutFeed::latest)
}
```
Cross-owner signatures (exact):
- W.2 `wire/FrameAdapter.kt`: `object FrameAdapter { val sink: com.veil.guard.capture.FrameSink }`.
- W.2 `wire/ml/LiveLanes.kt`: `object LiveLanes { fun build(ctx: android.content.Context, counters: com.veil.conductor.Counters): List<com.veil.conductor.Lane> }` (re-reads models + concepts each call).
- W.3 `wire/EventAdapter.kt`: `object EventAdapter { fun toBrain(e: com.veil.guard.signals.UiEvent): com.veil.brain.contract.UiEvent?; fun toLayout(n: com.veil.guard.signals.SnapNode): LayoutNode }`.
- W.3 `wire/PlanRecords.kt`: `object PlanRecords { fun toCoverPlan(plan: Record): CoverPlan; fun shifted(p: CoverPlan, dx: Int, dy: Int): CoverPlan; fun empty(planId: Long, tMs: Long, w: Int, h: Int): Record }` (mask-plan v1.0 map; numbers via `(x as Number)`).
- W.1 `wire/GuardRuntime.kt`: `object GuardRuntime { fun start(ctx: Context); fun pause(); fun resume(); fun stop(); fun setMode(m: String); fun setSkipApps(pkgs: Set<String>); fun reloadLanes(); fun writeStatus(ctx: Context) }` (all thread-safe; post to the conductor thread).
Debug log contract (`files/debug.jsonl`, one JSON object per line, `tMs` = uptime): Conductor records as-is (`look|finding|stats|pause`); `kind=plan` (or `maskPlan`) → `{"kind":"plan","tMs","lookId"(last judged look or null),"masks":[{"maskId","rect":[l,t,r,b],"style","layer"}],"plan":{original mask-plan}}`; stage lines `{"kind":"stage","lookId":int,"stage":"frame|gate|ai|judge|plan|draw","tMs":int}`; warnings `{"kind":"warn","what":...}`.
Trace sections (`android.os.Trace`, Android classes only): `veil.frame` (FrameAdapter), `veil.step` (pump), `veil.lanes` (worker job), `veil.plan` (LiveOverlay.submit), `veil.draw` (OverlayRenderer.render).
Gradle (all verify scripts): `powershell -NoProfile -ExecutionPolicy Bypass -File tools\gradle-locked.ps1 <args>`; ktlint as in `tools/verify/4.3.3.ps1` (copy its `Check` helper and ktlint line). App unit tests: `:app:testDebugUnitTest --tests "<class>"`. Pure classes (no `android.*` import): GuardCore, StageTracker, JsonlDebugLog, EventAdapter, PlanRecords, ImagePrep, ConceptPack.

## 3. Sub-phases (W.1, W.2, W.3 in parallel after Wave 0)
### 5.2-W.1 Runtime, lifecycle, commands, stage log
Owned: `wire/WireHub.kt`, `wire/GuardCore.kt`, `wire/GuardRuntime.kt`, `wire/ThreadWorker.kt`, `wire/StageTracker.kt`, `wire/JsonlDebugLog.kt`, `capture/service/CaptureService.kt` (edit), `capture/service/CaptureCommandReceiver.kt` (doc comment), `app/src/main/assets/params.json` (new, copy of `workshop/twin/params.json`), `app/src/test/java/com/veil/guard/wire/{GuardCoreWiringTest,StageTrackerTest}.kt`, `tools/verify/5.2-W.1.ps1`.
Key API (pure): `class GuardCore(paramsJson: String, mode: String, lanes: (Counters) -> List<Lane>, worker: AiWorker, overlay: () -> OverlayPort?, layout: () -> List<LayoutNode>, log: DebugLog, skipApps: Set<String>, now: () -> Long, trace: (String, () -> Unit) -> Unit = { _, b -> b() })` with `offer(f: Frame)`, `pump()`, `onEvent(e: UiEvent)`, `onDrawn(tMs: Long)`, `pause()`, `resume()`, `setMode(m)`, `setSkipApps(s)`, `rebuild()`, `val mode`, `val userPaused`, `val lastStats: Record?`.
Steps:
1. GuardCore owns one `Conductor` (5.2 §2 ctor) built from: `lanes(counters) + aiSentinel` (a last Lane that calls `stages.ai(input.lookId, now())` and returns empty), a forwarding `OverlayPort` (delegates to `overlay()`, drops if null), `StatsSink` → log + `lastStats`, `JsonlDebugLog` wrapped so each record also goes to `StageTracker.onRecord`. `setMode`/`setSkipApps`/`rebuild` rebuild the Conductor (new BrainPipeline). `setMode("off")` = `pause()`; other modes also `resume()`.
2. `pause()`: flag; `offer` drops frames; submits `PlanRecords.empty(...)` (last frame's screen size) to the overlay. `resume()` clears it. These are user pauses; screen-off/skip-app pauses stay inside the Conductor.
3. `StageTracker` (pure, synchronized, emits through the log): `frame(frameId, t)` remembered (cap 64); on a `look` record with `look==true` → `frame` + `gate` lines for its lookId; `ai(lookId,t)`; `judged(t)` (called by GuardCore when the worker `done` is delivered) → `judge` for the last ai lookId; first plan record after a judge → `plan`; `onDrawn(t)` → `draw` once for that lookId. Lines strictly in stage order per lookId.
4. `ThreadWorker(post: (Runnable) -> Unit, onDone: () -> Unit) : AiWorker`: single-thread executor `veil-ai`; job wrapped in Trace `veil.lanes`; `done(findings, aiMs)` posted via `post`; `busy` true from submit until done ran.
5. `GuardRuntime` (Android): `HandlerThread("veil-conductor")`; `start(ctx)` reads `assets/params.json`, mode from prefs (default `balanced`), skipApps default `{com.veil.guard, com.veil.console, com.android.settings}`, `lanes = { LiveLanes.build(ctx, it) }`, `JsonlDebugLog(File(ctx.filesDir,"debug.jsonl"))`, sets `WireHub.log/frames/events/drawn`: frames → `core.offer` + post one pending `pump` (AtomicBoolean, never more than one queued); events/drawn → posted. `stop()` clears WireHub fields W.1 set, quits threads. `writeStatus` → `files/status.json` `{mode, userPaused, lastStats}`.
6. `CaptureService`: consent granted → `GuardRuntime.start(applicationContext)` + `MediaProjectionScreenSource(proj, displaySize(), densityDpi, display.rotation).start(FrameAdapter.sink)`; `source a11y|mp` swaps to `AccessibilityScreenSource(screen=displaySize(), rotation=…)`/back (stop old first; a11y also starts the runtime); `pause|resume|stop` also call GuardRuntime; new cmds `mode <light|balanced|strict|off>` (persist to prefs), `skip <pkg,pkg>`, `concepts` (`reloadLanes`), `status`; `onDestroy` → `GuardRuntime.stop()`. Update the receiver doc comment with the full cmd list.
7. Tests (fakes, no Android): `GuardCoreWiringTest` builds GuardCore with real params from `src/main/assets/params.json`, a fake Lane returning one layer-1 `Finding` (hide, object) per look, a direct worker, a recording OverlayPort, a fake clock, frames whose thumbs change: (a) ≥1 overlay plan with ≥1 mask; (b) debug lines include stage `frame,gate,ai,judge,plan` for one lookId in non-decreasing tMs, then `onDrawn` adds `draw`; (c) plan lines have top-level `masks[0].rect` as a 4-int list AND nested `plan`; (d) `setMode("strict")` keeps producing plans; (e) `pause()` → 0 new looks + one empty plan; (f) a `scrolled` event → `shift` recorded. `StageTrackerTest`: out-of-order inputs never emit a later stage before an earlier one.
Verify `5.2-W.1.ps1`: ktlint owned .kt; params asset SHA256 == `workshop/twin/params.json`; `Select-String` CaptureService for `GuardRuntime.start`, `FrameAdapter.sink`, `"mode"`; `:app:testDebugUnitTest --tests "com.veil.guard.wire.GuardCoreWiringTest" --tests "com.veil.guard.wire.StageTrackerTest"`; `:app:assembleDebug` → `VERIFY 5.2-W.1: PASS`.

### 5.2-W.2 Frames in, real models, concepts
Owned: `wire/FrameAdapter.kt`, `wire/ml/{ImagePrep,ModelStore,OrtDescriber,OrtNsfwDetector,ConceptPack,LiveLanes}.kt`, `app/src/test/java/com/veil/guard/wire/ml/{ImagePrepTest,ConceptPackTest}.kt`, `tools/verify/5.2-W.2.ps1`.
Steps:
1. `FrameAdapter.sink`: if `WireHub.frames == null` close and return. Else in Trace `veil.frame`: `hardwareBuffer` → `Bitmap.wrapHardwareBuffer(hb, ColorSpace.get(SRGB))!!.copy(ARGB_8888,false)` (or `frame.bitmap`), `getPixels` → `IntArray`; `frame.close()` in `finally`; `t = uptimeMillis()`; `FrameMeta(++id, t, w, h, screen.w, screen.h, SelfCapture.current?.at(t)?.map { Rect(it.x,it.y,it.w,it.h) } ?: emptyList())`; `thumb = Thumbs.fromArgb(argb,w,h)`; invoke `WireHub.frames`.
2. `ImagePrep` (pure): `crop(argb, fw, fh, sw, sh, r: Rect): Img` (screen→frame scale, clamped; `data class Img(px: IntArray, w: Int, h: Int)`); `resizeBilinear(img, tw, th): Img` (PIL BILINEAR semantics, no antialias needed for downscale tests ±2/255); `letterbox(img, size): Pair<Img, Triple<Float,Float,Float>>` = `nudenet/parity.py:preprocess` (black square canvas, image pasted at (0,0), resize) with `letterbox_params`; `chw(img, mean, std, out: FloatArray, off: Int)` RGB planes, `(v/255 - mean)/std`.
3. `ModelStore`: dir `ctx.externalMediaDirs.first()/models`; cached `OrtSession` by file name, `null` + `warn` line if missing; one `OrtEnvironment`; CPU EP, 4 intra-op threads.
4. `OrtDescriber : Describer`: per piece crop → 224×224 stretch → `chw(mean=0.5,std=0.5)`; batch = smallest of {1,4,16} ≥ n (`siglip2/runtime.py:pick_batch`), pad by repeating the last row; input `pixel_values`, output `fingerprint`; L2-normalise; return first n.
5. `OrtNsfwDetector(id, session, size) : NsfwDetector`: crop `area` → letterbox → input `session.inputNames.first()` [1,3,size,size] (/255, no mean/std) → raw output → `NudeDecode.decode(raw, n, c, conf=0.2f, iou=0.45f, lb)` → boxes offset back to screen px.
6. `ConceptPack` (pure): `parse(json: String): List<CompiledConcept>` for `contracts/compiled-concept.schema.json` (port the helper used by `guard/brain/src/test/.../unit/GoldenTests.kt`); accepts one concept or `{"concepts":[...]}`. `load(dir: File): Concepts` reads `*.json` in `<media>/concepts/`: describer = all, finder = empty, keywords = `raw["keywords"]` string lists.
7. `LiveLanes.build`: `Layer1Lane(320n, 640m?, counters)` if 320n present; `RegionLane(concepts, OrtDescriber, finder = null, FingerprintCache(), counters)` if describer models and ≥1 concept; `TextLane(concepts, tox = null, MlKitOcr(), counters)` always; each skipped lane → `{"kind":"warn","what":"lane-off","lane":...,"why":...}`.
Tests: `ImagePrepTest` (crop scale/clamp; letterbox params on 300×200 → size 320 match `letterbox_params`; chw of a 2×2 known image; bilinear 4×4→2×2 known values); `ConceptPackTest` (parse `contracts/examples` compiled-concept example if present, else a tiny inline doc; keywords picked up).
Verify `5.2-W.2.ps1`: ktlint owned; `:app:testDebugUnitTest --tests "com.veil.guard.wire.ml.*"`; `:app:compileDebugKotlin`; `Select-String` LiveLanes for `Layer1Lane(`, `RegionLane(`, `TextLane(` → `VERIFY 5.2-W.2: PASS`.

### 5.2-W.3 Signals and overlay host
Owned: `signals/GuardAccessibilityService.kt` (edit), `overlay/OverlayRenderer.kt` (edit: Trace `veil.draw` around `render` body only), `wire/{EventAdapter,PlanRecords,LayoutFeed,LiveOverlay}.kt`, `app/src/test/java/com/veil/guard/wire/{EventAdapterTest,PlanRecordsTest}.kt`, `tools/verify/5.2-W.3.ps1`.
Steps:
1. `EventAdapter.toBrain`: Scrolled → `UiEvent("scrolled", tMs, dx, dy, pkg)` (same sign as the contract; brain Tracker adds dy); WindowChanged → `"windowChanged"`; ContentChanged → `"contentChanged"`; ScreenOff/On → `"screenOff"/"screenOn"`; NodesSnapshot → null. `toLayout`: PxRect → Rect 1:1, kind/text kept.
2. `LayoutFeed.latest()`: cached nodes; if older than 250 ms pull `SignalsHub.snapshotter?.snapshot()` and map with `toLayout`; never throws (runCatching → cached).
3. `PlanRecords`: `toCoverPlan` (masks: maskId, rect{x,y,w,h}, style upper-cased → `CoverStyle`, layer, peekable, label); `shifted` adds (dx,dy) to every cover (Tracker convention); `empty` builds a v1.0 plan with `masks=[]`, `reason="clear"`.
4. `LiveOverlay(touch: CoverTouchLayer) : OverlayPort`: `submit` in Trace `veil.plan` → `toCoverPlan` → `OverlayHub.sink?.submit(cp)` (null → one `warn`), keep `last`, main-thread `touch.update(cp.covers)`, arm `pendingDraw`; registers one `OwnOverlayListener` that on the first draw after arming calls `WireHub.drawn?.invoke(sample.tMs)`; `shift` → `shifted(last)` → same submit path (no draw stage).
5. `GuardAccessibilityService.onServiceConnected` (after existing lines, before `host?.onServiceConnected`): `if (OverlayHostRegistry.host == null) OverlayHostRegistry.host = OverlayRenderer()`; then after it: `SelfCapture.install(this)`; `OverlayCommands.handlers["selfcap"]?.invoke("on")`; `glue = GlueController(File(filesDir,"overlay"), w, h).also { it.register() }` (w,h from `currentWindowMetrics.bounds`); `touch = CoverTouchLayer(this, File(filesDir,"overlay/touch.jsonl"))`; `WireHub.overlay = LiveOverlay(touch)`; `WireHub.layout = layoutFeed::latest`. `onAccessibilityEvent`: scroll RawEvents also → `glue?.onEvent(raw)`. `emit`: also `EventAdapter.toBrain(e)?.let { WireHub.events?.invoke(it) }`. `onUnbind`: `WireHub.overlay = null`, layout reset, `touch.clear()`, `SelfCapture.uninstall()`, remove `glue` handler (existing teardown kept).
Tests: `EventAdapterTest` (each event type; snapshot → null; node mapping); `PlanRecordsTest` (round trip of a 2-mask record with Int and Long numbers; shift; empty plan parses with `MaskPlanJson` after JSON encode is NOT required).
Verify `5.2-W.3.ps1`: ktlint owned; `:app:testDebugUnitTest --tests "com.veil.guard.wire.EventAdapterTest" --tests "com.veil.guard.wire.PlanRecordsTest"`; `:app:compileDebugKotlin`; `Select-String` GuardAccessibilityService for `OverlayHostRegistry.host = OverlayRenderer()`, `SelfCapture.install(this)`, `.register()`, `CoverTouchLayer(`, `glue?.onEvent(raw)`, `WireHub.events` → `VERIFY 5.2-W.3: PASS`.

## 4. What it unlocks (become runnable on the phone once installed)
- HC-024 (4.3 covers + Chapter 4 gate) with the production service; HC-020 (4.1 watch the watcher: frames now flow); HC-023 (4.2 signals) unchanged but now feeds the Guard.
- 5.2 PT "The cat feed" (`tools/verify/pt-5.2.ps1`), AC-5.2-01..06 PHONE parts (new HC to be raised by the orchestrator).
- HC-021 / `pt-5.3.ps1` (stage lines, Trace sections, `mode` command) and HC-025 (6.2 "Not a cat" needs a wired Guard; concepts via `concepts` reload).
- Still blocked: HC-018 Teacher-on-phone (tokenizer), 6.1 real Guard in the console (D-5.2W-console), Finder pieces (D-5.2W-finder).

## 5. Human checklist (PENDING-HUMAN, phone)
1. `adb push` `data/forge/nudenet/nudenet-320n.onnx`, `nudenet-640m.onnx`, `data/forge/siglip2/siglip2-image-b{1,4,16}.onnx` → `/sdcard/Android/media/com.veil.guard/models/`; one compiled cat concept JSON → `.../concepts/`; then `--es cmd concepts`.
2. Install debug Guard, enable ONLY `GuardAccessibilityService` (not the debug overlay service), `--es cmd start`, accept consent; check `files/debug.jsonl` has `look`, `plan`, all six `stage` kinds, and no `warn lane-off`.
3. `--es cmd mode --es value strict|light|off` changes `status.json`; `off` clears covers and touch windows.
4. Test Feed cat post gets covered, cover follows a scroll, clears on app switch and screen off; `perfetto` shows `veil.*` sections.
5. Then run HC-024, pt-5.2, pt-5.3 (HC-021).
