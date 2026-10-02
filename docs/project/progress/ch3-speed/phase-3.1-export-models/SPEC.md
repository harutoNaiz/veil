# SPEC Phase 3.1 Export the models
MODEL: claude-opus-5-5 · Status: APPROVED (orchestrator; heavy runs H0-H4 serialized by the orchestrator) · PLAN lines used: 880-988 (Ch.3 intro, 3.1.1-3.1.3, PT-3.1, AC-3.1-01..07), 2173-2181 (App. C licences) · Inputs: PHASE 1.3 notes, D-004.

## 1. Deviations and risks
- **Deviation (layout):** ONNX files are large, so they live in git-ignored `data/forge/<model>/`. Git tracks `workshop/forge/<model>/` (export script, runtime adapter, `parity.json`, `checksums.sha256`, draft manifests). This replaces PLAN's "ONNX files in `workshop/forge/<model>/`".
- **Deviation (source):** there is no AI Hub token, so SigLIP2 is exported by us from the HF cache (`google/siglip2-base-patch16-224`), float32 only. w8a16 waits for 3.2.
- **Deferred (NPU fit):** we cannot check yet whether QNN runs TopK or other ops (no phone, no AI Hub). All files run on `onnxruntime-cpu`. The 3.2 profiling decides whether TopK moves to app code. Every exported file is fixed-shape now.
- **Deviation (YOLOE masks):** variant C uses only boxes, so the wrapper exports the detection and embedding branch only, with no mask coefficients or protos.
- **Deviation (YOLOE letterbox):** 1.3 used Ultralytics `auto=True`, which gives a rectangular input. The export uses a fixed 640×640 square letterbox (pad 114). PT-3.1 measures the effect on decisions.
- **Risk (YOLOE text encoder):** `mobileclip2_b.ts` is TorchScript. First try `torch.onnx.export(..., dynamo=False)`. If that fails, try the dynamo exporter. If both fail, mark the text-encoder row BLOCKED, ship a precomputed `proposal_pe.npy` plus a concept-text table, and raise it. The rest of 3.1.2 still closes.
- **Risk (toxicity model id):** PLAN names no checkpoint. The Builder picks one Apache-2.0, mmBERT-small-based multilingual toxicity classifier from the HF API (one search) and records the id, URL and licence in `parity.json`. The download is allowed once, with `HF_HUB_DISABLE_XET=1`.
- **Human (Layer 1):** NudeNet parity uses only harmless images (1.3 public and synthetic screens, fresh screens). "Layer 1 positive-class parity on the controlled evaluation set" is **PENDING-HUMAN**. Agents never fetch, generate or view explicit material. Toxicity sample text is never printed or viewed: only labels and scores are used.
- **Human:** Netron screenshots (PT-3.1 evidence) are PENDING-HUMAN. The machine substitute is the shape-check (AC-3.1-01).
- **Memory:** 7.4 GB RAM. Builders run only light tests on tiny inputs. Every full export and parity run is a separate HEAVY step that the orchestrator runs **one at a time** (H1 → H2 → H3 → H4). The H0 downloads use network only and may overlap.

## 2. Shared interfaces (all sub-phases)
**Paths.** Tracked: `workshop/forge/<model>/` (`export.py`, `runtime.py`, `parity.py`, `parity.json`, `checksums.sha256`, `manifests/<modelId>.json`). Untracked: `data/forge/<model>/*.onnx` plus caches. `<model>` ∈ `siglip2 | yoloe | nudenet | toxicity`.

