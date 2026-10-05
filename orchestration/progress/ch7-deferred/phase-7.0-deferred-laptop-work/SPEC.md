# SPEC 7.0 Deferred laptop work
MODEL: claude-opus-5-5 · Status: DRAFT for orchestrator · Inputs: DEFERRED.md, 5.2 SPEC-W §1 R-6, 6.3 SPEC D2/D3, 3.1.3 record, 5.1 PHASE notes · Entry: HEAD 7266ef6; phone NOT connected.
Goal: close the three deferred laptop items that most change the demo: toxicity on the text lane (D-5.2W-tox), Guard crash recovery with "Resume Veil" (D-6.3-guard), and a concept hot-swap without a restart (D-5.2W-teacher).

## 1. Choice and risks
| Item | Decision | Why |
| --- | --- | --- |
| D-5.2W-tox | **7.0.1** | TextLane runs with `tox = null` today; unblocks the toxic-text part of HC-018 and the 5.1 Teacher tokenizer (same Gemma BPE). |
| D-6.3-guard | **7.0.2** | AC-6.3-02 real-Guard part. Also fixes a real crash: `postNotification()` always calls `startForeground(..., TYPE_MEDIA_PROJECTION)`, which throws `SecurityException` on API 34+ when there is no live projection (sticky restart with a null intent, or a command before consent). |
| D-5.2W-teacher | **7.0.3** | `concepts` today = `GuardCore.rebuild()` + a new `ModelStore`: all ORT sessions reopen (~1.6 GB) and the brain pipeline resets. AC-5.1-07 wants changes live in ≤ 1 s. |
| D-5.2W-finder | TODO | RegionLane judges FINDER pieces only against `concepts.finder`, which is always empty (YOLOE text encoder BLOCKED in 3.1; `ConceptPack` sets finder = empty). Wiring it now costs a 640² run per look and adds no findings. Prerequisite: compile finder-space concepts on the laptop and split `ConceptPack` by spaceId. |
| D-6.3-blind | TODO | Lower demo value; next batch (about 20 min). |
| D-6.1-apk | TODO (orchestrator run) | This is a command, not build work. Run it alone after 7.0 (F12: one Gradle/Flutter at a time). |
- **R-1 Tokenizer exactness.** Both tokenizer.json files are Gemma BPE: `byte_fallback=true`, `fuse_unk=true`, `ignore_merges=false`, normalizer `Replace(" " → "▁")`. Toxicity: pre-tokenizer `Metaspace(prepend_scheme=always, split=true)`, template `<bos>(2) A <eos>(1)`. SigLIP2: `Split(" ")` (a no-op after the normalizer), template `A <eos>`. Kotlin must match HF `tokenizers` on a golden set. The golden set comes from Python, never hand-made.
- **R-2 Score.** The config says `problem_type = multi_label_classification`, with id2label[0] = `toxicity`. The app uses `sigmoid(logits[0])`, not the softmax that `parity.py` used (AUC is not re-measured here; see §4). The ONNX `toxicity-seq128.onnx` has `input_ids` and `attention_mask` (1,128) int64 and outputs `logits` (1,7). Ids are truncated to 128 like `pad_truncate` (so the eos may be cut), padded with id 0, mask 1/0.
- **R-3 RAM.** The laptop has 7.4 GB. No verify loads a model. The tokenizer pack is about 10 MB (fine in a Gradle test JVM). The 34 MB `tokenizer.json` is parsed only by Python.
- **R-4 Parallel compile.** 7.0.3 compiles against 7.0.1's `OrtToxicity`. **Wave 0:** in its first 3 minutes 7.0.1 writes `GemmaBpe.kt`, `ToxPrep.kt` and `OrtToxicity.kt` with the §2 signatures and `TODO()` bodies. The orchestrator runs 7.0.3's verify last.

