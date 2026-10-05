# SPEC · Phase 6.2 Learning and packs
MODEL: claude-opus-5-5
Status: APPROVED (orchestrator; 6.2.2 now, 6.2.1+6.2.3 after the 4.1 Gradle work since they load SigLIP2)
Based on: PLAN.md Phase 6.2 (lines 1934-2036) · ORCHESTRATOR.md section 0 (F1-F12) and 10 · repo read: guard/brain (Judge, contract/Types), guard/teacher (Teacher, SecureStore, Api), console/lib/guard, contracts (feedback, concept, concept-pack, model-manifest), workshop/twin (teacher, judge, run, calibrate, describer), workshop/eval, data/public

## 1. Deviations and risks
- D1 Phone parts (live long-press, PCAPdroid, scrcpy, Wireshark) are PENDING-HUMAN. AC-6.2-01 and -03 are proved on the laptop now (twin plus JVM test; correction code has no network import) and confirmed on the phone later.
- D2 The "app" side of AC-6.2-06 is checked by `workshop/api/client.py` (signature, sha256, schema) plus the existing Guard contract `setConceptPack` ("checksum/schema check; on reject the old pack stays"). No Dart or Flutter changes in this phase, so the Flutter build does not compete with Gradle (F12).
- D3 Signatures are Ed25519 via `cryptography` (6.2.2 runs `uv add cryptography`). The dev key is created on first run under `workshop/api/keys/`, which is git-ignored.
- D4 Gore and Needles: text only, meaning keyword rules and written prompts. No gore or needle images are ever fetched, generated or viewed. Their AC-6.2-07 image rows are PENDING-HUMAN (controlled set). Their keyword rules are scored on a hand-written harmless text set. The spoiler pack is treated the same way.
- D5 Spiders are scored on `data/public/photos` (8 spider, 42 clean). Alcohol gets at most 24 harmless drink and bottle photos via the `public_set.py` approach (HF datasets-server, licence recorded). If no licensed set turns up within 5 min, mark it PENDING-HUMAN. A pack that misses the threshold ships with `"catalogue": false` (PLAN "If rejected").
- D6 The fox is only covered as a cat in some modes and concepts. The fox test first asserts that at least one fox photo is `hide` under the chosen mode, trying `strict` and then the loose cat card (looksLike adds "a small furry animal with pointed ears"). If neither covers a fox, the precondition fails loudly; do not fake it.

## 2. Shared interfaces (fixed now; all three sub-phases code against these)
- Constants: `MAX_EXCEPTIONS=64` (oldest dropped), `STEP=0.02`, `CAP=0.15`, `EXCEPTION_SIM=0.92` (cosine; at or above this to any exception of the concept means `leave`).
- Threshold nudge = `-userOffset`: "notThis" → `nudge=min(nudge+STEP, CAP)`; "missed" → `nudge=max(nudge-STEP, -CAP)`. The book applies it by returning `cc.copy(userOffset = -nudge)`, so Judge is unchanged.
- Layer 1: `record()` rejects `layer != 2` (feedback schema const). `adjust()` and `filter()` return their input unchanged for any concept with `layer == 1`, or whose id is in `LAYER1_IDS = {"nsfw", "nudity"}`.
- Kotlin `:brain` `com.veil.brain.learn.CorrectionBook`:
  `fun record(fb: Feedback, vec: DoubleArray?)` · `fun adjust(cc: CompiledConcept, layer: Int = 2): CompiledConcept` · `fun filter(conceptId: String, vec: DoubleArray, v: Verdict, layer: Int = 2): Verdict` · `fun toJson(): JsonObject` / `fromJson(...)` (state shape: `{"concepts": {id: {"nudge": d, "exceptions": [b64 f16, ...]}}}`).