**`workshop/forge/common.py`.** Owned by 3.1.1, which writes it FIRST (step 1). The other Builders import it and never edit it.
```python
REPO: Path; FORGE_DATA = REPO / "data" / "forge"
OPSET = 17                                   # every export; allowed range 17-20
def sha256_file(p: Path) -> str
def shape_report(onnx_path: Path) -> dict    # {"opset": int, "inputs": [TensorSpec], "outputs": [TensorSpec], "fixed": bool}
                                             # fixed = every graph input/output dim has dim_value > 0 and no dim_param
def write_checksums(model: str, files: list[Path]) -> Path   # workshop/forge/<model>/checksums.sha256, "<sha>  <path rel. to veil>"
def check_checksums(model: str) -> list[str]  # mismatching paths ([] = reproducible)
def write_manifest(m: dict, model: str) -> Path  # validates via workshop.contracts.validate.validate("model-manifest", m) first
def write_report(model: str, report: dict) -> Path  # workshop/forge/<model>/parity.json
def cosine_rows(a, b) -> np.ndarray          # row-wise cosine, float64
def main(argv)  # CLI: `python -m workshop.forge.common shapes <dir>` -> prints one line per .onnx, exit 1 if any not fixed/opset∉17-20
                #      `python -m workshop.forge.common checksums` -> prints the union of all checksums.sha256 (the phase checksum list)
```
**`parity.json` shape:**
```json
{"model": "siglip2", "subPhase": "3.1.1", "created": "<iso>", "tools": {"torch": "...", "transformers": "...", "ultralytics": "...", "onnx": "...", "onnxruntime": "..."},
 "source": {"url": "https://...", "licence": "...", "revision": "<hf sha or file sha>"},
 "files": [{"path": "data/forge/siglip2/siglip2-image-b1.onnx", "sha256": "...", "bytes": 1, "opset": 17, "fixed": true, "inputs": [], "outputs": []}],
 "checks": [{"id": "AC-3.1-02.image.mean", "value": 0.999, "threshold": ">= 0.98", "n": 200, "pass": true, "note": ""}],
 "nondeterminism": "", "pass": true}
```
**Draft manifest.** One per ONNX file, valid against `contracts/model-manifest.schema.json`. It has `precision: "float32"`, `runtime: "onnxruntime-cpu"`, `file.path` = `data/forge/...`, plus `sourceUrl` and `licence` (AC-3.1-07). Embedding and finder files also carry `fingerprint`.
**Runtime adapters** (used by PT-3.1; they mirror the 1.3 classes so `workshop.twin.run` needs no change):
```python
# workshop/forge/siglip2/runtime.py (3.1.1)
class OnnxDescriber:  # same surface as workshop.twin.describer.Describer
    space_id = "siglip2-base-p16-224"; text_model_id = "siglip2-base-text"; image_model_id = "siglip2-base-image"
    def __init__(self, folder: Path = FORGE_DATA / "siglip2") -> None
    def embed_images(self, images: list[Image.Image], batch: int = 16) -> np.ndarray  # (N,768) L2; uses b16/b4/b1 files, pads the last chunk
    def embed_texts(self, texts: list[str]) -> np.ndarray                              # (M,768) L2; lower-case, pad to 64
# workshop/forge/yoloe/runtime.py (3.1.2)
class OnnxFinder:     # same surface as workshop.twin.finder.Finder for boxes()
    def __init__(self, folder: Path = FORGE_DATA / "yoloe") -> None
    def boxes(self, img: Image.Image) -> list[dict]        # region dicts via Finder._regions; CONF/MIN_SIDE/IOU/MAX_BOXES from finder.py, NMS in numpy
    def box_embeddings(self, img) -> tuple[list[dict], np.ndarray]
    def embed_texts(self, texts: list[str]) -> np.ndarray   # ONNX MobileCLIP2-B text encoder, (M,512) L2
```