## 2. Shared interfaces (exact)
Pure, in `guard/conductor/src/main/kotlin/com/veil/conductor/text/` (7.0.1):
```kotlin
class GemmaBpe(val prependMeta: Boolean, val splitMeta: Boolean, val bosId: Int, val eosId: Int, val unkId: Int, val padId: Int,
               private val vocab: Array<String>, private val merges: IntArray /* triples l,r,merged; rank = index/3 */,
               private val added: List<Pair<String, Int>>) {
    fun encode(text: String): IntArray            // with bos/eos per template, no truncation
    companion object { fun load(f: java.io.File): GemmaBpe }   // reads the VBPE pack (below)
}
object ToxPrep {
    fun inputs(ids: IntArray, len: Int, pad: Int): Pair<LongArray, LongArray>   // (input_ids, attention_mask)
    fun score(logits: FloatArray): Double                                        // sigmoid(logits[0])
}
```
App, `guard/app/src/main/java/com/veil/guard/wire/ml/OrtToxicity.kt` (7.0.1):
`object OrtToxicity { fun open(store: ModelStore): com.veil.conductor.TextClassifier? }` returns null, without logging, if `toxicity-seq128.onnx` or `toxicity-tok.bin` is missing in `store.dir`. 7.0.3 keeps `ModelStore.env`, `.dir`, `.has(name)` and `.session(name)` unchanged.
**VBPE pack** (big-endian, Python `struct ">"` = Java `DataInputStream`): `"VBPE"`, int version=1; ints prependMeta, splitMeta, bosId (-1 = none), eosId (-1 = none), unkId, padId; int nVocab, then for each id 0..n-1 a u16 length + UTF-8 bytes (the packer asserts ids are dense); int nMerges, then a triple (leftId, rightId, mergedId) each, in rank order (merges may be `[a,b]` arrays or `"a b"` strings; merged = vocab[a+b]); int nAdded, then (int id, u16 length, UTF-8) each (the packer drops and counts any with lstrip/rstrip/single_word = true).
**encode** = (1) split the raw text on added-token literals (leftmost, longest) into id segments; (2) other segments: replace `' '` with `"▁"`; if prependMeta and the segment does not start with `▁`, prepend `▁`; if splitMeta, split before every `▁` (MergedWithNext); (3) BPE each piece: code points → vocab ids, unknown code point → its UTF-8 bytes as `<0xXX>` (uppercase hex) ids, else unk, with consecutive unks fused; then repeatedly merge the adjacent pair with the lowest rank (leftmost on ties); (4) add bos/eos. For empty-string and edge cases, follow the golden set.

## 3. Sub-phases (parallel after Wave 0)
### 7.0.1 Toxicity on the phone (Gemma BPE tokenizer + ORT classifier)
**Owned:** `workshop/forge/toxicity/tokpack.py`; `guard/conductor/src/main/kotlin/com/veil/conductor/text/{GemmaBpe,ToxPrep}.kt`; `guard/conductor/src/test/kotlin/com/veil/conductor/text/{GemmaBpeTest,ToxPrepTest}.kt`; `guard/conductor/src/test/resources/tok/{golden-toxicity,golden-siglip2}.json`; `guard/app/src/main/java/com/veil/guard/wire/ml/OrtToxicity.kt`; `tools/verify/7.0.1.ps1`.
Steps:
1. `tokpack.py` (`uv run python -m workshop.forge.toxicity.tokpack [--golden|--check-golden]`) finds the tokenizer through `HF_HOME` (tools/env.ps1) snapshot `models--Horizon-Labs--multilingual-toxicity-small/snapshots/3baf7739…/tokenizer.json`. It writes `data/forge/toxicity/toxicity-tok.bin` (prepend=1, split=1, bos=2, eos=1) and, from `data/forge/siglip2/tokenizer.json`, `data/forge/siglip2/siglip2-tok.bin` (prepend=0, split=0, bos=-1, eos=1). It reads the flags from each JSON and asserts they equal these. It prints the vocab/merges/added counts and the dropped added-token count.
2. Golden: a fixed list of about 25 harmless strings: English sentence; mixed case; digits and punctuation; double, leading and trailing spaces; `\n` and `\t`; accented Latin; Hindi; Chinese; Arabic; emoji (including a ZWJ sequence); a URL; a 400-character string; `""`. Ids come from `tokenizers.Tokenizer.from_file(...).encode(s).ids` (add_special_tokens default). `--golden` writes `{"strings":[...],"ids":[[...]]}` per tokenizer; `--check-golden` re-encodes and exits 1 on any difference. No toxic or sample text is ever used or printed.
3. `GemmaBpe` per §2 (merges in a `HashMap<Long, Int>` keyed `l shl 32 or r` → rank index; naive lowest-rank loop). `GemmaBpeTest` loads `File("../../data/forge/toxicity/toxicity-tok.bin")` (the test working dir is `guard/conductor`) and the siglip2 pack. It **fails** if either is missing. It asserts exact ids for every golden string of both. `ToxPrepTest`: padding, truncation at 128, mask, and `score(floatArrayOf(0f, …)) == 0.5`.
4. `OrtToxicity.open`: loads the pack once (cached by file `lastModified`) plus `store.session("toxicity-seq128.onnx")`. The classifier: `ids = bpe.encode(text)`, `ToxPrep.inputs(ids, 128, bpe.padId)`, then `OnnxTensor.createTensor(env, LongBuffer.wrap(x), longArrayOf(1,128))` for both inputs, then run, then `ToxPrep.score(logits[0])`. Close tensors and the result with `use`. Exceptions → log one `{"kind":"warn","what":"tox-error"}` via `WireHub.log`, return 0.0.
**Verify `7.0.1.ps1`:** ktlint the owned .kt (Check helper as in 5.2-W.1.ps1); `uv run --locked ruff check workshop/forge/toxicity/tokpack.py`; `uv run python -m workshop.forge.toxicity.tokpack --check-golden` (also writes both .bin files); both .bin files exist; `:conductor:test --tests "com.veil.conductor.text.GemmaBpeTest" --tests "com.veil.conductor.text.ToxPrepTest"`; `:app:compileDebugKotlin` → `VERIFY 7.0.1: PASS`.

