# SPEC · Phase 3.2 "Profile on cloud phones"
MODEL: claude-opus-5-5 · Status: APPROVED (orchestrator) · Based on PLAN.md lines 990-1080 · ORCHESTRATOR §0 (F1-F12), §12

## 1. Deviations / risks
- **DV-1 No AI Hub token (HC-003), no phone.** All tooling runs end to end on recorded fixtures (`--fixture`, default). Live numbers come from ONE human command (§6). Every fixture-derived row is labelled `(fixture)` and links `fixture://<job>`; AC rows are AUTO-on-fixtures, live part PENDING-HUMAN.
- **DV-2 Models** = the 9 manifests from 3.1 (`workshop/forge/*/manifests/*.json`). Look path = nudenet-320n/640m, yoloe-26s-embed-top100, siglip2-base-image-b1/b4/b16, toxicity-seq128/256. `siglip2-base-text` runs at setup only: it is the one allowed AC-3.2-01 exception if needed.
- **DV-3 Precision candidates:** detectors (nudenet, yoloe) float16/w8a16/w8a8; transformers (siglip2, toxicity) float16/w8a16 only (no w8a8, no mixed int16).
- **DV-4 Score** = "points" 0-100 per model: detectors use the ch1 scorer (`workshop/eval/score_screens.py`) on decoded hub outputs; embedders/toxicity use 100 × mean cosine vs laptop float32 outputs (parity.py convention). Fixture mode reads recorded scores.
- **DV-5 Final manifests** go to the new `workshop/forge/manifests/` (runtime `onnxruntime-qnn`, file = downloaded compiled asset in `data/forge/cloud/`). The 3.1 per-model manifests stay untouched. In fixture mode the writer targets `--out <tmp>` with tiny stand-in files; the real directory is filled only by `--live`.
- **Risk:** qai-hub option names for QNN targets (`--target_runtime precompiled_qnn_onnx`, `submit_quantize_job`, `submit_link_job`) are used only on the live path; Builder checks them in the installed qai-hub 0.56.0 wheel, not the web. Privacy (§12.6): only the 50 test crops + calibration crops from `data/public/set` are uploaded, live only.

## 2. Shared interfaces (plain JSON, no cross-imports; package `workshop/forge/cloud/`, CLI `uv run python -m workshop.forge.cloud.<mod> [--live|--fixture] [--out DIR]`)
- Device const: `DEVICE = "Samsung Galaxy S26 (Family)"`; job link `https://app.aihub.qualcomm.com/jobs/<id>/` (fixture: `fixture://<id>`).
- `out/profile.json` (3.2.1 writes): `{"source":"fixture|live","device":str,"models":[{"modelId","precision","batch","compileJob","profileJob","quantizeJob"|null,"latencyMs":float,"peakMemMb":float,"layers":{"npu":int,"gpu":int,"cpu":int},"npuShare":float,"offChip":[{"layer","op","unit","cause"}]}]}`
- `out/precision.json` (3.2.2 writes): `{"source","models":[{"modelId","float":{"score","latencyMs"},"candidates":[{"precision","score","latencyMs","inferenceJob"}],"chosen":str,"delta":float}]}`
- `out/budget.json` (3.2.3 writes): `{"source","mode":"Balanced","rows":[{"step","ms","job"|null}],"totalMs","limitMs":45,"pass":bool,"modes":{"Light":{...},"Balanced":{...},"Strict":{...}}}`
- `out/` = `workshop/forge/cloud/out/` (committed; fixture runs write `source:"fixture"`). Each sub-phase owns its own fixtures under `workshop/forge/cloud/fixtures/<n>/`, shaped as above, so none waits for another.
- Raw hub profile shape parsed by 3.2.1 (as returned by `InferenceJob.download_profile()`): `execution_summary.estimated_inference_time` (µs), `execution_summary.estimated_inference_peak_memory` (bytes), `execution_detail[]` with `name`, `type`, `compute_unit` ∈ {NPU, GPU, CPU}.