- Kotlin `:teacher` `com.veil.teacher.CorrectionStore(store: SecureStore)`: `load(): CorrectionBook`, `save(book)`. Writes the book under the existing `"corrections"` key, so it is AES-GCM encrypted at rest.
- Python mirror `workshop/twin/corrections.py`: `CorrectionBook.record(fb: dict, vec)`, `.adjust(cc: dict, layer=2) -> dict`, `.filter(concept_id, vec, verdict: dict, layer=2) -> dict`, `.to_json()`. The same constants and behaviour as the Kotlin version.
- Pack files: `workshop/packs/<packId>.json` are ConceptPacks (contract 1.0). Each concept has `looksLike`, `butNot`, `keywords`, and `sensitive` where it applies. Eval reports go in `workshop/packs/reports/<packId>.json`, shaped `{recall, cleanFalseCoverRate, testImages, testSet, status: "PASS"|"FAIL"|"PENDING-HUMAN", textRecall?, textFalseRate?}`. 6.2.2 reads only these two globs. Until 6.2.3 lands, its tests use fixtures in `workshop/api/tests/fixtures/`.

## 3. Sub-phases (Wave 1: 6.2.1 ∥ 6.2.2 ∥ 6.2.3; phone: none)

### 6.2.1 Corrections (Kotlin + twin; the only sub-phase that runs Gradle)
Goal: the correction loop logic, encrypted storage, and the fox scenario.
Owned: `guard/brain/src/main/kotlin/com/veil/brain/learn/`, `guard/brain/src/test/kotlin/com/veil/brain/learn/`, `guard/brain/src/test/resources/corrections/`, `guard/teacher/src/main/kotlin/com/veil/teacher/CorrectionStore.kt`, `guard/teacher/src/test/kotlin/com/veil/teacher/CorrectionStoreTest.kt`, `workshop/twin/corrections.py`, `workshop/twin/fox_scenario.py`, `workshop/twin/tests/test_corrections.py`, `tools/verify/6.2.1.ps1`.
Steps:
1. Write `corrections.py` to the section 2 interface. Unit tests: 70 notThis keep 64 exceptions, oldest dropped; 10 notThis cap the nudge at +0.15; 10 missed reach -0.15; a Layer-1 record raises; Layer-1 adjust and filter are identity.
2. `fox_scenario.py`: use the `Describer` (SigLIP2, cached) to embed fox/*, cat/*, and one repost per fox. A repost is a 0.9 centre crop, resized to 256 px, saved as JPEG q60 via `variants.py` where it fits. Compile "cat" with `twin.teacher.compile_concept`. Assert the D6 precondition. Then apply one notThis on fox[0], re-judge with `adjust` and `filter`, and assert: fox[0] and its repost are not `hide`; every cat that was `hide` before is still `hide`. Write the vectors (f16 b64) and the expected decisions to `guard/brain/src/test/resources/corrections/fox.json` (small: only the photos used).
3. `CorrectionBook.kt` mirrors the Python code. `FoxScenarioTest.kt` replays fox.json and gets the same decisions. `LimitsTest.kt` repeats the Python limit tests. `CorrectionStoreTest.kt`: round-trip through SecureStore; the raw file bytes do not contain the string "nudge"; a wrong key fails. No `java.net`/`okhttp` import is allowed in `learn/` or `CorrectionStore.kt` (verify greps for this).
Verify `6.2.1.ps1`: ruff on the owned .py files; pytest `workshop/twin/tests/test_corrections.py`; run `fox_scenario.py` (it skips with code 3 and prints PENDING if the SigLIP2 cache is absent); `with-env.ps1 --cd guard .\gradlew.bat --no-daemon :brain:test :teacher:test :brain:ktlintCheck :teacher:ktlintCheck` (run the ktlint tasks only if they exist); grep for no network import → `VERIFY 6.2.1: PASS`.

### 6.2.2 Workshop server (Flask)
Goal: `workshop/api/` serves models and packs, and accepts opt-in data with enforced privacy.
Owned: `workshop/api/` (app.py, schemas.py, signing.py, client.py, `tests/`, `keys/.gitignore`), `pyproject.toml` + `uv.lock` (cryptography only), `tools/verify/6.2.2.ps1`.
Interfaces: `create_app(config: dict | None) -> Flask`. Config keys: `PACK_DIR`, `MODEL_DIR`, `KEY_DIR`, `DEV_TOKEN`, `ENCODER` (injectable; tests use a hash fake).
Endpoints (all JSON; errors are `{"error": "<code>"}` and never echo input):
- `GET /v1/models` → `{"models": [{"manifest": ModelManifest, "url", "sha256", "size"}], "signature": b64}`. The signature covers the canonical JSON of `models`. `GET /v1/models/<modelId>/file` serves the bytes.
- `GET /v1/packs` → `{"packs": [{packId, name, version, sensitive:false, sha256, url, accuracy}] + one {"packId": "sensitive-bundle", sensitive:true, sha256, url}, "signature"}`. `GET /v1/packs/<packId>` serves non-sensitive packs only; a sensitive id returns 404. `GET /v1/packs/sensitive-bundle` returns all sensitive packs in one JSON `{"packs": [...]}`.
- `POST /v1/compile` body `{consent: true, words: [1..8 strings, each ≤ 64 chars]}` → `{"concepts": [CompiledConcept]}`.
- `POST /v1/metrics` body `{consent: true, day: "YYYY-MM-DD", counts: {<enum key>: "0"|"1-9"|"10-99"|"100+"}}` → 204. Keys: `covers`, `peeks`, `corrections`, `packsInstalled`.
- `POST /v1/dev/eval` header `X-Dev-Token` (403 if missing or wrong) with body `{packId}` → that pack's report JSON.
Rules: pydantic models with `extra="forbid"` and `strict=True`. `consent` must be literal `true` (else 403 `consent_required`). An unknown field gives 422 `unknown_field`, and the response never contains the field name or value. The request logger records only method, path, status and ms. Opt-in routes never call `request.get_data` outside the parse helper. The response has no `Set-Cookie`, and the server reads no IP or identifier headers.
`client.py`: `fetch_catalogue(base) -> dict` checks the signature with the pinned public key; `download(entry) -> bytes` checks sha256 and then validates the ConceptPack or ModelManifest schema via `workshop.contracts`. Any failure raises `Rejected`.
Tests (Flask test client plus `caplog`): API shapes for each endpoint (AC-04); a "screen-like" extra field (`{"consent":true,"day":..,"counts":{},"screenText":"SECRET-123"}`) is rejected and `SECRET-123` is absent from the response and all captured logs; missing consent gives 403; a sensitive id is not individually served; the client rejects a tampered pack byte, a tampered sha in the catalogue, and a bad signature (AC-06); the client accepts a good pack and a good model.
Verify `6.2.2.ps1`: ruff; pytest `workshop/api/tests`; start `flask --app workshop.api.app run` for 5 s, fetch `/v1/packs` with client.py, then stop it → `VERIFY 6.2.2: PASS`.

### 6.2.3 Topic packs
Goal: 5 ConceptPacks, each with recorded accuracy or an honest PENDING-HUMAN.
Owned: `workshop/packs/` (5 pack JSONs, `build_packs.py`, `eval_packs.py`, `text_sets/*.jsonl`, `reports/`, `tests/`), `data/public/photos/alcohol/` + `index.json` and LICENSES rows for alcohol only (via a `public_set.py --group alcohol` extension in `workshop/twin/public_set.py`, fetch function only), `tools/verify/6.2.3.ps1`.
Packs: `spiders`, `needles` (sensitive), `gore` (sensitive), `alcohol` (sensitive), `spoiler-<show>` (the team's pick; use a long-finished public show, names and keywords only). Each concept has 4-8 `looksLike`, 3-6 `butNot` (spiders: crab, tick-free ant, cat toy; alcohol: juice, soda, tea; needles: pens, knitting needles, thermometer; gore: tomato sauce, red paint, ketchup), and 5-15 `keywords`. Gore and needles prompts are plain descriptive text.
Steps:
1. `build_packs.py` writes and schema-validates the packs (`workshop.contracts`).
2. `eval_packs.py --pack X` works as follows. For image sets, it uses `Describer` plus `compile_concept` plus judge(balanced). Recall = share of target photos marked hide; cleanFalseCoverRate = share of clean photos (cat/dog/fox/neutral) marked hide. Butnot terms may be tuned at most 2 times on the image set (record the tries). For text sets, it uses keyword rules on `text_sets/<pack>.jsonl` (≥ 20 positive and ≥ 40 harmless negative lines, written by hand, no graphic detail). It writes the report and copies `accuracy` and a one-line result into the pack `description`.
3. Status: image PASS/FAIL for spiders and alcohol (alcohol PENDING-HUMAN under D5); needles, gore and spoiler get image `PENDING-HUMAN` with text metrics recorded.
Tests: every pack validates; the sensitive flags are needles/gore/alcohol true and spiders/spoiler false; every report exists with a valid status.
Verify `6.2.3.ps1`: ruff; pytest `workshop/packs/tests`; `eval_packs.py --all --cached` (reuses cached embeddings, < 3 min) → `VERIFY 6.2.3: PASS`.

## 4. Acceptance criteria
| ID | Criterion | Pass threshold | How verified (now) |
| --- | --- | --- | --- |
| AC-6.2-01 | Fox scenario | After one "not a cat" correction, the same fox photo and its reposts stay uncovered, and real cats are still covered | fox_scenario.py + FoxScenarioTest; phone recording PENDING-HUMAN |
| AC-6.2-02 | Limits hold | Threshold change capped at ± 0.15; ≤ 64 exceptions per concept; Layer 1 unaffected by corrections | Unit tests (Py + JVM) |
| AC-6.2-03 | Corrections stay local (no waiver) | 0 network requests during a correction | No-network-import grep now; PCAPdroid PENDING-HUMAN |
| AC-6.2-04 | API to spec | Every endpoint returns the agreed shapes | workshop/api tests |
| AC-6.2-05 | Privacy enforced (no waiver) | Unknown fields are rejected without echoing input; opt-in endpoints refuse requests without consent; no request bodies appear in logs | Privacy tests; caplog inspection |
| AC-6.2-06 | Tamper-proof (no waiver) | The app rejects a manifest or pack with a bad signature or checksum | client.py tests; Guard on-device PENDING-HUMAN |
| AC-6.2-07 | Packs are good | 5 packs, each ≥ 80% recall and ≤ 5% clean false covers on its own test set; sensitive packs flagged | Eval reports; image rows for needles/gore/spoiler PENDING-HUMAN |

## 5. Proof test "Not a cat"
Laptop (now): run 6.2.1-3 verify. The fox and repost stay uncovered, cats stay covered; bad requests (extra screen-like field, no consent, tampered pack) are rejected and the logs hold no bodies; install the Spiders pack via client.py and score it on the spider photos. Phone (later): see section 6. Evidence goes in `progress/.../evidence/`: the verify outputs, the pytest logs, `reports/*.json` and the server log.

## 6. Human checklist (PENDING-HUMAN, one HUMAN_CHECKS item)
1. Test Feed with a fox post and a repost further down: long-press → "That's not a cat"; scroll away and back; the repost stays uncovered and a real cat is covered (scrcpy recording).
2. PCAPdroid running during step 1 shows 0 requests from Veil.
3. The app downloads the Spiders pack and a model update from the laptop server; a tampered pack is refused and the old pack stays.
4. On a controlled, consented set (a human curates it; Claude never fetches it), score the needles, gore and spoiler image recall and false covers; packs that fail stay out of the catalogue.
