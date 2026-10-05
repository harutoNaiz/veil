# SPEC: Phase 4.2 "Screen signals"
MODEL: claude-opus-5-5 · Status: APPROVED (orchestrator; the §2 shared files are created by Builder 4.2.1 as its first step, not by the orchestrator) · Source: PLAN.md lines 1186-1199 (Ch 4 gate), 1302-1401 (Phase 4.2)
Waves: **Wave 0** (orchestrator, 1 min: write the §2 files verbatim) → **Wave 1**: 4.2.1 ∥ 4.2.2 ∥ 4.2.3 (all offline; phone parts are `-Phone` switches).
Phone is NOT connected: every sub-phase must BUILD and pass JVM/pytest checks; PHONE rows are PENDING-HUMAN (F7).

## 1. Deviations and risks
- **Clock.** UiEvent `tMs` = `AccessibilityEvent.eventTime` (uptimeMillis, the contract clock). But 2.1's `record.py` takes `t0Ms` from `/proc/uptime` (boot time, which includes deep sleep). `pull_log.py --boottime` shifts `tMs` by (elapsedRealtime − uptimeMillis), taken from the log's `.clock.json` sidecar, so the log lines up with 2.1 recordings. The default output stays on the contract clock.
- **Frame-difference fallback (4.2.2 step 4)** is built as a pure-Kotlin `FrameShiftEstimator` with tests. Wiring it to 4.1's frame stream is deferred to the chapter gate, and those apps are listed as "estimated scroll". Laptop-side estimates reuse `workshop/recordings/estimate.py`.
- **One `event.source` fetch** (a single node with no children) is allowed for `TYPE_VIEW_SCROLLED` only, to get container bounds and id. Every other tree access lives only in `BoundedSnapshotter` (AC-4.2-05).
- **No Gatekeeper exists yet.** In logging mode the snapshot is pulled every 250 ms on its own HandlerThread (`startPump`), giving the cost table. The Gatekeeper calls `snapshot()` later.
- The JSON is written by hand (`UiEventJson`). Don't use org.json, because it is a stub in JVM tests.
- Log control is an exported receiver guarded by `android.permission.DUMP`, so only `adb shell` can reach it.
- **RAM:** three builders running Gradle could OOM (2 GB × 3 on 7.4 GB). Builders run Gradle **only through their verify script**, and before starting it wait while another `java` Gradle process is alive (`Get-Process java`).
- The Phase 1.1 `ProbeAccessibilityService` stays as it is. The new service is separate.

