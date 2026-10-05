# SPEC 3.3 Runtime on the real phone
MODEL: claude-opus-5-5 · Status: APPROVED (orchestrator; queued after 5.1 because both edit settings.gradle.kts) · Source: PLAN.md 1081-1184 (+ App. D 2183-2200) · Waves: 3.3.1 / 3.3.2 / 3.3.3 all parallel

## 1. Deviations and risks
- R1 **No phone.** AUTO = builds (smoketest APK + androidTest APK) and JVM tests. All timing/memory/soak/restart/parity numbers are PHONE rows: scripts in `tools/phone/3.3/` produce them later (F6/F7: DEFERRED + PENDING-HUMAN). The phase closes on AUTO.
- R2 **fp32 ONNX on HTP.** `data/forge/**` holds fp32 exports; we run them with `enable_htp_fp16_precision=1`. If an op is unsupported, load **fails loudly** (fallback is off, which is wanted). Fix path at the phone sitting: AI Hub QNN context binaries or quantized ONNX from the 3.2 jobs (`budget.json` job ids). Note: `budget.json` says `"source": "fixture"`, so the 45 ms budget is not measured yet.
- R3 **LiteRT has no .tflite models locally**, and the NPU dispatch library may not be in the AAR. The LiteRT wrapper builds and fails loudly without them. The comparison (AC-07) uses whatever the phone sitting gets. ORT+QNN is the default proposal.
- R4 Pins (checked on Maven, ~80 MB total): `com.microsoft.onnxruntime:onnxruntime-android-qnn:1.29.0` (pulls `com.qualcomm.qti:qnn-runtime:2.42.0`), `com.google.ai.edge.litert:litert:2.2.0`. Fixes from #31353 are applied in 3.3.1. If the HTP skel for this chip is missing at runtime, force a newer `qnn-runtime` (2.50.0 exists).
- R5 **Gradle concurrency** (3 Builders + 5.1, 7.4 GB RAM). Every Gradle call is wrapped in the named mutex from §2. There is one Gradle build per verify script.
- R6 The Android wrapper implementations live in `guard/smoketest` (package `com.veil.runtime.ort/litert`) for now. Chapter 5 moves those files unchanged into the Guard app. The interface in `:runtime` is the fixed guarantee. The soak runs without MediaProjection, because capture is out of scope (Ch4); `scrcpy --record` is optional evidence.