## 3. Sub-phases (all three build in parallel)
### 3.2.1 Compile and profile
Goal: per model × precision compile/quantize/profile submitter + collector + NPU-share parser.
Owned: `workshop/forge/cloud/__init__.py`, `hub.py`, `profile.py`, `placement.py`, `fixtures/1/`, `out/profile.json`, `workshop/forge/tests/test_cloud_profile.py`, `tools/verify/3.2.1.ps1`.
- `hub.py`: `class HubClient(Protocol)`: `compile(model_path, precision, batch) -> dict`, `quantize(model_path, calib_dir, w, a) -> dict`, `profile(job_target) -> dict`, `inference(job_target, inputs) -> dict`, `link(targets) -> dict`; each returns `{"jobId","url","status",...payload}`. `FixtureClient(root)` replays `fixtures/1/<modelId>/<precision>/{compile,profile,quantize}.json`; `LiveClient()` wraps qai_hub (late import, as in `workshop/bench/aihub.py`). `get_client(live: bool)`.
- `placement.py`: `parse(profile: dict) -> dict` → layers counts, `npuShare`, `offChip` list; `cause` = "unsupported op <type>" or "dynamic shape" (when a name/type hints `Shape`/`NonZero`/dynamic dims), else "unknown".
- `profile.py main`: loops models (DV-2) × precisions (DV-3); quantized variants use `quantize` with 64 calibration crops from `data/public/set` (live only); writes `out/profile.json`. Fixtures: all 9 models at float16 + candidates; include ONE model with 2 CPU layers (`NonZero`) to exercise `offChip`.
- Tests: parse counts/share; fixture run writes valid profile.json with npuShare=1.0 except the planted one.
- Verify: ruff (project config) on owned paths; pytest the test file; run `profile --fixture` and assert JSON keys. Ends `VERIFY 3.2.1: PASS`. < 1 min.

### 3.2.2 Choose precision per model
Goal: fastest precision within 2 points of float, with before/after scores.
Owned: `workshop/forge/cloud/precision.py`, `score_adapter.py`, `fixtures/2/`, `out/precision.json`, `workshop/forge/tests/test_cloud_precision.py`, `tools/verify/3.2.2.ps1`.
- `precision.py`: `choose(float_score: float, cands: list[dict], max_drop=2.0) -> str` = lowest `latencyMs` among cands with `float_score - score <= max_drop`; fall back to `"float16"`. Tie → higher-bit precision. Main reads profile latencies (`out/profile.json` if present else `fixtures/2/profile.json`) + scores, writes `out/precision.json`.
- `score_adapter.py`: `score(modelId, outputs, reference) -> float` per DV-4; fixture mode reads `fixtures/2/scores.json`. Live: runs `inference` on the 50 test crops/prompts per candidate, decodes with existing `decode.py`/parity helpers. No model loading in verify.
- Tests: choose() picks w8a8 when within 2.0, rejects 2.01 drop, fallback path; fixture run writes valid precision.json.
- Verify: ruff, pytest, `precision --fixture`. Ends `VERIFY 3.2.2: PASS`.