## 2. Shared interfaces (Wave 0: written verbatim; 4.2.1 owns `Contracts.kt` from then on; the two stubs belong to 4.2.2 and 4.2.3, who replace their bodies)
`guard/app/src/main/java/com/veil/guard/signals/Contracts.kt` (FROZEN for this phase):
```kotlin
package com.veil.guard.signals
data class PxRect(val x: Int, val y: Int, val w: Int, val h: Int)
data class SnapNode(val kind: String, val rect: PxRect, val nodeId: String? = null, val text: String? = null,
    val contentDescription: String? = null, val className: String? = null)   // kind: image|video|web|text|list|post|other
sealed interface UiEvent { val eventId: Long; val tMs: Long; val packageName: String? }
data class Scrolled(override val eventId: Long, override val tMs: Long, override val packageName: String?, val dx: Int, val dy: Int,
    val containerRect: PxRect? = null, val containerId: String? = null, val estimated: Boolean = false) : UiEvent
data class WindowChanged(override val eventId: Long, override val tMs: Long, override val packageName: String,
    val className: String? = null, val windowId: Int? = null) : UiEvent
data class ContentChanged(override val eventId: Long, override val tMs: Long, override val packageName: String?,
    val rect: PxRect? = null, val changeTypes: List<String> = emptyList()) : UiEvent
data class NodesSnapshot(override val eventId: Long, override val tMs: Long, override val packageName: String?,
    val nodes: List<SnapNode>, val truncated: Boolean, val durationMs: Long) : UiEvent
data class ScreenOff(override val eventId: Long, override val tMs: Long, override val packageName: String? = null) : UiEvent
data class ScreenOn(override val eventId: Long, override val tMs: Long, override val packageName: String? = null) : UiEvent
/** Fields copied out of an AccessibilityEvent on the callback thread. No tree walk. -1 = not reported. */
data class RawEvent(val type: Int, val tMs: Long, val packageName: String?, val className: String?, val windowId: Int,
    val sourceKey: String?, val sourceRect: PxRect?, val scrollDeltaX: Int, val scrollDeltaY: Int, val scrollX: Int,
    val scrollY: Int, val maxScrollX: Int, val maxScrollY: Int, val contentChangeTypes: Int)
data class ScrollDelta(val dx: Int, val dy: Int, val containerId: String?, val containerRect: PxRect?)
interface ScrollNormaliser { fun onScroll(raw: RawEvent): ScrollDelta?; fun reset() }  // content-moved sign
interface SnapSourceNode { val rect: PxRect; val className: String?; val text: String?; val contentDescription: String?
    val viewId: String?; val visible: Boolean; val childCount: Int; fun child(i: Int): SnapSourceNode? }
interface LayoutSnapshotter { fun snapshot(): NodesSnapshot? }  // null if < 250 ms since the last one; pull only
sealed interface ScreenshotResult { data class Ok(val bitmap: android.graphics.Bitmap, val tMs: Long) : ScreenshotResult
    data class Failed(val code: Int) : ScreenshotResult }
/** Backup capture path for 4.1 (about 3 fps, no consent dialog). */
interface ScreenshotSource { val available: Boolean; fun takeScreenshot(onResult: (ScreenshotResult) -> Unit) }
object SignalsHub { @Volatile var screenshots: ScreenshotSource? = null; @Volatile var snapshotter: LayoutSnapshotter? = null
    @Volatile var foregroundPackage: String? = null }   // set by the service while it is connected; null otherwise
```
Stubs: `signals/ScrollTracker.kt`: `class ScrollTracker : ScrollNormaliser { override fun onScroll(raw: RawEvent): ScrollDelta? = null; override fun reset() {} }`.
`signals/BoundedSnapshotter.kt`: `class BoundedSnapshotter(private val root: () -> SnapSourceNode?, private val clock: () -> Long, val budgetMs: Long = 40, val maxNodes: Int = 300, val minGapMs: Long = 250, private val ids: () -> Long = { 0 }) : LayoutSnapshotter { override fun snapshot(): NodesSnapshot? = null; fun startPump(sink: (UiEvent) -> Unit) {}; fun stopPump() {} }`.
Also empty `workshop/signals/__init__.py` and `workshop/signals/tests/__init__.py` (owned by 4.2.1).
Gradle (inside verify scripts): `. tools\env.ps1; & guard\gradlew.bat -p guard --no-daemon :app:assembleDebug :app:testDebugUnitTest --tests "com.veil.guard.signals.<Test>"`. Run ktlint as `& "$env:JAVA_HOME\bin\java.exe" -jar "$env:VEIL_TOOLCHAIN\ktlint\ktlint.jar" <owned .kt files>` (check mode), and ruff on the owned .py files.

## 3. Sub-phases

### 4.2.1 Accessibility service and event logger (M)
- **Goal:** turn events into UiEvents, provide the JSONL logging mode on the shared clock, track the foreground app, provide the screenshot source, and write the restricted-settings doc.
- **Owned paths:** `signals/{Contracts,GuardAccessibilityService,EventMapper,UiEventJson,EventLogger,ForegroundTracker,A11yScreenshotSource,A11yNode,LogControlReceiver}.kt`, `guard/app/src/main/AndroidManifest.xml`, `res/xml/guard_accessibility_service.xml`, `res/values/strings.xml` (add only), `guard/app/src/test/java/com/veil/guard/signals/{EventMapperTest,UiEventJsonTest,ForegroundTrackerTest}.kt`, `workshop/signals/{__init__,pull_log}.py`, `workshop/signals/tests/{__init__,test_pull_log}.py`, `docs/restricted-settings.md`, `tools/verify/4.2.1.ps1`.
- **Steps:**
  1. Service config: `typeViewScrolled|typeWindowStateChanged|typeWindowContentChanged|typeWindowsChanged`, `feedbackGeneric`, `notificationTimeout="50"`, `canRetrieveWindowContent="true"`, `canTakeScreenshot="true"`, flags `flagRetrieveInteractiveWindows|flagReportViewIds`. Register it in the manifest the same way as the probe.
  2. `onAccessibilityEvent`: copy the fields into `RawEvent` (for scroll events only, one `event.source` fetch for rect and key, then recycle). Pass it to `EventMapper.map(raw, nextId): UiEvent?`. Scroll events go through `ScrollTracker().onScroll`, and a null result means no event. Window state events become `WindowChanged`. Content changes become `ContentChanged` with the change-type names. A windows-changed event calls `scroll.reset()`. A dynamic screen on/off receiver emits `ScreenOn`/`ScreenOff`.
  3. `ForegroundTracker.onWindowState(pkg, className): String?`: ignore our own package, `com.android.systemui`, and IME packages (a set). Keep the last real app. Write it to `SignalsHub.foregroundPackage`.
  4. `EventLogger`: run `adb shell am broadcast -a com.veil.guard.LOG -n com.veil.guard/.signals.LogControlReceiver --es cmd start|stop --es name <s>`. Write `filesDir/signals/<name>.events.jsonl` (one `UiEventJson.toJson` per line, flushed every 500 ms and on stop) and `<name>.clock.json` `{uptimeMs, elapsedRealtimeMs}`. On start, also call `snapshotter.startPump(logger::write)`.
  5. `A11yScreenshotSource(service)`: wraps `takeScreenshot(DEFAULT_DISPLAY, …)` with `Bitmap.wrapHardwareBuffer` and `tMs = timestamp/1_000_000`. Set `SignalsHub` on connect and clear it on unbind. `A11yNode` adapts `AccessibilityNodeInfo` to `SnapSourceNode`.
  6. `pull_log.py --name <s> [--boottime] --out data/signals`: uses `adb exec-out run-as com.veil.guard cat files/signals/...`.
  7. `docs/restricted-settings.md`: the iQOO steps (App info → ⋮ → Allow restricted settings → Accessibility → Veil Guard), plus screenshot placeholders.
