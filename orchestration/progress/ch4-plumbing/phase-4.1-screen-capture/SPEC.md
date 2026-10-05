# SPEC 4.1 Screen capture
MODEL: claude-opus-5-5 · Status: APPROVED (orchestrator; 360x792 = panel aspect accepted) · Source: PLAN.md 1186-1301 (Ch4 intro + Phase 4.1), App. D 2183-2200 · Fast track F1-F12.
Phone NOT connected: every sub-phase must BUILD + pass JVM unit tests (pure Kotlin, no `android.*` in tested classes). On-device items are PHONE checks (PENDING-HUMAN, F7).
Gradle: `guard/` project, run `.\gradlew.bat -p guard --no-daemon :app:...` (gradle.properties already caps 2 GB). Orchestrator serialises Gradle verify runs.

## 1. Deviations / risks
- **Frame size = 360 × round_even(360·H/W)** in portrait (swap in landscape). 1080×2400 → 360×800 (PLAN); the iQOO 15 panel (1440×3168) gives 360×792, matching `frame.schema.json`'s example. AC-4.1-01 is checked as "short side 360, aspect within 1 %".
- **Android 14+: one `createVirtualDisplay` per MediaProjection token**, token single-use. So pause = `virtualDisplay.setSurface(null)`, resume = `setSurface(reader.surface)`, rotation = `virtualDisplay.resize()` + new ImageReader. Never recreate the display (that would need new consent).
- **Android 15 QPR1+ stops projection on keyguard** → `onStop` → AWAITING_PERMISSION, reason `keyguard` (from SCREEN_OFF receiver). Resume needs a fresh consent dialog; this is expected, documented in the behaviour table.
- **Entire screen**: use `createScreenCaptureIntent(MediaProjectionConfig.createConfigForDefaultDisplay())` (API 34+); still detect single-app via `Callback.onCapturedContentResize` size ≠ display size → AWAITING_PERMISSION reason `singleApp`.
- **Accessibility service is owned by 4.2** (`com.veil.guard.signals`). 4.1.3 only defines `ScreenshotProvider` + `ScreenshotBridge` (§2). 4.2 (or a follow-up 1-line wiring) must set `ScreenshotBridge.provider` on connect and add `android:canTakeScreenshot="true"` to its service XML. Until wired, the backup source reports `Unavailable` and AC-4.1-07 stays PENDING-HUMAN.
- **Shared files**: `AndroidManifest.xml` is touched by 4.1.1 (only) and by 4.2: add elements only, never edit others' entries. Strings go in a new `res/values/capture_strings.xml`. `docs/reports/ch4-plumbing.md`: 4.1.3 writes only a `## Phase 4.1` section (append if file exists).
- **adb control**: commands go through `CaptureCommandReceiver`, exported but protected by `android.permission.DUMP` (only shell/system can send). `ConsentActivity` is exported so `am start` can open it.
- Parallel compile risk: each Builder's first step (≤ 2 min) writes the §2 files verbatim (if missing) plus its public class skeletons. If compile fails in a file you don't own, wait 1 min and retry once.

## 2. Shared interfaces (package `com.veil.guard.capture`, file `guard/app/src/main/java/com/veil/guard/capture/CaptureApi.kt`, owned by 4.1.1 for commit; any Builder may create it verbatim; nobody edits it)
```kotlin
package com.veil.guard.capture
enum class CaptureState(val wire: String) { RUNNING("running"), PAUSED("paused"), STOPPED("stopped"), AWAITING_PERMISSION("awaitingPermission") }
enum class FrameSourceKind(val wire: String) { MEDIA_PROJECTION("mediaProjection"), ACCESSIBILITY_SCREENSHOT("accessibilityScreenshot") }
data class PxRect(val x: Int, val y: Int, val w: Int, val h: Int)
data class FrameSize(val width: Int, val height: Int)
/** One delivered frame. The receiver MUST call close() as soon as it is done (guarantee to later phases). */
interface CapturedFrame : AutoCloseable {
    val frameId: Long; val tMs: Long; val size: FrameSize; val screen: FrameSize; val rotation: Int
    val source: FrameSourceKind; val blindRects: List<PxRect>
    val hardwareBuffer: android.hardware.HardwareBuffer?   // null in JVM tests / a11y path after downscale to bitmap
    val bitmap: android.graphics.Bitmap?                   // set on the a11y path
}
fun interface FrameSink { fun onFrame(frame: CapturedFrame) }
interface FrameSource {
    val kind: FrameSourceKind
    fun start(sink: FrameSink); fun pause(); fun resume(); fun stop()
    fun onRotation(screen: FrameSize, rotation: Int)
}
/** Implemented by 4.2's accessibility service; full-resolution screenshot, callback on any thread. */
interface ScreenshotProvider { fun takeScreenshot(onResult: (android.hardware.HardwareBuffer?, errorCode: Int) -> Unit) }
object ScreenshotBridge { @Volatile var provider: ScreenshotProvider? = null }
/** Pure: shared by 4.1.2/4.1.3. Short side 360, long side rounded to even, aspect kept. */
object CaptureGeometry {
    fun targetSize(screen: FrameSize): FrameSize {
        val portrait = screen.height >= screen.width
        val s = minOf(screen.width, screen.height); val l = maxOf(screen.width, screen.height)
        val long = (Math.round(360.0 * l / s / 2.0) * 2).toInt()
        return if (portrait) FrameSize(360, long) else FrameSize(long, 360)
    }
}
```
Log formats (app files dir `files/capture/`, pulled with `run-as`): `frames.jsonl` = one `frame.schema.json` object per frame (contractVersion "1.0", `ownOverlay: []`); `state.jsonl` = `{"tMs","state","reason","source","outstanding","fps"}` on every transition + a heartbeat every 5 s. Writer: `capture/CaptureLog.kt` (4.1.1). Frames saved as PNG only when pref `save_frames=true`.