### 7.0.2 Guard crash recovery and "Resume Veil"
**Owned:** `guard/app/src/main/java/com/veil/guard/capture/service/{CaptureService,CaptureNotifications,RecoveryPolicy}.kt`, `capture/state/CaptureStateMachine.kt`, `guard/app/src/main/AndroidManifest.xml` (CaptureService entry + one permission), `res/values/capture_strings.xml`, `app/src/test/java/com/veil/guard/capture/service/{RecoveryPolicyTest,GuardRecoveryLoopTest}.kt`, `capture/state/CaptureStateMachineTest.kt` (add a case), `tools/verify/7.0.2.ps1`.
Interface (pure, no `android.*`):
```kotlin
enum class FgsKind { PROJECTION, WAITING }
data class StartDecision(val fgs: FgsKind, val event: CaptureEvent?, val stopSelf: Boolean)
object RecoveryPolicy {
    fun onStart(action: String?, consentOk: Boolean, hasProjection: Boolean, wasRunning: Boolean): StartDecision
    fun wasRunning(s: CaptureState): Boolean   // RUNNING, PAUSED, AWAITING_PERMISSION -> true; STOPPED -> false
}
```
Steps:
1. Rules: consent result OK, or `hasProjection` → PROJECTION. `action == null` (sticky restart) with wasRunning → WAITING + `CaptureEvent.Restarted`; without wasRunning → WAITING + `stopSelf=true`. Anything else → WAITING, no event.
2. `CaptureStateMachine`: add `object Restarted : CaptureEvent()`: STOPPED → AWAITING_PERMISSION with reason `"restarted"`; other states → null.
3. `CaptureService.onStartCommand`: read `wasRunning` from prefs `veil.capture`, decide, call `postNotification(kind)` **before** `getMediaProjection`, then handle the event or call `stopSelf()`. On API ≥ 34, the type is `FOREGROUND_SERVICE_TYPE_MEDIA_PROJECTION` for PROJECTION and `FOREGROUND_SERVICE_TYPE_SPECIAL_USE` for WAITING. Later posts use `if (projection != null) PROJECTION else WAITING`. In `projectionCallback.onStop`, set `projection = null` first. In `handleEvent`, persist `RecoveryPolicy.wasRunning(t.state)`.
4. Manifest: `foregroundServiceType="mediaProjection|specialUse"`, plus `<property android:name="android.app.PROPERTY_SPECIAL_USE_FGS_SUBTYPE" android:value="Waiting for screen-capture consent to resume on-device covering"/>` and the permission `FOREGROUND_SERVICE_SPECIAL_USE`.
5. `CaptureNotifications.build(ctx, text, awaitingPermission, reason: String? = null)`: when awaiting, the content intent also opens ConsentActivity. Content text: `"restarted"` → "Veil stopped unexpectedly. Tap Resume Veil."; `"keyguard"` → "Paused while locked. Tap Resume Veil." (new strings in capture_strings.xml).
6. `GuardRecoveryLoopTest` (pure) loops 5 times each: **crash** (RUNNING, persisted true → new state machine → `onStart(null, …)` → Restarted → AWAITING_PERMISSION → ConsentGranted → RUNNING); **lock** (KeyguardLocked → AWAITING_PERMISSION → ConsentGranted → RUNNING); **kill** (UserStop → STOPPED, wasRunning false → `onStart(null, …)` has stopSelf → a fresh ConsentGranted → RUNNING). It prints `RECOVERY-GUARD crash=5/5 lock=5/5 kill=5/5`. `RecoveryPolicyTest` covers every rule in step 1.
**Verify `7.0.2.ps1`:** ktlint the owned .kt; `:app:testDebugUnitTest --tests "com.veil.guard.capture.service.*" --tests "com.veil.guard.capture.state.CaptureStateMachineTest"`; `Select-String` on `app/build/test-results/testDebugUnitTest/TEST-com.veil.guard.capture.service.GuardRecoveryLoopTest.xml` for `RECOVERY-GUARD crash=5/5 lock=5/5 kill=5/5`; `Select-String` on CaptureService for `FOREGROUND_SERVICE_TYPE_SPECIAL_USE` and `RecoveryPolicy.onStart`; `:app:processDebugMainManifest` → `VERIFY 7.0.2: PASS`.