- **Tests:** mapper (each event kind, field mapping, null package), JSON (keys and omitted nulls; a test writes 1,000 mixed events to `build/tmp/uievents-1000.jsonl`), tracker (a 20-switch sequence with systemui/IME noise).
- **Verify `4.2.1.ps1`:** gradle build plus the 3 tests → `uv run --locked python -m workshop.contracts.validate guard\app\build\tmp\uievents-1000.jsonl --type UiEvent --jsonl` → grep check: `GuardAccessibilityService.kt` and `EventMapper.kt` contain none of `getChild|rootInActiveWindow|findAccessibilityNodeInfos|getWindows|\.windows\b` → ktlint, ruff, pytest. `-Phone`: install, start log, `drive scroll`, stop, pull, validate. Ends with `VERIFY 4.2.1: PASS`.

### 4.2.2 Accurate scrolling (M)
- **Goal:** report content-moved dx/dy in screen px for both delta-style and Compose-style events, plus the frame-difference fallback and the accuracy tooling.
- **Owned paths:** `signals/{ScrollTracker,FrameShiftEstimator}.kt`, `test/.../signals/{ScrollTrackerTest,FrameShiftEstimatorTest}.kt`, `workshop/signals/scroll_ruler.py`, `workshop/signals/tests/test_scroll_ruler.py` (+ fixtures under `workshop/signals/tests/fixtures/`), `tools/verify/4.2.2.ps1`.
- **Steps:**
  1. Container key = `"$windowId/${sourceKey ?: className}"`.
  2. If `scrollDeltaX/Y` ≠ 0, report `dx=-deltaX, dy=-deltaY`.
  3. Otherwise, if `scrollX/Y` ≥ 0 (Compose and other absolute reporters), diff against the last value for that key: `dy = -(cur - last)`. The first event for a key only stores the value and returns null. A jump with |diff| > 4 × container height counts as a reset (store, return null).
  4. A zero result, or index-only data, returns null. `reset()` clears all keys.
  5. `FrameShiftEstimator.estimate(prev: IntArray, cur: IntArray, w: Int, h: Int, maxShift: Int): Int?` works on grey row profiles and searches for the best vertical shift (SAD). It returns content-moved dy, or null when confidence is low.
  6. `scroll_ruler.py --guard <events.jsonl> --truth <feedlog.jsonl | estimate.jsonl>`: splits gestures at gaps > 150 ms. Per gesture, error = |Σ guard dy − (−ΔscrollY truth)|, and direction is checked. It prints a per-app table (mean error, direction %) and `RULER: PASS|FAIL`.
- **Tests:** a positive Android delta gives negative content dy, Compose absolute sequences per key (two interleaved containers), first event, reset, the jump guard, the estimator on a synthetic shifted profile (±1 px), and the ruler on fixture logs (one passing, one with a wrong sign).
- **Verify `4.2.2.ps1`:** gradle tests, ktlint, ruff, pytest. `-Phone`: proof test §5 machine part. Ends with `VERIFY 4.2.2: PASS`.