## 3. Sub-phases (all in parallel)
### 4.1.1 Service, consent, state machine
**Goal**: FGS holding projection permission; fixed states; Resume Veil recovery. **Owned**: `guard/app/src/main/java/com/veil/guard/capture/CaptureApi.kt`, `.../capture/CaptureLog.kt`, `.../capture/state/**`, `.../capture/service/**`, `guard/app/src/test/java/com/veil/guard/capture/state/**`, `guard/app/src/main/AndroidManifest.xml` (add-only), `guard/app/src/main/res/values/capture_strings.xml`, `tools/verify/4.1.1.ps1`.
**Files**: `state/CaptureStateMachine.kt` (pure): `fun on(e: CaptureEvent, tMs: Long): Transition?`, `val state`, `val reason`; events `ConsentGranted(entireScreen: Boolean)`, `ConsentDenied`, `ProjectionStopped(cause)`, `KeyguardLocked`, `Pause`, `Resume`, `UserStop`, `ContentResized(content, display)`. `state/EntireScreenCheck.kt` (pure): `isEntireScreen(content, display, tol=0.02)`. `service/CaptureService.kt` (FGS type mediaProjection), `service/ConsentActivity.kt` (translucent), `service/CaptureNotifications.kt` (ongoing + "Resume Veil" action → ConsentActivity), `service/CaptureCommandReceiver.kt`.
**Steps**: 1) Manifest: perms `FOREGROUND_SERVICE`, `FOREGROUND_SERVICE_MEDIA_PROJECTION`, `POST_NOTIFICATIONS`; service `foregroundServiceType="mediaProjection"` exported=false; ConsentActivity exported, theme `@android:style/Theme.Translucent.NoTitleBar`; receiver exported, `android:permission="android.permission.DUMP"`, action `com.veil.guard.capture.CMD` (extras `cmd`=start|pause|resume|stop|source|saveFrames, `value`). 2) ConsentActivity launches the capture intent (§1 config on API 34+), passes resultCode/data to the service. 3) Service: `startForeground(..., FOREGROUND_SERVICE_TYPE_MEDIA_PROJECTION)` **before** `getMediaProjection`; register `MediaProjection.Callback` (onStop, onCapturedContentResize) **before** starting the source; feed every event to the state machine; on AWAITING_PERMISSION post Resume Veil. 4) SCREEN_OFF receiver → `KeyguardLocked` cause label. 5) `source` cmd swaps `FrameSource` at runtime (`MediaProjectionScreenSource` 4.1.2 / `AccessibilityScreenSource` 4.1.3; pref `capture_source`) without restarting the service. 6) Tests (≈8): all legal transitions; stop→awaiting reported same tMs (≤ 1 s); pause/resume never emits a consent request; singleApp → awaiting; illegal events ignored; isEntireScreen tolerance.
**Verify** `tools/verify/4.1.1.ps1`: ktlint on owned Kotlin; `:app:testDebugUnitTest --tests "com.veil.guard.capture.state.*"`; `:app:assembleDebug`; manifest grep for `mediaProjection` + `FOREGROUND_SERVICE_MEDIA_PROJECTION`. Ends `VERIFY 4.1.1: PASS`. Human: PHONE behaviour table rows (lock/unlock, chip tap, app kill, appops shortcut).