## 2. Shared interfaces (verbatim; 3.3.2 writes `Api.kt` + settings lines FIRST, within 2 min)
`guard/settings.gradle.kts`: add after the teacher line, only by 3.3.2:
`if (file("runtime/build.gradle.kts").exists()) include(":runtime")` and `if (file("soak/build.gradle.kts").exists()) include(":soak")`. Inside the `!brainOnly` block: `if (file("smoketest/build.gradle.kts").exists()) include(":smoketest")`.
Gradle mutex (every verify/Builder Gradle call): `$m=New-Object System.Threading.Mutex($false,'Global\veil-gradle'); [void]$m.WaitOne(); try { .\gradlew.bat --no-daemon ... } finally { $m.ReleaseMutex() }`
```kotlin
package com.veil.runtime   // guard/runtime/src/main/kotlin/com/veil/runtime/Api.kt  (FROZEN for Chapter 5)
sealed interface Tensor { val shape: LongArray }
class FloatTensor(override val shape: LongArray, val data: FloatArray) : Tensor
class LongTensor(override val shape: LongArray, val data: LongArray) : Tensor
data class IoSpec(val name: String, val shape: LongArray, val dtype: String) // "float32" | "int64"
data class ModelSpec(val id: String, val path: String, val inputs: List<IoSpec>, val outputs: List<IoSpec>)
enum class Backend { NPU, CPU }
class LoadedModel(val spec: ModelSpec, val backend: Backend, val loadMs: Double, val fromCache: Boolean, val handle: Any)
class RuntimeFailure(message: String, cause: Throwable? = null) : RuntimeException(message, cause)
interface ModelRuntime : AutoCloseable {
    val name: String                                   // "ort-qnn" | "litert-npu"
    fun load(spec: ModelSpec, config: RuntimeConfig = RuntimeConfig()): LoadedModel  // throws RuntimeFailure
    fun run(model: LoadedModel, inputs: Map<String, Tensor>): Map<String, Tensor>     // throws RuntimeFailure
    fun release(model: LoadedModel)
}
enum class PerfMode(val qnn: String) { BURST("burst"), LOW_POWER("low_power_saver"), DEFAULT("default") }
data class RuntimeConfig(val allowCpuFallback: Boolean = false, val runPerfMode: PerfMode = PerfMode.BURST,
    val idlePerfMode: PerfMode = PerfMode.LOW_POWER, val fp16: Boolean = true, val cacheDir: String? = null, val profileDir: String? = null) {
    fun cachePath(id: String): String?                     // "$cacheDir/${id}_ctx.onnx" or null
    fun ortSessionEntries(id: String, cacheExists: Boolean): Map<String, String> // session.disable_cpu_ep_fallback=1 unless allowed; ep.context_enable=1, ep.context_embed_mode=1, ep.context_file_path=cachePath when cacheDir set && !cacheExists
    fun qnnProviderOptions(nativeLibDir: String): Map<String, String> // backend_path=$dir/libQnnHtp.so, htp_performance_mode=runPerfMode.qnn, enable_htp_fp16_precision=1|0, htp_graph_finalization_optimization_mode=3
    fun ortRunEntries(): Map<String, String>               // qnn.htp_perf_mode=run, qnn.htp_perf_mode_post_run=idle
}
```
Also in `:runtime` (3.3.2): `data class Latency(n,p50,p95,max,mean)` + `fun latencyOf(ms: DoubleArray): Latency` (nearest rank: `sorted[ceil(p*n)-1]`); `object ProfileCheck { fun providerCounts(ortProfileJson: String): Map<String,Int>; fun allOnNpu(json): Boolean }` (counts `"cat":"Node"` events by `args.provider`; true iff only `QNNExecutionProvider`); `class SerialWorker : AutoCloseable { fun <T> call(block: () -> T): T }` (one thread "veil-ai"); `class ResidentModels(rt, specs, cfg, warmups = 2, inputs: (ModelSpec) -> Map<String,Tensor>) : AutoCloseable { fun start(): Long /*readyMs*/; fun run(id: String, inputs: Map<String,Tensor>): Map<String,Tensor> }` (all calls through SerialWorker); `object ImagePrep { fun nchw(argb: IntArray, w: Int, h: Int, scale: Float, mean: FloatArray, std: FloatArray): FloatArray }`.
Phone file formats (device dir `/sdcard/Android/media/com.veil.smoketest/`, models in `models/`, frames in `screens/`, outputs in `out/`):
`timing.csv` = `runtime,model,phase,i,ms` (phase cold|warm|idle-first; model `look` = one full Balanced look). `soak.csv` = `tMs,lookMs,ok,pssKb,thermal,headroom`. `fp.csv` = `image,v0..v767` (siglip2-image-b1 fingerprint). `models.txt` = `id|file.onnx|manifest.json`. Logcat tag `VEIL`: `VEIL_READY ms=<n> cache=<bool>`.
Balanced look = nudenet-320n, yoloe-26s-embed-top100, siglip2-image-b4, toxicity-seq128 (from `budget.json`), run in sequence on the SerialWorker; text inputs are fixed dummy ids.

## 3. Sub-phases
### 3.3.1 Runtime smoke test (Android app + wrappers)
Goal: the smoketest APK and its test APK build with ORT-QNN (fallback off) and LiteRT-NPU wrappers. Owned: `guard/smoketest/**`, `tools/verify/3.3.1.ps1`.
Files: `build.gradle.kts` (app `com.veil.smoketest`, minSdk 31, compile/target 36, `abiFilters += "arm64-v8a"`, `packaging { jniLibs { useLegacyPackaging = true } }`, deps `project(":runtime")`, ORT-QNN + LiteRT pins (R4), androidx.test runner/junit). `AndroidManifest.xml` (`android:extractNativeLibs="true"`, `<uses-native-library android:name="libcdsprpc.so" android:required="false"/>`, also `libOpenCL.so` optional). `ort/OrtQnnRuntime.kt`, `litert/LiteRtRuntime.kt`, `Manifests.kt` (org.json manifest to ModelSpec), `Frames.kt` (Bitmap stretch to ImagePrep), `MainActivity.kt` (mode `ready`: ResidentModels.start, log VEIL_READY; mode `pt`: 50 screens, show per-look ms + p50/p95 + cosine vs `laptop-fp.csv` on screen, write out/), androidTest `BenchTest`, `ResidentTest`, `SoakTest` (args via `-e`: runtime, model, n, minutes, rate).
Steps: 1) In OrtQnnRuntime.load: `Os.setenv("ADSP_LIBRARY_PATH", nativeLibraryDir, true)` before the first OrtEnvironment. Apply ortSessionEntries via addConfigEntry and `addQnn(qnnProviderOptions)`. If the cache exists, load the `_ctx.onnx`. Enable profiling when profileDir is set. Use `RunOptions` + ortRunEntries. Wrap every exception in RuntimeFailure, so nothing fails silently. 2) LiteRtRuntime: `CompiledModel` with **only** `Accelerator.NPU` (check the API in the Gradle cache AAR). Throw RuntimeFailure if the .tflite or the dispatch lib is missing (R3). 3) BenchTest: n runs → timing.csv plus the profile, then assert `ProfileCheck.allOnNpu`. ResidentTest: all models, 2 warm-ups, 1000 runs each, idle 30 s then the first run, 1000 looks on real frames in burst vs low-power, `Debug.getPss()`. SoakTest: minutes × 3 looks/s → soak.csv with `PowerManager.currentThermalStatus` and `getThermalHeadroom(10)`.
Verify `3.3.1.ps1` (one Gradle call): `:smoketest:assembleDebug :smoketest:assembleDebugAndroidTest`. Then: the APK zip lists `lib/arm64-v8a/libonnxruntime.so`, `libQnnHtp.so`, ≥1 `libQnnHtp*Skel.so` (print them); the manifest has `libcdsprpc.so`; grep shows `disable_cpu_ep_fallback` is never set to `0` in `src/`; ktlint `guard/smoketest/src/**/*.kt`. < 5 min after first download. Ends `VERIFY 3.3.1: PASS`.