### 4.2.3 Bounded layout snapshot (M)
- **Goal:** a pull-only snapshot with a 40 ms budget, a 300-node limit and at least 250 ms between calls, plus the cost and frame-stat tooling.
- **Owned paths:** `signals/BoundedSnapshotter.kt`, `test/.../signals/BoundedSnapshotterTest.kt`, `workshop/signals/{snap_cost,frame_stats}.py`, `workshop/signals/tests/{test_snap_cost,test_frame_stats}.py` (+ fixtures), `tools/verify/4.2.3.ps1`.
- **Steps:**
  1. `snapshot()`: return null if `clock() - last < minGapMs`. Otherwise run an iterative BFS from `root()`, skipping invisible and offscreen nodes. Check `clock()` at every node, and stop with `truncated=true` when `≥ budgetMs` or `maxNodes` is reached.
  2. Kind by class: Image→image; Video/Surface/Texture/PlayerView→video; WebView→web; non-blank text→text; Recycler/ListView/Lazy→list; everything else is skipped. Text is clipped to 2000 chars and the description to 500.
  3. `durationMs` comes from the clock. Log `VEIL_SNAP ms=<d> nodes=<n> truncated=<b>`.
  4. `startPump(sink)` runs on a HandlerThread every `minGapMs`. It is the only caller in this phase.
  5. `snap_cost.py` parses `VEIL_SNAP` lines from logcat and prints p50/p95/max ms and max nodes, then `SNAP: PASS` if p95 ≤ 40 and nodes ≤ 300.
  6. `frame_stats.py --package com.instagram.android`: runs `dumpsys gfxinfo <pkg> reset`, 30 × `drive scroll`, and parses "Janky frames" %. It does this with the service off, then on (`settings put secure enabled_accessibility_services`), and prints the difference in percentage points.
- **Tests:** a fake tree of 1,000 nodes is capped at 300 with `truncated`, a fake clock advancing 1 ms per node stops at 40, a second call within 250 ms returns null, kind mapping works, and both parsers run on fixture text.
- **Verify `4.2.3.ps1`:** gradle tests, ktlint, ruff, pytest. `-Phone`: pump for 60 s in Instagram plus `snap_cost`, and `frame_stats`. Ends with `VERIFY 4.2.3: PASS`.

## 4. Acceptance plan
| AC | Criterion | Pass threshold (PLAN, verbatim) | Type | How |
| --- | --- | --- | --- | --- |
| AC-4.2-01 | Events valid | 1,000 logged events all validate against the `UiEvent` contract | AUTO + PHONE | 4.2.1 synthetic 1,000; real log via `-Phone` |
| AC-4.2-02 | Scroll accurate | Mean error ≤ 8 px per scroll in Instagram, YouTube and Chrome; direction correct in 100% of checked cases | PHONE | `scroll_ruler.py` table |
| AC-4.2-03 | Logger in sync | Logged scrolls within ± 1 frame of the screen recording | PHONE | `record.py --events` (pulled with `--boottime`) + `sync_check` |
| AC-4.2-04 | Snapshot within budget | p95 ≤ 40 ms, ≤ 300 nodes, called at most once every 250 ms | AUTO + PHONE | unit tests; `snap_cost.py` |
| AC-4.2-05 | No tree walks in callbacks | Zero layout-tree walks inside event handling | AUTO | grep check in 4.2.1 + review |
| AC-4.2-06 | Watched app stays smooth | Instagram dropped-frame rate with the service on vs off differs by ≤ 1 percentage point | PHONE | `frame_stats.py` |
| AC-4.2-07 | Right app known | Foreground app correct across 20 app switches | AUTO + PHONE | tracker test; 20 switches on the phone |
| AC-4.2-08 | Sideload setup works | Restricted-settings steps written and tested on the iQOO | HUMAN | `docs/restricted-settings.md` + screenshots |

## 5. Proof test "Scroll ruler" (`tools/verify/pt-4.2.ps1`, written by 4.2.2; it runs only with the phone)
- **Machine part:**
  1. Install guard + testfeed and start the log.
  2. 100 scrolls and flings at varied speeds (`drive scroll --duration 120..600` mixed with `fling`).
  3. Pull both logs, then run `scroll_ruler.py` (Test Feed truth).
  4. In Instagram, YouTube and Chrome: `record.py` with a 30 s recording and the guard log, then the ruler against the estimate.
  5. Run `snap_cost.py` and `frame_stats.py`, and capture a Perfetto trace (`adb shell perfetto -o … -t 20s gfx view am`).
  6. Write the report to `data/signals/pt-4.2/report.md`. Pass rule: **AC-4.2-02 to AC-4.2-06 hold.**
- **Human part (about 5 min):** watch one Instagram run, and confirm the feed doesn't feel slower with the service on and that the event counter moves.

## 6. Human items checklist (one sitting, about 25 min, PENDING-HUMAN)
- [ ] Connect the iQOO. Install the guard debug APK, then do Allow restricted settings and enable "Veil Guard signals". Take screenshots of each screen for `docs/restricted-settings.md` (AC-08).
- [ ] Run `tools\verify\4.2.1.ps1 -Phone` (real log validates, AC-01).
- [ ] Do 20 app switches and check that the logged foreground app matches each one (AC-07).
- [ ] Run `tools\verify\pt-4.2.ps1` (AC-02..06). Have Instagram, YouTube and Chrome logged in, and keep the phone unlocked and awake.
- [ ] Do the Instagram smoothness side-by-side with the service on and off (AC-06 human view).
