# SPEC 5.1 Port the brain
MODEL: claude-opus-5-5 (Refiner) · status **DRAFT** · 2026-10-02 · PLAN.md lines 1507-1617 · fast track F1-F12

Run everything from `D:\iqoo finale\veil` as `powershell -NoProfile -ExecutionPolicy Bypass -File tools\with-env.ps1 <cmd>`. Gradle: `cd guard; .\gradlew.bat --no-daemon <task>` (2 GB cap already in `gradle.properties`). ktlint: `& "$env:JAVA_HOME\bin\java.exe" -jar "$env:VEIL_TOOLCHAIN\ktlint\ktlint.jar" "<module>/src/**/*.kt"` (exit 0). The phone is NOT connected: instrumented tests must compile (`:app:assembleDebugAndroidTest`) but run only later (PHONE).

## 1. Deviations and risks
- **D1 Work split, not PLAN's file split:** to balance three 15-min builders, 5.1.1 ports change/scheduler/gatekeeper/judge/cache, while 5.1.2 ports tracker/planner/motion core *and* runs the tapes (it debugs what the tapes check most). All of it still lives in the one `guard/brain` module.
- **D2 Tapes hold no cache or judge records** (`run_tape` uses `use_cache=False` and oracle findings). So the cache-hit sequence and Judge parity are checked against **derived fixtures** that a Python ref script writes (`guard/brain/src/test/resources/*.json`, committed). The golden tapes are untouched (rule 12.9).
- **D3 phash64/signature are pixel ops (cv2 DCT/resize).** The Kotlin cache takes `(hash, sig)` as inputs; computing them from pixels on the phone is 5.2. DEFERRED: bit-exact phash.
- **D4 Store = AES-256-GCM encrypted JSON document** (settings, cards, corrections), with the key from an injected `KeyProvider` (Android Keystore on the phone, fixed test key on the JVM). There is no SQL database. It meets AC-5.1-06's "unreadable without key".
- **D5 Teacher scope:** a port of `teacher.concept_card` and `compile_concept` (the lookalike dict as in Python, so cards match the Workshop). The PLAN "nearest nouns from a vocabulary" step and the **object finder's text encoder** (no YOLOE text ONNX exists, and MobileCLIP2 is research-only) are DEFERRED.
- **R1 Teacher parity on the laptop** uses onnxruntime-java and DJL HF tokenizers with `siglip2-text.onnx`. If it OOMs or runs past 5 min, mark AC-5.1-05 DEFERRED (F6) and do not tune.
- **R2 Float detail:** JDK 17 has no `Float.float16ToFloat`, so write the half-to-float decoder by hand. The Judge does its maths in `Double`. numpy's BLAS sum order differs from a plain loop, so compare probabilities with tol 1e-9, and decisions exactly unless |p − thr| < 0.001.
- **R3 settings.gradle.kts** is the only shared file. 5.1.1 writes it first (content in §2). Verify order is 5.1.1 → 5.1.2 → 5.1.3, serialised by the orchestrator.

## 2. Shared interfaces (write against these, don't wait)
**`guard/settings.gradle.kts` (5.1.1 owns; final content of the include block):**
```kotlin
include(":brain")
if (file("teacher/build.gradle.kts").exists()) include(":teacher")
if (!providers.gradleProperty("veil.brainOnly").isPresent) {
    include(":app")
    if (file("testfeed/build.gradle.kts").exists()) include(":testfeed")
}
```
**Module `:brain`** (`guard/brain/build.gradle.kts`, 5.1.1): `plugins { id("org.jetbrains.kotlin.jvm") }` (KGP is already on the buildscript classpath), `kotlin { jvmToolchain(17) }`, **main deps: Kotlin stdlib only**, test deps `junit:junit:4.13.2` + `org.jetbrains.kotlinx:kotlinx-serialization-json:<1.x>` (JsonElement API, no compiler plugin). `tasks.test { systemProperty("veil.tapes", rootProject.file("../contracts/tapes").path); systemProperty("veil.repo", rootProject.file("..").path); maxHeapSize = "512m" }`, plus `tasks.register<Test>("tapeTest") { filter.includeTestsMatching("com.veil.brain.tapes.*") }` (same props).