### 3.3.2 Runtime wrapper (JVM) for residency and timing
Goal: the frozen interface, config, stats, residency and worker, unit-tested on the JVM. Owned: `guard/runtime/**`, the 3 include lines in `guard/settings.gradle.kts`, `tools/verify/3.3.2.ps1`.
Files: `build.gradle.kts` (`org.jetbrains.kotlin.jvm`, jvmToolchain 17, junit, test maxHeap 512m, **no android/onnxruntime deps**). `Api.kt` (§2), `Config.kt`, `Latency.kt`, `ProfileCheck.kt`, `Resident.kt`, `ImagePrep.kt`. Tests `com.veil.runtime.unit.*` with a `FakeRuntime`.
Tests (one each): default config has `session.disable_cpu_ep_fallback=1` and no CPU option; `allowCpuFallback=true` drops the key; cache path/entries switch when cacheExists; run entries burst/low_power_saver; latencyOf on 1..100 gives p50=50, p95=95; ProfileCheck on 2 small JSON fixtures (QNN-only true, mixed CPU false); ResidentModels loads all, runs warm-ups ×2, all runs on a single thread "veil-ai", release on close, a load failure propagates as RuntimeFailure; ImagePrep on a 2×1 image gives the expected values.
Verify `3.3.2.ps1`: `-Pveil.brainOnly=true :runtime:test`; ktlint `guard/runtime/src/**/*.kt`; the build file has no `com.android|onnxruntime`. Ends `VERIFY 3.3.2: PASS`.