### 7.0.3 Concept hot-swap without a restart
**Owned:** `guard/app/src/main/java/com/veil/guard/wire/{GuardCore,GuardRuntime}.kt`, `wire/ml/{LiveLanes,ModelStore,ConceptWatcher}.kt`, `teacher/TeacherDebugActivity.kt`, `app/src/test/java/com/veil/guard/wire/LaneSwapTest.kt`, `tools/verify/7.0.3.ps1`.
Steps:
1. `ModelStore`: a process-wide session cache (companion, `@Synchronized`) keyed by name, storing a `lastModified xor length` stamp. Reopen only if the stamp changed (close the old one); keep a single `OrtEnvironment`. Keep the §2 members.
2. `LiveLanes.build`: one object-level `FingerprintCache` (it survives rebuilds; fingerprints do not depend on concepts). `TextLane(concepts, OrtToxicity.open(store), MlKitOcr(), counters)`; null → `off("toxicity", "toxicity-seq128.onnx or toxicity-tok.bin missing")`, and the lane still runs with keywords.
3. `GuardCore`: add `class SwapLane : Lane { @Volatile var current: List<Lane>; run = current.flatMap { it.run(input) } }`. The Conductor gets `listOf(swap, sentinel)`; `build()` sets `swap.current = lanes(counters)` and keeps `counters` in a field. New `fun swapLanes()` does `swap.current = lanes(counters)` (same Conductor, no pipeline reset). Expose `val buildCount: Int` (counts `build()` calls). `rebuild()` (mode/skip) is unchanged.
4. `GuardRuntime.reloadLanes()` → `run { it.swapLanes() }`, then log `{"kind":"concepts","tMs":uptime,"lanes":n}`. In `start()`: `mkdirs` the `<media>/concepts`, then `ConceptWatcher(dir) { handler.removeCallbacks(r); handler.postDelayed(r, 150) }.start()` where `r` = reloadLanes. In `stop()`: stop it.
5. `ConceptWatcher(dir: File, onChange: () -> Unit)` wraps `FileObserver(dir, CLOSE_WRITE or MOVED_TO or DELETE or MOVED_FROM)` and acts only on `*.json`; it has `start()` and `stop()`.
6. `TeacherDebugActivity`: after its existing write, it also writes the card JSON only (no sha line) to `<media>/concepts/<conceptId>.json.tmp`, then `renameTo` the final name, so the watcher swaps it in.
7. `LaneSwapTest` (fakes in the style of GuardCoreWiringTest, real `src/main/assets/params.json`): the factory returns a no-finding lane, so there is no plan with masks. Flip it to a one-finding lane and call `swapLanes()`; the next changed frame gives a plan with ≥ 1 mask. `buildCount` is unchanged by `swapLanes()` and rises by 1 after `setMode("strict")`. The factory is called once per swap.
**Verify `7.0.3.ps1`:** ktlint the owned .kt; `:app:testDebugUnitTest --tests "com.veil.guard.wire.LaneSwapTest" --tests "com.veil.guard.wire.GuardCoreWiringTest"`; `Select-String` on LiveLanes for `OrtToxicity.open(` and on GuardRuntime for `ConceptWatcher(` and `swapLanes()`; `:app:assembleDebug` (after 7.0.1 is done) → `VERIFY 7.0.3: PASS`.

## 4. Human follow-ups (PENDING-HUMAN, batch into one HC)
1. Push `data/forge/toxicity/toxicity-seq128.onnx` and `toxicity-tok.bin` to `/sdcard/Android/media/com.veil.guard/models/`. `debug.jsonl` has no `lane-off toxicity`. A mildly rude, non-explicit Test Feed caption gets `text.toxic` at strict; a neutral caption does not.
2. Crash recovery: 5 times `adb shell am crash com.veil.guard` (or `kill`): the "Resume Veil" notification appears and one tap brings back running. Lock 5/5, stop 5/5. Log the results in `docs/release/edge-cases.md` (AC-6.3-02 phone part).
3. Hot-swap: push a compiled concept JSON into `.../concepts/`. The `concepts` log line appears ≤ 1 s after the file write, covers follow without a restart, and no `look` gap appears (AC-5.1-07).
4. New deferred row (orchestrator): **D-7.0-auc**, re-run the toxicity AUC with sigmoid(logit 0) (heavy, 563 MB model). Run D-6.1-apk alone after this phase. D-5.2W-finder and D-6.3-blind stay TODO for the reasons in §1.