### 3.2.3 Batch variants, budget, manifests, report
Goal: Describer b1/b4/b16 (+ link job if allowed), Balanced budget, per-mode sizes, v1 manifests + validator, `docs/reports/ch3-profile.md`, live runner.
Owned: `workshop/forge/cloud/budget.py`, `budget_config.json`, `manifests.py`, `report.py`, `fixtures/3/`, `out/budget.json`, `workshop/forge/manifests/` (live only), `docs/reports/ch3-profile.md`, `tools/cloud_live.ps1`, `workshop/forge/tests/test_cloud_budget.py`, `tools/verify/3.2.3.ps1`.
- `budget_config.json`: Balanced = preprocessing 3.0 ms (constant, laptop-estimated, labelled) + nudenet-320n + yoloe-26s + siglip2 image at batch 4 (assumed 4 new crops/look) + toxicity-seq128 × 1 + logic 1.0 ms. Light/Strict use nudenet-320n/640m and siglip2 b1/b16; YOLOE only `26s` exists → noted as size gap.
- `budget.py`: `compute(profile: dict, precision: dict, cfg: dict) -> dict` uses the chosen-precision latency per row; `pass = totalMs <= 45`.
- `manifests.py`: `build(base_manifest, chosen, file_path) -> dict` (copies 3.1 manifest, sets `precision`, `runtime:"onnxruntime-qnn"`, `file{path,sha256,bytes}`); `validate_dir(dir) -> list[str]` = schema via `workshop.contracts.validate.validate("ModelManifest", m)` + sha256 vs file (`common.sha256_file`) + every `fingerprint` manifest has `spaceId` and `pairedWith`. CLI: `manifests --fixture --out <tmp>` writes stand-in 1 KB files; `--live` writes `workshop/forge/manifests/`; `manifests --check DIR`.
- `report.py`: renders `docs/reports/ch3-profile.md` from `out/*.json` (missing file → "pending"): per-model table (latency, peak mem, NPU share, off-chip + plan, job links), precision table (float vs chosen, delta), budget table, modes table; every number cell carries its job link; header line `Source: fixture|live`.
- `tools/cloud_live.ps1`: `profile --live; precision --live; budget --live; manifests --live; manifests --check workshop/forge/manifests; report`, stops on first error.
- Tests: compute() total on fixture ≤ 45 → pass, 46 → fail; validate_dir catches bad checksum and missing `pairedWith`; report has a link in every number row.
- Verify: ruff, pytest, `budget --fixture`, `manifests --fixture --out $env:TEMP\veil-3.2.3` then `--check` it, `report`, assert report exists with `Source:`. Ends `VERIFY 3.2.3: PASS`.

## 4. Acceptance
| ID | Criterion | Pass threshold | AUTO (fixtures) | Live |
| --- | --- | --- | --- | --- |
| AC-3.2-01 | All on the AI chip | 100% of layers on the AI chip for every model used during looks; at most one documented exception, outside the look path | parser + report on fixtures (3.2.1) | PENDING-HUMAN |
| AC-3.2-02 | Accuracy kept | Chosen precision stays within 2 points of float on the Chapter 1 test scores | chooser tests (3.2.2) | PENDING-HUMAN |
| AC-3.2-03 | Budget fits | Profiled total for one Balanced look ≤ 45 ms | budget tests (3.2.3) | PENDING-HUMAN |
| AC-3.2-04 | Manifests valid | Every manifest validates; checksums match the files; `spaceId` and paired text encoder set for every fingerprint model | validator on tmp set (3.2.3) | PENDING-HUMAN |
| AC-3.2-05 | Auditable | Every number in the report links to its AI Hub job | report test (3.2.3) | PENDING-HUMAN |

## 5. Proof test "Cloud phone run"
AUTO now: run all three verify scripts; report renders with fixture links, placement parsed, budget and manifests checked. Live (PENDING-HUMAN, after token): `cloud_live.ps1` sends each model with 50 test crops/prompts as inference jobs; `score_adapter` compares to laptop outputs (cosine ≥ 0.98 required, recorded in precision.json); placement report shows 100% NPU; measured times feed the budget table. Evidence: job links in `docs/reports/ch3-profile.md`.

## 6. Human checklist (one HUMAN_CHECKS item)
1. HC-003: `uv run qai-hub configure --api_token <token>` (token never written to files).
2. `powershell -File "D:\iqoo finale\veil\tools\cloud_live.ps1"` (background, ~1-2 h, uploads test crops only).
3. Review `docs/reports/ch3-profile.md`: off-chip layers, chosen precisions, Balanced total ≤ 45 ms; then commit `workshop/forge/manifests/`.