### 4.1.2 ScreenSource, small frames, pacing
**Goal**: 360-wide frames via ImageReader HardwareBuffers, latest-only, released at once; pause/resume; rotation. **Owned**: `.../capture/source/**`, `guard/app/src/test/java/com/veil/guard/capture/source/**`, `tools/verify/4.1.2.ps1`.
**Files**: `source/MediaProjectionScreenSource.kt` (`class MediaProjectionScreenSource(projection: MediaProjection, screen: FrameSize, dpi: Int, rotation: Int) : FrameSource`); `source/DisplayPort.kt` (`interface DisplayPort { fun create(size: FrameSize, dpi: Int); fun setSurfaceAttached(on: Boolean); fun resize(size: FrameSize, dpi: Int) }`); `source/ScreenSourceCore.kt` (pure: drives DisplayPort; pause/resume/rotate; asserts create called once); `source/FrameGate.kt` (pure: outstanding-lease counter, drops a new frame while one is outstanding, `outstanding`, `dropped`); `source/FrameRateMeter.kt` (pure: sliding 1 s / 10 s window fps).
**Steps**: 1) `ImageReader.newInstance(w, h, RGBA_8888, 2, USAGE_GPU_SAMPLED_IMAGE or USAGE_CPU_READ_RARELY)`; on image available `acquireLatestImage()`, wrap as `CapturedFrame` whose `close()` closes the Image and decrements FrameGate. 2) VirtualDisplay flags `AUTO_MIRROR`, created once. 3) Pause/resume/rotation per §1. 4) Static screen → no `onImageAvailable` (Android only posts on change): no timers, no polling. 5) Tests (≈8): geometry 1080×2400→360×800, 1440×3168→360×792, landscape swap; 10× pause/resume = 1 create, 10 detach/attach; rotation = resize not create; FrameGate never > 1 outstanding, counts drops; meter fps on synthetic timestamps.
**Verify** `tools/verify/4.1.2.ps1`: ktlint on owned Kotlin; `:app:testDebugUnitTest --tests "com.veil.guard.capture.source.*"`. Ends `VERIFY 4.1.2: PASS`. Human: PHONE fps static/scroll/video.

### 4.1.3 Backup capture, blind spots, driver routine
**Goal**: a11y-screenshot source (~3 fps, downscaled), black-area blind marking, the "Watch the watcher" routine + log checker. **Owned**: `.../capture/backup/**`, `.../capture/blind/**`, `guard/app/src/test/java/com/veil/guard/capture/{backup,blind}/**`, `workshop/bench/capture_routine.py`, `workshop/bench/capture_logs.py`, `workshop/bench/tests/test_capture_logs.py`, `workshop/bench/tests/fixtures/capture/**`, `docs/reports/ch4-plumbing.md` (§ Phase 4.1 only), `tools/verify/4.1.3.ps1`, `tools/verify/pt-4.1.ps1`.
**Files**: `backup/AccessibilityScreenSource.kt` (`class AccessibilityScreenSource(bridge: ScreenshotBridge = ScreenshotBridge, screen: FrameSize, rotation: Int) : FrameSource`; downscale via `Bitmap.wrapHardwareBuffer` → `createScaledBitmap` to `CaptureGeometry.targetSize`); `backup/ShotScheduler.kt` (pure: next shot ≥ 333 ms after last request, backoff +333 ms on interval-too-short error, pause stops scheduling); `backup/ThumbDedupe.kt` (pure: 32×64 luma checksum; identical → drop, keeps "only when changed"); `blind/BlindSpotDetector.kt` (pure: `detect(luma: ByteArray, w: Int, h: Int, hints: List<PxRect>): List<PxRect>` — whole frame ≥ 95 % pixels luma < 16 → full rect; hint rect (e.g. video node from 4.2) ≥ 90 % black → that rect; else 8×8-cell black regions ≥ 25 % of frame → bounding box; max 16).
**Steps**: 1) Source + scheduler + dedupe; `Unavailable` (log reason, state stays) when `ScreenshotBridge.provider == null`. 2) Detector + tests (≈8: all-black, video-hint black, small black icon ignored, ≤ 16 rects, scheduler ≥ 333 ms and ≥ 2 fps steady, backoff, dedupe). 3) `capture_routine.py --minutes 5`: PT steps via `adb.py` (30 s idle; scroll Instagram; YouTube video; rotate via `settings put system user_rotation`; lock/unlock keyevents; chip tap = PENDING manual prompt; `am force-stop com.veil.guard`; open Netflix), starts `scrcpy --record`, samples `dumpsys meminfo com.veil.guard` every 10 s, pulls `files/capture/*.jsonl` via `run_as_cat` into `veil/data/capture/<ts>/`. 4) `capture_logs.py`: validates frames.jsonl against `contracts/frame.schema.json`; reports idle fps, sizes by rotation, stop→awaiting latency, resume count, max outstanding, memory growth %, blind frames per package → JSON + AC verdicts. 5) pytest on synthetic fixtures (pass + fail case). 6) Report section: behaviour table + compatibility table (Netflix, Prime Video, Chrome Incognito, a banking app, Instagram DMs, YouTube, WhatsApp, Test Feed; ≥ 8) rows `PENDING-HUMAN`.
**Verify** `tools/verify/4.1.3.ps1`: ktlint; `:app:testDebugUnitTest --tests "com.veil.guard.capture.backup.*" --tests "com.veil.guard.capture.blind.*"`; `uv run --locked ruff check` + `pytest workshop/bench/tests/test_capture_logs.py -q`; `capture_routine.py --dry-run` prints the step plan. Ends `VERIFY 4.1.3: PASS`. `pt-4.1.ps1` (PHONE only): routine + checker → `PT 4.1: PASS/FAIL`.