Package `com.veil.brain.contract` (5.1.1 writes `Types.kt` in its first 3 min, exactly as below):
```kotlin
typealias Record = Map<String, Any?>   // mirrors the Python dict: Int/Long/Double/String/Boolean/null/List/Map, same keys incl. "x", no "seq"
data class Rect(val x: Int, val y: Int, val w: Int, val h: Int) { fun toMap(): Record }
data class UiEvent(val type: String, val tMs: Long, val dx: Int = 0, val dy: Int = 0, val packageName: String? = null, val raw: Record = emptyMap())
data class FrameMeta(val frameId: Int, val tMs: Long, val width: Int, val height: Int, val screenWidth: Int, val screenHeight: Int, val ownOverlay: List<Rect>)
data class Finding(val findingId: String, val frameId: Int, val lookId: Int, val tMs: Long, val conceptId: String, val layer: Int,
    val decision: String, val probability: Double, val rect: Rect, val scope: String, val lane: String)
data class Track(val trackId: Int, val conceptId: String, val layer: Int, val rect: Rect, val state: String, val sightings: Int,
    val firstSeenMs: Long, val lastSeenMs: Long, val holdUntilMs: Long, val maxHoldUntilMs: Long, val lastFindingId: String,
    val peeked: Boolean, val scope: String, val selfCaptureFraction: Double) { fun toMap(): Record }
data class Embedding(val dim: Int, val vectorF16: String, val raw: Record = emptyMap())
data class CompiledConcept(val conceptId: String, val looksLike: List<Embedding>, val butNot: List<Embedding>, val ignore: List<Embedding>,
    val calibrationOffset: Double, val userOffset: Double, val thresholds: Map<String, Double>, val margin: Double,
    val exampleCentroid: Embedding? = null, val exampleThreshold: Double? = null, val raw: Record = emptyMap())
data class Verdict(val pRaw: Double, val probability: Double, val score: Double, val margin: Double, val decision: String, val exampleScore: Double? = null)
```
`com.veil.brain.gate` (5.1.1), which 5.1.2's motion core depends on:
```kotlin
interface Gate {                          // = workshop.twin.gatekeeper.GatekeeperPipeline
    var busyUntil: Long
    var rateMul: Int                      // motion.py line 58 multiplies mp.rate
    fun onEvent(event: UiEvent): List<Record>
    fun onThumb(thumb: ByteArray, frame: FrameMeta): Pair<Record, Record>   // (change, look), exactly as on_thumb
}
object Gatekeeper { fun create(mode: String, paramsJson: String, lookMs: Int): Gate }  // paramsJson = workshop/twin/params.json text (hand-parsed or tiny parser, no deps)
```
`com.veil.brain.judge.Judge.judge(vecs: List<DoubleArray>, cc: CompiledConcept, mode: String): List<Verdict>` · `F16.decode(b64: String, dim: Int): FloatArray` (5.1.1).
`com.veil.brain.cache.FingerprintCache(capacity = 8000, maxDist = 10, ttlMs = 60000)`: `get(h: Long, tMs: Long, sig: Sig?): FloatArray?`, `put(...)`, `clear()`, `hits`, `misses`, `size` (5.1.1; `Sig` mirrors `cache.signature`'s tuple).
`com.veil.brain.motion.BrainPipeline(mode: String, paramsJson: String, gate: Gate = Gatekeeper.create(...), latencyMs: Int = 100)`: `onEvent(e)`, `enqueue(f: Finding)`, `step(thumb: ByteArray, frame: FrameMeta): List<Record>` returns `[change, look, tracks, maskPlan]`, the same as `motion.MotionPipeline._step` with `use_cache=False` (5.1.2).
`com.veil.teacher.TextEncoder { val spaceId: String; val textModelId: String; fun encode(phrases: List<String>): List<FloatArray> }` (L2-normalised) · `KeyProvider { fun key(): ByteArray }` (32 bytes) (5.1.3).

## 3. Sub-phases (all three start together)
### 5.1.1 Kotlin decision logic (gate, judge, cache)
**Goal:** a pure-JVM brain module with the contract types, change detector, scheduler, gatekeeper fold, Judge and cache, all faithful to Python.
**Owns:** `guard/settings.gradle.kts`, `guard/brain/build.gradle.kts`, `guard/brain/src/main/kotlin/com/veil/brain/{contract,gate,judge,cache}/**`, `guard/brain/src/test/kotlin/com/veil/brain/unit/**`, `guard/brain/src/test/resources/{judge,cache}-golden.json`, `workshop/brain_ref/{judge_ref,cache_ref}.py`, `tools/verify/5.1.1.ps1`.
**Steps:**
1. Write settings, build file and `Types.kt` per §2 first.
2. Port `change.py` (`detect`, `shift_rows`: Int maths on a `ByteArray` thumb, THUMB_W×THUMB_H), `scheduler.py` (`step`, `_cdiv`, `_better`, fixed tie order), and `gatekeeper.py` (`_fold`, `on_thumb`, `on_event`, params.json per mode). Records use the same keys and order as Python.
3. Port `judge.py` in Double, with `F16` (half→float32→double, as numpy does) and `CompiledConcept` built from a JSON map in the test only.
4. Port `cache.py` `FingerprintCache` (`hamming` = `java.lang.Long.bitCount(a xor b)`, LRU, ttl, ties: smaller dist then newest, `_sig_ok`).
5. Write `judge_ref.py`: `contracts/examples/compiled-concept/*` plus 200 seeded random unit vectors per concept, all 3 modes → `judge-golden.json`. Write `cache_ref.py`: a seeded sequence of 2000 put/get/clear ops → `cache-golden.json` (expected hit/miss per op).
6. Unit tests: Judge golden (decisions exact unless within 0.001 of thr; probability tol 1e-9), cache hit sequence exact, scheduler/change 3-4 hand cases, and `BrainIsPortable` (reads `brain/build.gradle.kts` and asserts no `android` in plugins or deps).

**Verify `tools/verify/5.1.1.ps1`:** regenerate both fixtures (`uv run python -m workshop.brain_ref.judge_ref` and `cache_ref`), then `git diff --exit-code` on them. Run `gradlew --no-daemon -Pveil.brainOnly=true :brain:test --tests "com.veil.brain.unit.*"`, ktlint on `guard/brain`, and grep that `brain/build.gradle.kts` has no `com.android`/`androidx`. Ends with `VERIFY 5.1.1: PASS`. Under 4 min.

### 5.1.2 Golden tape tests (cover port + harness + CI)
**Goal:** the Kotlin tracker, planner and motion core reproduce every golden tape byte-for-byte in record terms, on the laptop and (later) on the phone.
**Owns:** `guard/brain/src/main/kotlin/com/veil/brain/{cover,motion}/**`, `guard/brain/src/test/kotlin/com/veil/brain/tapes/**`, `guard/app/src/androidTest/java/com/veil/guard/brain/**`, `.github/workflows/brain-tapes.yml`, `tools/verify/5.1.2.ps1`.
**Steps:**
1. Port `tracker.py` (as amended by 2.3 A1: `_dy` shift of own covers, a scene cut clears all tracks; integer only, except `_fraction`) and `planner.py` (pad, merge, cap, ordering, labels) into `cover/`.
2. Port `motion.MotionPipeline._step`, `_deliver`, `_confirm_rect` and the reason priority into `motion/BrainPipeline` (no oracle, no cache). Use the `Gate` interface. Until 5.1.1 lands, compile against a 10-line stub `Gate` in test code only.
3. `TapeReplay.kt` (test): read `tapes.json`, check each tape's sha256 (fail if it changed), and replay tape-in the way `motion.run_tape` does (header → pipeline; event → `onEvent`; finding → `enqueue`; frame → base64 thumb → `step`). Keep only the kinds `goldens.py` compares. Compare record by record with tape-out minus `seq`, using structural JSON equality (ints exact; doubles `==`). On mismatch, print tape, frameId, kind and the first differing key path.
4. One JUnit test per tape plus a summary line `TAPES 3/3 exact`.
5. Instrumented `BrainTapeInstrumentedTest` (androidTest): the same replay, with tapes read from androidTest assets (5.1.3 wires the assets dir). It compiles only now; it runs on the phone later.
6. `brain-tapes.yml`: on push/PR, ubuntu, setup-java 17, `cd guard && ./gradlew --no-daemon -Pveil.brainOnly=true :brain:test`.

**Verify `tools/verify/5.1.2.ps1`:** `gradlew --no-daemon -Pveil.brainOnly=true :brain:tapeTest`, then check the output contains `TAPES 3/3 exact`, then ktlint on `guard/brain`, then check the workflow YAML parses (`uv run python -c "import yaml..."`). Ends with `VERIFY 5.1.2: PASS`. Under 4 min.

### 5.1.3 Teacher and encrypted store
**Goal:** build concept cards from words on the device, keep them in an encrypted store, and apply list changes live.
**Owns:** `guard/teacher/**` (JVM module, deps `project(":brain")`, kotlinx-serialization-json, `com.microsoft.onnxruntime:onnxruntime`, `ai.djl.huggingface:tokenizers` test-only), `guard/app/build.gradle.kts`, `guard/app/src/main/AndroidManifest.xml`, `guard/app/src/main/java/com/veil/guard/teacher/**`, `guard/app/src/androidTest/java/com/veil/guard/teacher/**`, `workshop/brain_ref/teacher_ref.py`, `tools/verify/5.1.3.ps1`.
**Steps:**
1. `Teacher.conceptCard(word)` and `compile(concept, enc, calibration, thresholds)`, ported from `teacher.py` (`_singular`, `LOOKS_LIKE`, `IGNORE`, `LOOKALIKES`, offsets clipped, f16 encode). calibration.json and thresholds.json are packaged as resources.
2. `ConceptRegistry`: an atomic swap of `Map<conceptId, CompiledConcept>`, with listeners notified on change, so there is no restart (AC-07). Teaching never runs inside `step` (a separate executor).
3. `SecureStore(file, keyProvider)`: AES-256-GCM, random 12-byte IV per write, atomic temp-file rename, JSON `{settings, cards, corrections}`. Tests: round-trip; reopen after a new instance ("restart"); the raw bytes contain no plaintext marker; a wrong key throws `AEADBadTagException`.
4. JVM `OrtSiglipTextEncoder` (lower-case, pad to 64, tokenizer.json found by `teacher_ref.py` in the HF snapshot and copied to `data/forge/siglip2/tokenizer.json`). `teacher_ref.py` writes `data/ch5/teacher-ref.json` (5 concepts: spiders, cats, clowns, snakes, needles → Python cards and prompt fingerprints). The test `TeacherParity` checks card JSON equal (minus vectors), cosine ≥ 0.99 per prompt, and logs `card ms=` per concept. Run it in its own task `teacherParity` (`maxHeapSize = "1g"`).
5. App: `project(":brain")` and `project(":teacher")` deps, `onnxruntime-android`, `testInstrumentationRunner = "androidx.test.runner.AndroidJUnitRunner"`, androidTest deps, `sourceSets["androidTest"].assets.srcDir("../../contracts/tapes")`. Add `TeacherDebugActivity` (text field → card, shows ms, exports JSON to app files), `KeystoreKeyProvider`, and an Android ORT encoder. Add an instrumented `TeacherStoreInstrumentedTest`: card in ≤ 1 s, store survives process restart, live swap ≤ 1 s.

**Verify `tools/verify/5.1.3.ps1`:** `gradlew --no-daemon -Pveil.brainOnly=true :teacher:test` (store, card, registry), then `:teacher:teacherParity` (skip with a `DEFERRED` line if `data/forge/siglip2/siglip2-text.onnx` is missing or the run exceeds 5 min), then `gradlew --no-daemon :app:assembleDebug :app:assembleDebugAndroidTest`, then ktlint on `guard/teacher` and `guard/app`. Ends with `VERIFY 5.1.3: PASS`. Under 5 min (the parity run is the risk).

## 4. Acceptance criteria
| ID | Criterion | Pass threshold (PLAN) | Mark | How here |
| --- | --- | --- | --- | --- |
| AC-5.1-01 | Tapes pass | 100% of golden tapes give an exact match for the change detector, scheduler, tracker, planner and cache-hit sequence | AUTO + PHONE | 5.1.2 `TAPES 3/3 exact` and 5.1.1 cache fixture; on-device run PHONE |
| AC-5.1-02 | Judge matches | Decisions are identical except within 0.001 of a threshold | AUTO | 5.1.1 judge-golden |
| AC-5.1-03 | Portable | The brain module has no Android dependencies and runs in laptop CI | AUTO (+HUMAN: first green GH run after a push) | build-file grep, `-Pveil.brainOnly` run, workflow |
| AC-5.1-04 | Teacher is fast | A new concept card is ready on the phone in ≤ 1 s | PHONE | instrumented test timing log (laptop `card ms=` informational) |
| AC-5.1-05 | Teacher matches | Phone prompt fingerprints vs Python: cosine ≥ 0.99 per prompt | AUTO (laptop proxy) + PHONE | `TeacherParity`; DEFERRED if R1 hits |
| AC-5.1-06 | Stored safely | The store file is unreadable without the key; settings and corrections survive a restart | AUTO + PHONE | JVM store tests; phone restart + pulled file |
| AC-5.1-07 | Live changes | A list change takes effect in ≤ 1 s, with no restart | AUTO + PHONE | registry test; instrumented test |
| (PLAN 5.1.2-4) | Model parity | fingerprints cosine at least 0.98, decisions at least 99% | DEFERRED | needs phone image-encoder runs (5.2/5.3) |

## 5. Proof test "Same brain on the phone"
- **Machine (now):** `tools/verify/pt-5.1.ps1` (orchestrator) runs 5.1.1, 5.1.2 and 5.1.3 in order and prints `PT 5.1: PASS (laptop)`.
- **Machine (PHONE):** `gradlew :app:connectedDebugAndroidTest` runs `BrainTapeInstrumentedTest` and `TeacherStoreInstrumentedTest`. Pull the reports from `guard/app/build/outputs/androidTest-results/`.
- **Human (PHONE):** type the 5 concepts in `TeacherDebugActivity`, export the cards, and compare them with `teacher-ref.json` (TeacherParity in compare-file mode). Reboot the phone and check that settings and corrections are still there. `adb pull` the store file, try to open it without the key, and take a screenshot of the failure.

## 6. Human items (one HUMAN_CHECKS entry)
- [ ] With the phone connected: run `connectedDebugAndroidTest`. Tapes 3/3, card ≤ 1 s, live swap ≤ 1 s.
- [ ] Debug screen: 5 concepts → export → compare with Workshop cards (cosine ≥ 0.99).
- [ ] Reboot → settings and corrections persist. Pulled store unreadable (screenshot).
- [ ] After the user asks for a push: confirm the `brain-tapes` GitHub Actions run is green.
- [ ] Decide on DEFERRED items: object-finder text encoder (licence), vocabulary lookalikes, bit-exact phash on device.
