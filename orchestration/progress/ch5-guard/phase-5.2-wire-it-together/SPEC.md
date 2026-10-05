# SPEC Phase 5.2 Wire it together
MODEL: claude-opus-5-5 · Status: APPROVED (orchestrator; Gradle queue after 4.1) · PLAN.md lines 1618-1722 · Entry: 5.1 built (JVM); 4.2/4.3/3.3 specified, NOT built; 4.1 building; phone NOT connected.

## 1. Deviations / risks
- **DV-1 Ports, not live adapters.** All logic lives in a new pure-JVM module `guard/conductor` (deps: `:brain` only) behind the ports in §2. The live Android adapters (4.1 `CapturedFrame` → `Frame`, 4.2 `UiEvent`/`SnapNode` → brain `UiEvent`/`LayoutNode`, 4.3 `OverlaySink`/`OverlayHost` ← `OverlayPort`, 3.3 `ResidentModels`/`SerialWorker` → `AiWorker`/detectors) are **DEFERRED** to `progress/DEFERRED.md` item "5.2-W live wiring" (≈1 file, `app/.../wire/LiveWiring.kt`), built once 4.2/4.3/3.3 are committed. Their types are referenced only in comments now.
- **DV-2 Toxicity tokenizer + real model runs DEFERRED** (same as 5.1's SigLIP2 tokenizer): `TextClassifier`, `Describer`, `Finder`, `NsfwDetector` have fakes in tests; GPU crop/resize lives inside the real `Describer` adapter (5.2-W).
- **DV-3 Layer 1 "longer hold":** brain `Tracker` has no per-layer hold and is frozen by tape parity; do NOT edit `:brain`. Layer 1 gets first-sighting confirm + solid + non-peekable (already in brain). Longer hold → DEFERRED to 5.3 as a twin+brain change via waiver.
- **R-1 Parity** is defined on the 3 golden tapes (`contracts/tapes`, twin output = `*.tape-out.jsonl`) with a scripted detector; synthetic sessions only if `veil/data/ch2/synth-test` exists (else print `SKIP synth`).
- **R-2 ML Kit** pinned `com.google.mlkit:text-recognition:16.0.1` (bundled Latin). If it fails to resolve in 2 min, 5.2.3 reports it, the line is removed and OCR is DEFERRED (AC-5.2-06 OCR part PENDING).
- **R-3 Gradle:** one build at a time via the mutex below; JVM tests run with `"-Pveil.brainOnly=true"` (fast, no `:app`); only `:app:compileDebugKotlin` needs the full build.

## 2. Shared interfaces (Wave 0, 5.2.1 writes in the first 3 min; nobody else edits)
- `guard/settings.gradle.kts`: add OUTSIDE the `!brainOnly` block: `if (file("conductor/build.gradle.kts").exists()) include(":conductor")`.
- `guard/conductor/build.gradle.kts`: copy `guard/brain/build.gradle.kts` (same plugin, toolchain 17, junit, kotlinx-serialization-json 1.8.1 test dep, `veil.tapes`/`veil.repo` props, 512m heap) + `implementation(project(":brain"))`.
- `guard/app/build.gradle.kts`: add `implementation(project(":conductor"))` and `implementation("com.google.mlkit:text-recognition:16.0.1")`.
- Gradle (all verify scripts): `$m=New-Object System.Threading.Mutex($false,'Global\veil-gradle'); [void]$m.WaitOne(); try { powershell -NoProfile -ExecutionPolicy Bypass -File tools\with-env.ps1 --cd guard .\gradlew.bat --no-daemon "-Pveil.brainOnly=true" :conductor:test --tests "com.veil.conductor.<T>" } finally { $m.ReleaseMutex() }`. ktlint: `& "$env:JAVA_HOME\bin\java.exe" -jar "$env:VEIL_TOOLCHAIN\ktlint\ktlint.jar" <owned .kt>` (inside with-env).
`guard/conductor/src/main/kotlin/com/veil/conductor/Ports.kt`:
```kotlin
package com.veil.conductor
import com.veil.brain.contract.CompiledConcept
import com.veil.brain.contract.Finding
import com.veil.brain.contract.FrameMeta
import com.veil.brain.contract.Record
import com.veil.brain.contract.Rect
/** thumb = brain THUMB_W x THUMB_H gray; argb = frame-size pixels (null in pure tests). Rects everywhere are SCREEN px. */
class Frame(val meta: FrameMeta, val thumb: ByteArray, val argb: IntArray? = null)
data class LayoutNode(val kind: String, val rect: Rect, val text: String? = null) // kind as 4.2 SnapNode: image|video|web|text|list|post|other
enum class Source(val wire: String) { LAYOUT("layout"), FINDER("finder"), TILE("tile"), CROP("crop"), WHOLE("whole") }
data class Piece(val id: String, val rect: Rect, val source: Source, val kind: String, val lookId: Int, val parentId: String? = null)
data class LookInput(val lookId: Int, val frame: Frame, val rect: Rect, val layout: List<LayoutNode>, val mode: String)
data class Concepts(val describer: List<CompiledConcept>, val finder: List<CompiledConcept>, val keywords: Map<String, List<String>>)
fun interface Lane { fun run(input: LookInput): List<Finding> }                  // runs ON the AI worker
interface Describer { fun describe(frame: Frame, pieces: List<Piece>): List<FloatArray> } // one call, pieces.size <= 16
interface Finder { fun boxes(frame: Frame, area: Rect): List<Pair<Rect, FloatArray>> }    // box + its own fingerprint
data class NsfwBox(val cls: Int, val score: Float, val rect: Rect)
interface NsfwDetector { val id: String; fun detect(frame: Frame, area: Rect): List<NsfwBox> } // "nudenet-320n" | "nudenet-640m"
fun interface Ocr { fun read(frame: Frame, rect: Rect): String? }
fun interface TextClassifier { fun toxicity(text: String): Double }
interface AiWorker { val busy: Boolean; fun submit(job: () -> List<Finding>, done: (List<Finding>, Long) -> Unit) } // Long = aiMs
interface OverlayPort { fun submit(plan: Record); fun shift(dx: Int, dy: Int, tMs: Long) } // plan = mask-plan v1.0 map
fun interface StatsSink { fun publish(stats: Record) }
fun interface DebugLog { fun write(rec: Record) }   // one JSON line each: kind = look|finding|plan|stats|pause
class Counters { val m = java.util.concurrent.ConcurrentHashMap<String, Long>(); fun add(k: String, n: Long = 1) { m.merge(k, n, Long::plus) } }
```
Counter keys (lanes add, conductor publishes): `pieces.layout|pieces.finder|pieces.tile|pieces.crop|pieces.whole`, `cacheHits`, `cacheMisses`, `describerCalls`, `describerMaxBatch` (max, via `m.merge(k,n,::maxOf)`), `layer1.320n`, `layer1.640m`, `ocrCalls`, `toxicityCalls`, `textSeen`.

## 3. Sub-phases (all three in parallel after Wave 0)
Paths below are under `veil/guard/conductor/src/{main,test}/kotlin/com/veil/conductor/` unless absolute-ish.

### 5.2.1 The conductor (+ replay mode, parity test)
Goal: every look in order, never queuing; replay mode; parity vs twin. Owned: `settings.gradle.kts` line, `conductor/build.gradle.kts`, `Ports.kt`, `Conductor.kt`, `Thumbs.kt`, `Replay.kt`, `test/ConductorTest.kt`, `test/ReplayParityTest.kt`, `test/Fakes.kt` (ManualWorker, ScriptedLane, RecordingOverlay), `app/build.gradle.kts` lines, `app/src/debug/java/com/veil/guard/replay/ReplayActivity.kt`, `app/src/debug/AndroidManifest.xml` (create or insert one element), `tools/verify/5.2.1.ps1`.
Key API: `class Conductor(mode: String, paramsJson: String, lanes: List<Lane>, worker: AiWorker, overlay: OverlayPort, stats: StatsSink, log: DebugLog, counters: Counters, skipApps: Set<String>, layout: () -> List<LayoutNode>)` with `fun onEvent(e: com.veil.brain.contract.UiEvent)`, `fun offer(f: Frame)` (1-slot mailbox: a newer frame replaces an untaken one, `framesSkipped++`), `fun pump()` (takes the slot and steps; the live adapter calls it from one conductor thread, tests call it directly), `val paused: Boolean`.
Steps:
1. Wraps one `BrainPipeline(mode, paramsJson)` (do not modify `:brain`). Per frame: `pipeline.step(thumb, meta)` → if `look.look==true`: worker free → `submit { lanes.flatMap { it.run(LookInput(...rect=look.rect)) } }`, on done `pipeline.enqueue(each finding)` + stats; worker busy → `framesSkippedBusy++` (no queue, ever). Every maskPlan record → `overlay.submit(plan)`; log look/finding/plan.
2. `onEvent`: forward to `pipeline.onEvent`; `scrolled` → also `overlay.shift(dx, dy, tMs)` immediately (no AI). `screenOff` or `windowChanged` to a pkg in `skipApps` → paused: submit one empty plan (reason `clear`), log `pause`, drop frames (`framesSkippedPaused++`, 0 looks); `screenOn`/`windowChanged` to other pkg → resume.
3. Stats after each completed look (`engine-stats` names where they exist): `tMs, mode, looksTotal, looksPerSecond` (last 5 s), `aiMsLast, aiMsMean, cacheHits, activeCovers` (masks in last plan), `framesSeen, framesAnalysed, framesSkipped, framesSkippedBusy, framesSkippedPaused, paused, counters`.
4. `Thumbs.fromArgb(argb, w, h): ByteArray` = port of `workshop/twin/change.py:thumb`. `Replay`: `fun run(c: Conductor, frames: Sequence<Frame>, events: List<UiEvent>, findings: List<Record>)` interleaves by `tMs` (events before a frame at equal tMs, as `TapeReplay`), writes `plans.jsonl`.
5. `ReplayParityTest`: for each golden tape, drive a Conductor through Replay with `ManualWorker` (job runs when the tape's first finding with that look's frameId arrives; findings without a pending look are enqueued directly and counted) and `ScriptedLane` (returns tape findings for that frameId). Per frame, each twin mask matched to a Kotlin mask with IoU ≥ 0.9; assert ≥ 95% matched; print `PARITY <tape> masks=<n> matched=<pct>`.
6. `ConductorTest`: (a) 600 frames at 16 ms with a worker taking 300 ms → pending looks never > 1, `framesSkippedBusy > 0`; (b) screenOff and a skipped app → 0 looks, `paused`; (c) scrolled → `shift` called before the next frame; (d) stats published after each look.
7. `ReplayActivity` (debug, `android:exported="true" android:permission="android.permission.DUMP"`): extras `video`, `events`, `findings` (files in `/sdcard/Android/media/com.veil.guard/replay/`); `MediaMetadataRetriever.getFrameAtIndex` at the video fps → 360-wide ARGB → `Frame`; ScriptedLane + a thread worker; writes `files/replay/plans.jsonl`.
Verify `tools/verify/5.2.1.ps1`: ConductorTest + ReplayParityTest (print PARITY lines), `:app:compileDebugKotlin` (full build, mutex), ktlint → `VERIFY 5.2.1: PASS`.

### 5.2.2 Pieces from three sources (+ cat-feed checker)
Goal: all relevant pieces, deduped, cached, batched. Owned: `regions/RegionProposer.kt`, `regions/RegionLane.kt`, `regions/Hashes.kt`, `test/regions/*`, `workshop/guardcheck/__init__.py`, `workshop/guardcheck/cat_feed.py`, `workshop/guardcheck/tests/test_cat_feed.py`, `tools/verify/pt-5.2.ps1`, `tools/verify/5.2.2.ps1`.
Key API: `class RegionProposer(grid: Pair<Int,Int> = 3 to 6, overlap: Double = 0.25, tallCrops: Int = 3)` `fun propose(input: LookInput, finderBoxes: List<Rect>): List<Piece>`; `class RegionLane(concepts: Concepts, describer: Describer, finder: Finder?, cache: FingerprintCache, counters: Counters, proposer: RegionProposer = RegionProposer()) : Lane`.
Steps:
1. Layout nodes of kind `image|video|post` → `Source.LAYOUT` pieces (kind kept; `web/list/other` dropped, `text` left to the text lane). Finder boxes → `FINDER` (kind `object`). Tiles/crops/whole = exact port of `workshop/twin/pieces.py:make_pieces` on the screen size, kept only if they overlap `input.rect` ≥ 25 % of the piece.
2. Dedupe: IoU (`com.veil.brain.cover.iouPct`) ≥ 80 → keep by priority layout > finder > tile > crop > whole.
3. Per piece: `h = Hashes.dhash64(frame, rect)` (gray 9x8 dHash; bit-exact phash is DEFERRED per 5.1) → `cache.get(h, tMs)`; hits reuse the vector, misses go to `describer.describe` in chunks of ≤ 16 (Explore grids land here), then `cache.put`. Finder pieces use their own fingerprint and the `concepts.finder` cards; others use `concepts.describer`.
4. `Judge.judge` per concept → findings ported from `workshop/twin/judge.py:to_findings` (keep `decision != "leave"`; lane `describer`|`finder`, layer 2). Counters as §2.
5. `cat_feed.py`: reads Guard `debug.jsonl` plans + Test Feed `feedlog.jsonl` (reuse `workshop/bench/testfeed.py`); per feed frame, each visible `cat|spider` item ≥ 80 % covered (after 300 ms grace), clean/lookalike items < 10 % covered; prints a report, exit 0 iff clean. Pytest on two tiny synthetic log pairs (pass + fail). `pt-5.2.ps1` = the PENDING-HUMAN driver (§5).
Tests: Instagram-like fixture (3 post nodes, 1 image, 12 Explore thumbnails, 2 finder boxes) → all three sources present, dupes removed, `describerMaxBatch ≤ 16`, second identical look = all cache hits, 0 describer calls.
Verify `5.2.2.ps1`: `:conductor:test --tests "com.veil.conductor.regions.*"`, ktlint, `uv run --locked pytest workshop/guardcheck -q`, ruff → `VERIFY 5.2.2: PASS`.

### 5.2.3 Layer 1 and the text lane
Goal: always-on safety + text filtering. Owned: `layer1/Layer1Lane.kt`, `layer1/NudeDecode.kt`, `text/TextLane.kt`, `test/layer1/*`, `test/text/*`, `app/src/main/java/com/veil/guard/wire/MlKitOcr.kt`, `tools/verify/5.2.3.ps1`.
Key API: `class Layer1Lane(small: NsfwDetector, large: NsfwDetector?, counters: Counters, thr: Double = 0.45) : Lane`; `object NudeDecode { fun decode(raw: FloatArray, n: Int, c: Int, conf: Float, iou: Float, lb: Triple<Float,Float,Float>): List<NsfwBox> }` (port of `workshop/forge/nudenet/decode.py`, for the 5.2-W adapter); `class TextLane(concepts: Concepts, tox: TextClassifier?, ocr: Ocr?, counters: Counters, toxThr: Map<String, Double> = mapOf("light" to 0.7, "balanced" to 0.5, "strict" to 0.35)) : Lane`.
Steps:
1. Layer 1: run `small` (320n) every look; run `large` (640m) only when mode is `balanced|strict`; merge boxes IoU ≥ 50. Layer-1 classes = NudeNet `*_EXPOSED` genital/breast/buttocks/anus labels (indices from the nudenet label list; confirm in the forge code). Finding: `layer=1, lane="layer1", conceptId="layer1", decision="hide", scope="object"`. Brain confirms layer 1 on first sighting and plans it solid + `peekable=false`.
2. Text: candidate texts = layout `text` nodes first. OCR only for layout `image` nodes (≤ 4 per look, largest first), never for text nodes. Normalise (trim, lowercase, collapse spaces); a 2000-entry LRU of seen texts → toxicity runs only on unseen text (`toxicityCalls`), seen text reuses its score. Keyword rules: `concepts.keywords[conceptId]`, case-insensitive whole word.
3. A hit covers the whole post: rect = smallest layout `post` node containing the text node (else the text node). `layer=2, lane="text", decision="hide", scope="post"`, conceptId = keyword's concept or `text.toxic`.
4. `MlKitOcr : Ocr` (Android): crop `frame.argb` (screen→frame scale) → `Bitmap` → `Tasks.await(TextRecognition.getClient(TextRecognizerOptions.DEFAULT_OPTIONS).process(InputImage.fromBitmap(b, 0)))`.text`.
Tests (fakes only; no explicit content): 320n-only in light, both in balanced; layer-1 finding → plan mask `style=solid, peekable=false` on the first look (through a real `BrainPipeline` step); text: abusive fake text → post rect covered; same text twice → `toxicityCalls == 1`; OCR called only for image nodes; keyword hit; NudeDecode vs a small hand-made raw array.
Verify `5.2.3.ps1`: `:conductor:test --tests "com.veil.conductor.layer1.*" --tests "com.veil.conductor.text.*"`, `:app:compileDebugKotlin`, ktlint → `VERIFY 5.2.3: PASS`.

## 4. Acceptance criteria
| ID | Criterion | Pass threshold | How verified | Now |
| --- | --- | --- | --- | --- |
| AC-5.2-01 | Works live | A cat in a live Instagram feed is covered; the cover follows scrolling; covers clear on app switch | Recorded demonstration | PHONE (after 5.2-W) |
| AC-5.2-02 | Respects off states | 0 looks with the screen off and in skipped apps | Stats log | AUTO ConductorTest(b) + PHONE |
| AC-5.2-03 | Never queues | No backlog under load; skipped frames counted | Trace | AUTO ConductorTest(a) + PHONE |
| AC-5.2-04 | All piece sources used | Layout, finder and tiles each produce pieces on Instagram; Explore thumbnails batched ≤ 16 per AI call | Stats; trace | AUTO fixture + PHONE |
| AC-5.2-05 | Layer 1 live | Controlled test images get a solid cover on first sighting; peek is disabled for them | Test log | AUTO fakes + PHONE (human-supplied set) |
| AC-5.2-06 | Text lane live | An abusive-comment test page is covered; OCR runs only on text inside images; toxicity runs only on new text | Counters; test log | AUTO fakes + PHONE |
| AC-5.2-07 | Matches the twin | The same recording replayed on the phone gives cover plans matching the twin's (overlap ≥ 0.9 for ≥ 95% of covers) | Integration parity test | AUTO JVM ReplayParityTest + PHONE ReplayActivity |

## 5. Proof test "The cat feed" (PENDING-HUMAN, needs 5.2-W + phone)
`tools/verify/pt-5.2.ps1`: install Guard + Test Feed (Balanced) → `workshop/bench/drive.py` scrolls the known cat/spider/lookalike/clean set → pull `debug.jsonl` + `feedlog.jsonl` → `cat_feed.py` report; repeat with Layer 1 stand-in set and the abusive-comment page; screen off 60 s + open a skip-list app (stats must show 0 looks); 5-min Instagram session recorded with scrcpy. Passes when AC-5.2-01..07 hold and the checker report is clean. Evidence → `progress/ch5-guard/phase-5.2-wire-it-together/evidence/`.

## 6. Human checklist
1. After 5.2-W: run `pt-5.2.ps1` with the phone connected; keep the scrcpy recording.
2. Supply the controlled Layer 1 evaluation set by hand (agents never fetch it); confirm solid, non-peekable covers.
3. Instagram test account: watch a cat get covered, scroll, switch apps; Explore grid small cats.
4. Run ReplayActivity on one recorded session; confirm `PARITY` ≥ 95 % vs the twin.