## 3.1.1 Describer (SigLIP2) export + PT-3.1 harness
**Goal:** phone-ready SigLIP2 image encoders (batch 1/4/16) and a text encoder that match the laptop float model.
**Owned paths:** `workshop/forge/__init__.py`, `workshop/forge/common.py`, `workshop/forge/siglip2/`, `workshop/forge/proof.py`, `workshop/forge/tests/test_common.py`, `workshop/forge/tests/test_siglip2.py`, `workshop/forge/tests/test_proof.py`, `workshop/forge/tests/__init__.py`, `tools/verify/3.1.1.ps1`, `tools/verify/pt-3.1.ps1`, `pyproject.toml`, `uv.lock` (only if `uv add onnxscript` is needed; no other sub-phase touches these).
**Files:** `siglip2/export.py` (`--out data/forge/siglip2`), `siglip2/parity.py`, `siglip2/runtime.py`, `proof.py`.
**Steps:**
1. Write `common.py` exactly to the §2 interface, then `__init__.py` files.
2. `export.py`: load the HF model offline (`HF_HUB_OFFLINE=1`). Wrap `get_image_features` and `get_text_features`, pooled and L2-normalised in-graph. Export with `torch.onnx.export` at opset 17 with no `dynamic_axes`: `siglip2-image-b{1,4,16}.onnx` (input `pixel_values` (B,3,224,224) f32, output `fingerprint` (B,768)) and `siglip2-text.onnx` (input `input_ids` (1,64) int64, output `fingerprint` (1,768)). The tokenizer and image preprocessing stay in app code; the Python runtime reuses the HF processor. Write checksums and 4 manifests (`imageEmbedding`/`textEmbedding`, spaceId `siglip2-base-p16-224`, dim 768, `pairedWith`; sourceUrl `https://huggingface.co/google/siglip2-base-patch16-224`, licence `Apache-2.0`).
3. `parity.py`: take 200 crops from 1.3 dev screens: `workshop.twin.pieces.make_pieces` over public dev, then synthetic dev, in fixed order, first 200 regions, seed-free. Compare `Describer.embed_images` (torch) with `OnnxDescriber`. The b1, b4 and b16 files are each checked on the same 200 crops. Use 100 prompts: concept-card prompts from `workshop.twin.teacher.concept_card` for cats, spiders, dogs, bicycles, flowers and more, deduplicated, first 100. Compare torch `embed_texts` with ONNX.
4. `proof.py` (PT-3.1, §5): `--engine torch|onnx --out <dir>` runs `run.run_screens(..., variant="C", use_cache=False)`. ONNX uses `piece_fn=describer_pieces(OnnxDescriber(), finder_boxes_fn=OnnxFinder().boxes)` and `encoder=OnnxDescriber()`. `--compare a b` writes `data/forge/pt-3.1/diff.json` and `diff.md`. Light tests use fake findings only.
**HEAVY H1 (orchestrator runs alone):** `powershell -NoProfile -ExecutionPolicy Bypass -File tools\verify\3.1.1.ps1 -Heavy`, which runs export, then parity, then the checksum re-check.
**Verify `tools/verify/3.1.1.ps1`:** `uv run --locked ruff check workshop/forge/common.py workshop/forge/siglip2 workshop/forge/proof.py workshop/forge/tests`. It runs pytest `test_common.py` (shape check on a tiny fixed vs dynamic ONNX built in-test; checksum round trip; manifest validation), `test_siglip2.py` (runtime padding logic with a stub session) and `test_proof.py`. If `-Heavy`: run the export, run `parity.py`, assert `parity.json.pass`, run `common shapes data/forge/siglip2`, and run `check_checksums("siglip2")` (if a checksum differs, `nondeterminism` must be non-empty and parity must pass). The script ends with `VERIFY 3.1.1: PASS`.
**Human:** none.