ktlint (every script): `& "$env:JAVA_HOME\bin\java.exe" -jar "$env:VEIL_TOOLCHAIN\ktlint\ktlint.jar" --relative <owned globs>`. Each script dot-sources `tools\env.ps1`, uses the `Check` helper pattern of `tools/verify/3.1.3.ps1`, runs < 5 min.

## 4. Acceptance criteria (PLAN thresholds verbatim)
| ID | Criterion | Pass threshold | How verified | Now |
| --- | --- | --- | --- | --- |
| AC-4.1-01 | Right size | Frames arrive at 360 × 800 (matching the panel's aspect ratio) in both orientations | Frame log | JVM geometry tests; PHONE frame log |
| AC-4.1-02 | Quiet when still | A static screen delivers ≤ 1 frame per second | Frame counter | PHONE (checker idle fps) |
| AC-4.1-03 | No leaks | 10 minutes of scrolling: memory growth ≤ 5%, no unreleased frames | Memory log | FrameGate tests; DEFERRED 10-min PHONE run |
| AC-4.1-04 | Recovery | When capture stops, the awaiting-permission state appears within 1 s; "Resume Veil" restores capture 10 out of 10 times | Test log | state-machine tests; PHONE 10× |
| AC-4.1-05 | Pause keeps permission | Pause and resume 10 times with no new permission dialog | Test log | ScreenSourceCore test; PHONE 10× |
| AC-4.1-06 | Lock behaviour known | Outcomes of lock/unlock, status-bar chip tap and app kill recorded; the permission-shortcut result recorded | Behaviour table | PENDING-HUMAN |
| AC-4.1-07 | Backup path works | Accessibility-screenshot capture delivers ≥ 2 frames/s and can be switched on without a restart | Test log | ShotScheduler tests; PHONE (needs 4.2 wiring) |
| AC-4.1-08 | Blind spots known | ≥ 8 apps tested for black frames | Compatibility table | detector tests; PENDING-HUMAN table |

## 5. Proof test PT-4.1 "Watch the watcher"
**Machine (now)**: all three verify scripts PASS; `capture_logs.py` passes the good fixture and fails the bad one (idle 3 fps, 2 outstanding, no awaiting state).
**Machine (PHONE)**: `tools/verify/pt-4.1.ps1` installs debug APK, starts consent, runs the 5-min routine with scrcpy recording, pulls logs, runs the checker: idle ≤ 1 fps; sizes 360×long / long×360; awaiting ≤ 1 s after lock and kill; max outstanding ≤ 1; memory growth ≤ 5 %; Netflix frames carry a full-frame blindRect. Evidence → `progress/ch4-plumbing/phase-4.1-screen-capture/evidence/`.
**Human**: compare captured frames to the scrcpy recording at 5 marked moments (same content); tap "Resume Veil" after lock and after kill; tap the status-bar chip.

## 6. Human items (one batch in HUMAN_CHECKS.md)
- [ ] Connect iQOO, run `pt-4.1.ps1`; accept consent ("Entire screen"); tap Resume Veil when prompted (lock, kill), tap the capture chip once.
- [ ] Test `adb shell appops set com.veil.guard PROJECT_MEDIA allow`: dialog skipped? survives lock? → behaviour table.
- [ ] 10× Resume Veil and 10× pause/resume (`am broadcast -a com.veil.guard.capture.CMD --es cmd pause|resume`): no dialog on pause/resume.
- [ ] Enable 4.2's accessibility service, switch `--es cmd source --es value accessibilityScreenshot`, confirm ≥ 2 fps without restart.
- [ ] Open the 8 apps (test accounts only, no personal content) → fill compatibility table.
- [ ] DEFERRED (F6): 10-min scrolling memory run for AC-4.1-03.