### 3.3.3 Soak analysis, phone scripts and decision draft
Goal: log analysers (JVM) plus the PHONE scripts that produce all AC evidence in one sitting. Owned: `guard/soak/**`, `tools/phone/3.3/**`, `workshop/forge/phone/**`, `docs/reports/ch3-speed.md`, `tools/verify/3.3.3.ps1`, one appended entry in `docs/decisions.md`.
Files: `:soak` (JVM, standalone, own nearest-rank percentile): `SoakAnalyzer.analyze(rows, warmupMs = 60_000): SoakResult(looks, errors, growthPct, firstMinP95, lastMinP95, driftPct, maxThermal, pass)`. Growth = median PSS of the last 60 s vs the first 60 s after warm-up. Drift = last-minute p95 vs first-minute p95. pass = errors==0 && growth≤5 && drift≤20 && looks ≥ 0.95·3·seconds. `TimingReport` (timing.csv to a markdown p50/p95 table, gate line `look p95 ≤ 45 ms`). `FpParity` (min cosine of fp.csv vs laptop-fp.csv, ≥ 0.98). Mains `SoakCheckKt`/`TimingReportKt`/`FpParityKt` print `SOAK|TIMING|PARITY: PASS|FAIL` with exit 0/1, plus JavaExec tasks `soakCheck`/`timingReport`/`fpParity` (`-Pin=…`). `workshop/forge/phone/laptop_ref.py`: first 50 sorted PNGs of `data/public/set` → `data/ch3/phone/screens/` + `laptop-fp.csv` via onnxruntime CPU on `siglip2-image-b1.onnx` (manifest preprocessing; reuse `workshop/forge/siglip2/runtime.py` if it fits), `--limit N`.
Phone scripts (`tools/phone/3.3/`, all use `common.ps1`: adb from toolchain, exit 2 `NO PHONE` when no device, `-DryRun` prints the adb commands, evidence to `data/ch3/phone/<stamp>/`): `install.ps1` (adb install -r -t both APKs, push models + manifests + models.txt + screens + laptop-fp.csv), `bench.ps1 -Runtime ort-qnn|litert-npu -Model -N 100|1000`, `resident.ps1` (ResidentTest + `dumpsys meminfo com.veil.smoketest` TOTAL PSS), `soak.ps1 -Minutes 10 -Rate 3` (runs in the background; host samples `dumpsys thermalservice` + meminfo every 10 s), `restart.ps1` (force-stop, `am start -W … --es mode ready`, read VEIL_READY), `pt.ps1` (install → pt mode → soak → restart → all three checks; optional scrcpy record). Output is pulled with `adb exec-out run-as com.veil.smoketest` or from the media dir.
Draft `ch3-speed.md` (tables marked PENDING-PHONE) and a `decisions.md` entry "D-3.3 runtime: ORT+QNN proposed, PENDING phone comparison".
Verify `3.3.3.ps1`: Gradle `-Pveil.brainOnly=true :soak:test` (fixtures pass / growth 6% / drift 25% / 1 error / short soak); ktlint `guard/soak/src/**/*.kt`; `ruff check`+`format --check` on `workshop/forge/phone`; `laptop_ref.py --limit 2` writes 2 rows of 768; every `tools/phone/3.3/*.ps1` parses with no errors (PS Parser); `bench.ps1 -DryRun` exits 0 and prints `am instrument`. Ends `VERIFY 3.3.3: PASS`.

## 4. Acceptance (includes the Chapter 3 gate)
| ID | Pass threshold (PLAN, word for word) | AUTO now | PHONE (script) |
| --- | --- | --- | --- |
| AC-3.3-01 | Fallback to the main processor is disabled, and every model still loads and runs on the AI chip | config unit test + grep (3.3.1/2) | bench.ps1 + ProfileCheck |
| AC-3.3-02 | One full Balanced look, p95 ≤ 45 ms on the phone with real frames | TimingReport fixture | resident.ps1 |
| AC-3.3-03 | With all models loaded, app memory (PSS) ≤ 3 GB | n/a | resident.ps1 (`dumpsys meminfo`) |
| AC-3.3-04 | 10-minute soak at 3 looks/s: 0 errors; memory growth ≤ 5% after warm-up; last-minute p95 within 20% of first-minute p95 | SoakAnalyzer fixtures | soak.ps1 (DEFERRED, F6) |
| AC-3.3-05 | All models ready ≤ 5 s after a restart, with the compiled cache present | n/a | restart.ps1 |
| AC-3.3-06 | Phone vs laptop-float fingerprints: cosine ≥ 0.98 | laptop_ref + FpParity fixture | pt.ps1 |
| AC-3.3-07 | ONNX Runtime vs LiteRT comparison and the choice recorded | draft entry | human after bench both |
Smoke "Done when": runs on the AI chip in under 10 ms with no fallback, in at least one runtime (`bench.ps1 -Model siglip2-image-b1 -N 100`). Gate: if rejected, apply the Chapter 3 fallback: switch to LiteRT, then smaller models, then drop the object finder. Re-run all criteria after each step.

## 5. Proof test PT-3.3 "AI in your hand" (PENDING-HUMAN)
`tools/phone/3.3/pt.ps1`: 50 on-phone screenshots → covers/timings on screen, cosine ≥ 0.98 vs laptop. Then a 10-min hand-held soak at 3 looks/s (SOAK: PASS, thermal logged), then reopen with VEIL_READY ≤ 5000 ms. Evidence: scrcpy recording, timing.csv, soak.csv, host thermal/meminfo csv under `data/ch3/phone/<stamp>/`.

## 6. Human checklist
1. Connect the iQOO (USB debugging, stay awake on) and run `tools/phone/3.3/pt.ps1`. 2. If QNN load fails (R2), approve AI Hub context-binary downloads. 3. Supply LiteRT .tflite + NPU dispatch lib, then run `bench.ps1 -Runtime litert-npu`. 4. Hold the phone for 10 min and report comfort. 5. Approve the D-3.3 runtime decision.