## 3.1.2 Object finder (YOLOE) export
**Goal:** a phone-ready finder that outputs boxes plus fingerprints, with no baked-in classes, plus its text encoder.
**Owned paths:** `workshop/forge/yoloe/`, `workshop/forge/tests/test_yoloe.py`, `tools/verify/3.1.2.ps1`.
**Files:** `yoloe/wrapper.py` (`class EmbedWrapper(nn.Module)`), `yoloe/export.py`, `yoloe/parity.py`, `yoloe/runtime.py`, `yoloe/proposal_pe.npy` (8×512, tracked, tiny).
**Wrapper I/O (fixed):**
- Inputs: `images` (1,3,640,640) f32 RGB 0-1 square letterbox; `proposal_pe` (1,8,512) f32. `proposal_pe` holds the 8 `PROPOSAL_VOCAB` text embeddings, fed by the app, so nothing is baked in.
- Outputs: `boxes` (1,100,4) xyxy in input pixels; `objectness` (1,100) = max over the 8 prompts of sigmoid(head score); `fingerprint` (1,100,512) = L2-normalised BN output of the contrastive head (the point before the text dot); `fp_scale` (1,100) = ‖BN feat‖·exp(logit_scale of that level); `fp_bias` (1,100). App-side concept score = sigmoid(fp_scale·cos(fingerprint, text) + fp_bias). Top-100 by objectness is a fixed-k `TopK` in-graph (see §1 Deferred).
**Steps:**
1. Build `EmbedWrapper` from the UNFUSED `YOLOE("data/models/yoloe-26s-seg.pt")`, inside `contextlib.chdir(MODELS)` with `YOLO_AUTOINSTALL=False`. It reuses the head's box decode and the one2one branch, and replaces the class einsum with the outputs above.
2. `export.py`: export `yoloe-26s-embed-top100.onnx` at opset 17 with no dynamic axes. Export the text encoder `mobileclip2-b-text.onnx`: input `input_ids` (1,77) int64 (CLIP tokenizer in app code), output (1,512) L2 (see §1 Risk). Save `proposal_pe.npy`, write checksums, and write 2 manifests: `objectFinder` with fingerprint spaceId `yoloe-26s-mobileclip2-b`, dim 512, role `region`, pairedWith `mobileclip2-b-text`; and `textEmbedding`. Sources: `https://github.com/ultralytics/ultralytics`, `AGPL-3.0`, and `https://github.com/apple/ml-mobileclip` with `Apple ML research licence (research only; verify)`.
3. `parity.py`: use the same 640×640 tensors for both engines, on all public dev and synthetic dev screens (cap 60). The reference is Ultralytics' YOLOE with `set_classes(L, get_text_pe(L))` and a forward on that tensor, keeping detections with conf ≥ 0.05. Run three prompt lists against the same ONNX file: PROPOSAL_VOCAB, list 1 `["cat","spider"]` and list 2 `["bicycle","dog","flower"]`, each padded to 8 by repeating the last row. Checks: every reference detection has an ONNX box with IoU > 0.95 and |Δscore| < 0.02; every fingerprint norm is 1 ± 0.001; AC-3.1-04 shows the same file sha for both lists, with both passing. Text encoder: cosine ≥ 0.999 against `get_text_pe` on the same 100-prompt rule as 3.1.1 (the report states this threshold as our choice; PLAN gives none).
4. `runtime.py` `OnnxFinder` per §2.
**HEAVY H2:** `powershell -NoProfile -ExecutionPolicy Bypass -File tools\verify\3.1.2.ps1 -Heavy`
**Verify `tools/verify/3.1.2.ps1`:** `uv run --locked ruff check workshop/forge/yoloe workshop/forge/tests/test_yoloe.py`. It runs pytest `test_yoloe.py`: numpy NMS and region conversion on fake arrays, the concept-score formula, and `proposal_pe.npy` shape. Use no model load in light mode. If `-Heavy`: export, then parity, assert pass, then shapes, then checksums. The script ends with `VERIFY 3.1.2: PASS`.
**Human:** none (licences flagged in the manifests).

## 3.1.3 Layer 1 (NudeNet) and toxicity export
**Goal:** phone-ready safety models, with decoding and NMS in app code.
**Owned paths:** `workshop/forge/nudenet/`, `workshop/forge/toxicity/`, `workshop/forge/tests/test_nudenet.py`, `workshop/forge/tests/test_toxicity.py`, `tools/verify/3.1.3.ps1`.
**Files:** `nudenet/{fetch.py,export.py,decode.py,parity.py}`, `toxicity/{fetch.py,export.py,parity.py}`.
**Steps:**
1. `nudenet/fetch.py`: plain-HTTP download of `320n.onnx` and `640m.onnx` from the NudeNet GitHub release (v3.4 weights) into `data/forge/nudenet/src/`. Record URL and sha. Do not install the pip package.
2. `nudenet/export.py`: load each file, set every graph input/output dim to a fixed value (1,3,320,320 / 1,3,640,640), remove any in-graph NMS if present, keep or convert to opset 17-20, run `onnx.checker` and shape inference, and save `nudenet-320n.onnx` and `nudenet-640m.onnx`. Write manifests (`nsfwDetector`, sourceUrl `https://github.com/notAI-tech/NudeNet`, licence `AGPL-3.0 (verify)`) and checksums.
3. `decode.py`: numpy only, the reference for the Kotlin port. `decode(raw, conf=0.2, iou=0.45, letterbox) -> list[(cls, score, xyxy)]` (YOLOv8 layout: transpose, argmax class, threshold, NMS, unletterbox).
4. `nudenet/parity.py`: use 200 harmless images (1.3 public set, synthetic dev and test screens, fresh screens; top up with deterministic crops or flips of these to reach 200). Original file plus `decode` gives the reference; the exported file plus `decode` gives the candidate. Detection agreement = matched (same class, IoU ≥ 0.5) / max(#ref, #new), pooled; an image where both have none counts as agreement. Do this for both models.
5. `toxicity/fetch.py`: one HF API search, then pick the model (§1 Risk). Download with `HF_HUB_DISABLE_XET=1` to the HF cache. Also download a public toxicity sample of ≤ 1,000 labelled rows (a multilingual toxicity dataset slice with an open licence; record URL and licence) into `data/forge/toxicity/sample.jsonl`. Never print or view text.
6. `toxicity/export.py`: export `toxicity-seq128.onnx` and `toxicity-seq256.onnx` (inputs `input_ids` and `attention_mask` (1,L) int64, output `logits` or `score` (1,C)) at opset 17. Write manifests (`toxicityClassifier`, `preprocessing.kind` `text`, `maxTokens` L) and checksums.
7. `toxicity/parity.py`: AUC of the PyTorch float model (natural length), against AUC of each ONNX length (pad or truncate to L). Check AUC drop ≤ 0.005 for each.
**HEAVY:**
- **H0 (network only; may overlap):** `tools\verify\3.1.3.ps1 -Fetch`
- **H3 (alone):** `powershell -NoProfile -ExecutionPolicy Bypass -File tools\verify\3.1.3.ps1 -Heavy`
**Verify `tools/verify/3.1.3.ps1`:** `uv run --locked ruff check workshop/forge/nudenet workshop/forge/toxicity workshop/forge/tests/test_nudenet.py workshop/forge/tests/test_toxicity.py`. It runs pytest: `decode` on synthetic arrays (threshold, NMS, unletterbox), the agreement metric on toy detections, the AUC helper and pad/truncate. If `-Heavy`: export both, run both parities, assert pass, then shapes, then checksums. The script ends with `VERIFY 3.1.3: PASS`.
**Human:** HC: Layer 1 positive-class parity on the controlled evaluation set (PENDING-HUMAN).

## 4. Acceptance criteria
| AC | Mode | How checked | Threshold (PLAN, word for word) |
| --- | --- | --- | --- |
| AC-3.1-01 Fixed shapes | AUTO | `python -m workshop.forge.common shapes data/forge` (all 4 models) plus Netron (human) | No model has a variable-size input or output |
| AC-3.1-02 Describer matches | AUTO (H1) | `workshop/forge/siglip2/parity.json` | Image fingerprints vs laptop float on 200 crops: mean cosine ≥ 0.98 and worst 5% ≥ 0.95. Text: ≥ 0.999 on 100 prompts |
| AC-3.1-03 Finder matches | AUTO (H2) | `workshop/forge/yoloe/parity.json` | Box overlap > 0.95 and score difference < 0.02 vs Ultralytics; every fingerprint has length 1 ± 0.001 |
| AC-3.1-04 List not baked in | AUTO (H2) | same report: one file sha, two lists pass | The same exported finder file works with two different concept lists |
| AC-3.1-05 Safety and text match | AUTO (H3) on harmless set · positive class PENDING-HUMAN | `nudenet/parity.json`, `toxicity/parity.json` | NudeNet ≥ 98% detection agreement; toxicity AUC drop ≤ 0.005 |
| AC-3.1-06 Reproducible | AUTO (H1-H3 re-run vs the Builder's `checksums.sha256`) | `check_checksums` in each `-Heavy` | Re-running each export script gives the same checksum, or any non-determinism is documented and parity still passes |
| AC-3.1-07 Licences recorded | AUTO | manifests validate; each has `sourceUrl` and `licence` (light verify) | Licence and source URL recorded for every file |
| Checksum list | AUTO | `python -m workshop.forge.common checksums` lists every exported file | A checksum list of every exported file |

## 5. Proof test PT-3.1 "Same answers, new engine"
**Machine part, H4 (alone, after H1-H3):** `powershell -NoProfile -ExecutionPolicy Bypass -File tools\verify\pt-3.1.ps1`
1. Screens: public dev, synthetic dev and `data/ch1/fresh/_verify-smoke` (no test split, per AC-1.3-08). Variant C, Balanced, concepts `cats,spiders`.
2. `proof.py --engine torch`, then `--engine onnx`, as separate processes, one at a time. Each writes findings and a 1.3-style gallery under `data/forge/pt-3.1/<engine>/`.
3. `--compare`: a decision = (screen, concept) "covered or not". Agreement must be ≥ 98% (PLAN: "at least 98% of decisions the same"). Per-region decisions (IoU ≥ 0.9 matched) are reported for information.
4. Change the list three times (`bicycles`; `dogs,flowers`; `cats,spiders` again) with the ONNX engine only. Record the sha256 of every `data/forge/**/*.onnx` before and after; they must be unchanged and every run must exit 0.
5. Run the shape check over `data/forge`.
6. The script prints `PT-3.1: PASS` and the paths of the two galleries and `diff.md`.

**Human part (PENDING-HUMAN):** look at both galleries side by side and open each ONNX file in Netron, taking screenshots.
**Passes when:** AC-3.1-02 to AC-3.1-04 hold.

## 6. Human items (paste into HUMAN_CHECKS.md)
```
HC-3.1-a  PT-3.1 human part: open data/forge/pt-3.1/torch/.../index.html and data/forge/pt-3.1/onnx/.../index.html
          side by side; confirm covers look the same; read data/forge/pt-3.1/diff.md. Reply OK / list differences.
HC-3.1-b  Netron: open every data/forge/**/*.onnx in https://netron.app (local file, nothing uploaded with the desktop app);
          screenshot the input/output panel of each into data/forge/pt-3.1/netron/; confirm no "?" or named dims.
HC-3.1-c  Layer 1 positive-class parity (PENDING-HUMAN): on your controlled evaluation set, run
          tools\verify\3.1.3.ps1 -Heavy -L1Set <your folder>; confirm >= 98% detection agreement. Agents never touch that set.
HC-3.1-d  Licences: confirm acceptable for the demo: YOLOE AGPL-3.0, MobileCLIP2 research-only, NudeNet AGPL-3.0,
          toxicity model <id> (licence in workshop/forge/toxicity/parity.json).
```
(3.1.3's `parity.py` accepts `-L1Set <dir>`, so HC-3.1-c needs no code change; that run reports and never prints images.)
