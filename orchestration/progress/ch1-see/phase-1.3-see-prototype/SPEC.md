# SPEC 1.3 The SEE prototype
MODEL: claude-opus-5-5 · Status: APPROVED (orchestrator 08:30; amendments A1 public real-photo set, A2 weights arriving late; see Builder prompts and LOG) · PLAN lines used: 80-87, 226-234, 439-549 (+ ORCHESTRATOR §0, §12; PHASE 1.1 notes)

Summary: SigLIP2 Describer + Teacher v0 + Judge v0 on tiles (variant A), YOLOE finder (variants B/C), then
calibration, mode thresholds, report and decision, all on 1.2's SYNTHETIC labelled set. Real test-set numbers and the
Chapter 1 gate are PENDING-HUMAN (one command ready). Three parallel Builders; the orchestrator runs 1.3.3's verify last.

## 0. Pre-step (orchestrator, once, before the Builders; heavy, about 5-10 min)
```powershell
cd "D:\iqoo finale\veil"
# (a) so a plain `uv sync` (bootstrap/bench_check) never strips torch: edit pyproject.toml [tool.uv]
#     default-groups = ["dev", "ml"]      (this change is committed with 1.3.1)
$env:YOLO_AUTOINSTALL = 'False'      # ultralytics must never pip-install on its own
powershell -NoProfile -ExecutionPolicy Bypass -File tools\with-env.ps1 uv sync --group ml
#     (if uv.lock changes, it goes into 1.3.1's commit; CPU torch from the locked PyPI wheels, see DV-1)
New-Item -ItemType Directory -Force data\models | Out-Null
powershell -NoProfile -ExecutionPolicy Bypass -File tools\with-env.ps1 uv run python -c "from transformers import AutoModel, AutoProcessor as P; m='google/siglip2-base-patch16-224'; AutoModel.from_pretrained(m); P.from_pretrained(m); print('siglip2 ok')"
powershell -NoProfile -ExecutionPolicy Bypass -File tools\with-env.ps1 --cd data\models uv run python -c "from ultralytics import YOLOE; m=YOLOE('yoloe-26s-seg.pt'); n=['cat']; m.set_classes(n, m.get_text_pe(n)); print('yoloe ok')"
#     If 'yoloe-26s-seg.pt' is not a known asset in 8.4.171, use 'yoloe-11s-seg.pt' and tell the Builders.
git status --porcelain     # expect only pyproject.toml (and maybe uv.lock); weights live in git-ignored data/models
```
If the SigLIP2 processor fails on the tokenizer (the huggingface-hub override flagged in 1.1), 1.3.1 runs
`uv add sentencepiece protobuf`. **Only 1.3.1 may run `uv add`**; the other Builders report any missing dependency in their record.

## 1. Deviations and risks
- **DV-1 CPU torch.** We use the locked PyPI CPU wheels. A CUDA re-lock costs time and adds risk. Speed numbers are relative only (PLAN says so). GPU torch is DEFERRED.
- **DV-2 Synthetic data.** All numbers come from 1.2's synthetic dev/test split and only check the pipeline. AC-1.3-01/02/03, the real-dev
  AC-1.3-04 re-check and the Chapter 1 gate are PENDING-HUMAN. They run with one command once 1.2's real frozen test set exists.
- **DV-3 Small YOLOE only.** We use `yoloe-26s-seg.pt` (fallback `yoloe-11s-seg.pt`). Medium is DEFERRED.
- **DV-4 Variant B is time-boxed.** Per-box YOLOE embeddings get about 8 min of Builder time. If extraction fails, B is reported as "not run: <reason>",
  and variant C (YOLOE boxes judged by SigLIP2 crops plus tiles) carries the finder. The orchestrator approved this fallback.
- **DV-5 Judge maths v0** (exact, §2). Fixed temperature T=100. The calibration offset is a shift in probability space, so it fits
  the CompiledConcept range of -1..1 and ports trivially to Kotlin.
- **DV-6 Tall-element crops** are 3 square W×W crops (top, middle, bottom). There is no layout lane yet.
- **DV-7 Example photos** are 3-5 labelled cat crops from dev, with their screens excluded from that measurement. The gain is marked "indicative".
- **DV-8 The report embeds no images.** The gallery stays in git-ignored `data/ch1/`; the report cites image names only.
- **R-1 Stray downloads.** Ultralytics downloads to the cwd. `finder.py` wraps model load and the first `get_text_pe` in
  `contextlib.chdir(data/models)`, sets `YOLO_AUTOINSTALL=False`, and `.gitignore` gets `*.pt` and `mobileclip*.ts`.
- **R-2 Interfaces from 1.2.** If the scorer's or data layout's API differs from §2, adapt only `data.py` and `run.score_findings`.

## 2. Interfaces (all three Builders code against these from minute 0)
Paths: `REPO = D:\iqoo finale\veil`. Work dirs (git-ignored): `data/models/`, `data/ch1/{cache,runs,gallery,fresh}/`.
Vectors: float32 numpy, L2-normalised. Pieces = `Region` dicts, verdicts = `Finding` dicts (contract v1.0; validate with
`workshop.contracts.validate.validate("Region"|"Finding"|"Concept"|"CompiledConcept", obj)` + `rules.check_rules`; cards use `rules.encode_f16/decode_f16`).

```python
# workshop/twin/data.py (1.3.1). The ONLY place that knows 1.2's dataset layout (read 1.2 SPEC §2).
@dataclass(frozen=True)
class Screen: image: Path; label: dict | None          # label = ScreenLabel dict, None for unlabelled folders
def load_split(set_name: str, split: str) -> list[Screen]   # set_name "synthetic"|"real", split "dev"|"test"
def load_folder(folder: Path) -> list[Screen]                 # *.png/*.jpg, label None (proof test)
def log_test_run(set_name: str, note: str) -> int  # append to data/ch1/test-runs.jsonl {set,n,utc,note};
                                                   # raise RuntimeError if this set already has 3 test runs
# workshop/twin/describer.py (1.3.1)
SPACE_ID = "siglip2-base-p16-224"; HF_ID = "google/siglip2-base-patch16-224"
class Describer:                  # also satisfies the TextEncoder protocol below
    space_id = SPACE_ID; text_model_id = "siglip2-base-text"; image_model_id = "siglip2-base-image"
    def __init__(self, device: str = "cpu") -> None
    def embed_images(self, images: list[Image.Image], batch: int = 16) -> np.ndarray   # (N, 768)
    def embed_texts(self, texts: list[str]) -> np.ndarray   # (M, 768); padding="max_length", max_length=64
class TextEncoder(Protocol):  space_id: str; text_model_id: str
                              def embed_texts(self, texts: list[str]) -> np.ndarray: ...
# workshop/twin/pieces.py (1.3.1)
def make_pieces(img, look_id=0, grid=(3, 6), overlap=0.25, tall_crops=3,
                finder_boxes: list[dict] | None = None, tiles: bool = True) -> list[dict]
    # Region dicts: "whole"(source whole, kind screen) + "t{r}-{c}"(tile) + "c{i}"(crop) + finder boxes as given
def crop(img: Image.Image, rect: dict) -> Image.Image
# workshop/twin/teacher.py (1.3.1). Teacher v0
LOOKS_LIKE = ["a photo of a {c}", "a cartoon {c}", "a drawing of a {c}", "a {c} emoji", "a close-up of a {c}"]
IGNORE = ["a screenshot of an app", "text on a screen", "a user interface"]
LOOKALIKES = {"cat": ["a dog", "a fox", "a lion", "a stuffed toy"],
              "spider": ["an ant", "a crab", "a scorpion", "a beetle"]}   # unknown words: [] (or 1 neutral if schema needs it)
def concept_card(word: str) -> dict          # Concept v1.0; "cats" -> conceptId "cats", {c}="cat" (strip one trailing s)
def compile_concept(concept: dict, enc: TextEncoder, calibration: Path | dict | None = CALIB_PATH,
                    thresholds: Path | dict | None = THRESH_PATH, example_centroid: np.ndarray | None = None) -> dict
    # CompiledConcept v1.0; merges calibration["concepts"][id] (calibrationOffset, butNotExtra, exampleThreshold)
    # and thresholds.json if the files exist; defaults thresholds {light .7, balanced .5, strict .3}, margin .01, offsets 0
CALIB_PATH = workshop/twin/calibration.json; THRESH_PATH = workshop/twin/thresholds.json   # written by 1.3.3
# workshop/twin/judge.py (1.3.1). Judge v0, exact maths:
#  sL,sN,sI = max cosine of piece vs looksLike / butNot / ignore (empty group -> -1)
#  p_raw = softmax(T*[sL,sN,sI])[0], T = 100 ;  p = clip(p_raw + calibrationOffset + userOffset, 0, 1)
#  margin = sL - sN ; score = sL ; sE = cos(piece, exampleCentroid) if present
#  hide if (p >= thr[mode] and margin >= cc.margin) or (sE is not None and sE >= exampleThreshold)
#  nearMiss if not hide and p >= thr[mode] - 0.1 ; else leave
def judge(vecs: np.ndarray, cc: dict, mode: str = "balanced") -> list[dict]  # [{p_raw, probability, score, margin, decision}]
def to_findings(image: str, regions: list[dict], verdicts: list[dict], concept_id: str, lane: str) -> list[dict]
    # Finding v1.0 for hide + nearMiss only; findingId f"f{i}-{regionId}"[:64], layer 2, scope "object"
# workshop/twin/run.py (1.3.1). The ONLY caller of 1.2's workshop/eval/score_screens.py
PieceFn = Callable[[Screen, Image.Image], tuple[list[dict], np.ndarray]]
def describer_pieces(desc: Describer, finder_boxes_fn=None, tiles=True) -> PieceFn   # variant A (C passes boxes)
def embed_set(screens, piece_fn: PieceFn, cache_key: str, use_cache=True) -> list[tuple[list[dict], np.ndarray, float]]
    # cache data/ch1/cache/<cache_key>/<image stem>.npz {regions json, vecs, sec}; sec = compute seconds
def score_findings(screens, findings_by_image: dict[str, list[dict]], concept_id: str) -> dict
    # -> {"recall", "precision", "cleanFalseCover"} (fractions 0..1) via 1.2 scorer
def run_set(set_name, split, concepts: list[str], variant="A", mode="balanced", out: Path | None = None,
            piece_fn: PieceFn | None = None, encoder: TextEncoder | None = None, lane="describer",
            ccs: dict[str, dict] | None = None, use_cache=True) -> dict
    # writes <out>/<concept>/<stem>.json (Finding array); returns {concept: scores, "secPerScreen": float}
    # split=="test" calls data.log_test_run first
def sweep(set_name, split, concept, variant, ccs, grid=[0.05, 0.10, ..., 0.95], **run_kw) -> list[dict]
    # cached vectors, balanced threshold overridden per t -> [{"t", "recall", "precision", "cleanFalseCover"}]
# CLI: python -m workshop.twin.run (--set S --split D | --images DIR) --concepts cats,spiders
#      [--variant A|C] [--mode balanced] [--out DIR] [--gallery] [--no-cache]  -> prints JSON scores
# workshop/twin/gallery.py (1.3.1)
def build_gallery(screens, findings_by_concept: dict[str, dict[str, list[dict]]], out_html: Path) -> Path
    # label boxes green, hide red, nearMiss orange; 360-px JPEG thumbs; per-screen TP/FP/FN line
# workshop/twin/finder.py (1.3.2)
MODELS = REPO/"data/models"; YOLOE_WEIGHTS = "yoloe-26s-seg.pt"
PROPOSAL_VOCAB = ["animal", "object", "toy", "drawing", "insect", "person", "food", "vehicle"]  # fixed, not the user list
class Finder:
    space_id: str           # e.g. "yoloe-26s-mobileclip2" (name of the real text encoder found in ultralytics source)
    text_model_id: str
    def __init__(self, weights=YOLOE_WEIGHTS) -> None
    def boxes(self, img) -> list[dict]           # Region dicts, source finder, kind object, objectness=conf;
                                                 # conf>=0.05, iou .5, imgsz 640, <=20 boxes, >=24x24 px
    def box_embeddings(self, img) -> tuple[list[dict], np.ndarray]   # variant B; raise NotImplementedError(reason)
    def embed_texts(self, texts) -> np.ndarray   # YOLOE's OWN text encoder (get_text_pe), L2-normalised
# workshop/twin/variants.py (1.3.2)
def compare(set_name, split, concepts) -> dict
    # {"rows":[{variant, concept, recall, precision, cleanFalseCover, t, secPerScreen, note}], "chosen", "reason"}
    # each row = sweep's best point: highest recall with cleanFalseCover <= 0.05 (raw p, offsets 0)
    # writes data/ch1/variants-<set>.json ; CLI prints a markdown table
```
Files written by 1.3.3: `calibration.json` = `{"version":1,"set","variant","concepts":{"cats":{"calibrationOffset","butNotExtra":[],"exampleThreshold":null}}}`;
`thresholds.json` = `{"version":1,"modes":{"light","balanced","strict"},"margin"}`;
`data/ch1/results-<set>.json` = `{variants, chosenVariant, calibration, thresholds, dev:{mode:{concept:scores}}, examples, newWord, listSwitch, test|null}`.

## 3. Sub-phases (all start at once)

### 1.3.1 Describer and Judge on whole pieces
- **Goal:** variant A end to end. Pieces, SigLIP2, Teacher v0, Judge v0, Finding JSON, scorer and gallery.
- **Owned paths:** `workshop/twin/{__init__,data,describer,pieces,teacher,judge,run,gallery}.py`, `workshop/twin/tests/test_twin_v0.py`,
  `tools/verify/1.3.1.ps1`, `pyproject.toml`, `uv.lock`.
- **Steps:** (1) read 1.2 SPEC §2 and wire `data.py` and `score_findings`; (2) implement §2 exactly; (3) run A on the
  synthetic dev split for cats and spiders with `--gallery`; (4) put the baseline table in your record.
- **Verify `tools/verify/1.3.1.ps1`:**
  - ruff on `workshop/twin`.
  - pytest `test_twin_v0.py`: cards for cats, spiders and snakes validate as Concept and CompiledConcept; Judge on toy
    vectors gives hide, nearMiss and leave, and the margin rule blocks a hide; pieces = 1 + 18 + 3 with all rects inside
    the image; Findings validate; `log_test_run` refuses a 4th run (temp log).
  - Describer smoke: `embed_texts` has shape (1, 768) and norm 1.
  - CLI `--set synthetic --split dev --concepts cats,spiders --variant A --gallery`: JSON has recall, precision and cleanFalseCover in [0,1] for both concepts, and the gallery `index.html` has at least 1 `<img>`.
  - The script ends with `VERIFY 1.3.1: PASS`.
- **Human needs:** none.

### 1.3.2 Add the object finder
- **Goal:** YOLOE boxes plus per-box fingerprints, compared with YOLOE's own text encoder. Score variants A, B and C, record speed and pick one.
- **Owned paths:** `workshop/twin/finder.py`, `workshop/twin/variants.py`, `workshop/twin/tests/test_finder.py`,
  `tools/verify/1.3.2.ps1`, `.gitignore` (add `*.pt`, `mobileclip*.ts`).
- **Steps:**
  1. Find which text encoder the checkpoint uses (grep `ultralytics/nn/text_model.py` and `tasks.py`) and set `space_id` from it.
  2. `boxes()`: `set_classes(PROPOSAL_VOCAB, get_text_pe(...))` once at init (runtime only, never an export).
  3. `box_embeddings()`: forward-hook the head's per-anchor visual embedding, i.e. the `cv3[i]` output after the contrastive head's BN,
     which is the vector the head dots with text. Flatten it in anchor order, keep the NMS-kept anchors (ultralytics nms
     `return_idxs=True` if present, else `torchvision.ops.nms` on the raw output) and L2-normalise. Stop after about 8 min: raise NotImplementedError(reason).
  4. Variants: A = `describer_pieces(d)`; B = `Finder.box_embeddings` + `compile_concept(card, finder)` + `lane="finder"`;
     C = `describer_pieces(d, finder_boxes_fn=f.boxes)`.
  5. Speed is mean `sec` from the uncached cache entries.
  6. `chosen` = the best recall at ≤5% clean false-cover, ties going to the faster variant. Write `reason`.
- **Verify `tools/verify/1.3.2.ps1`:**
  - ruff.
  - pytest `test_finder.py`: boxes are valid Regions; `embed_texts` dim equals the box-vector dim (or B skipped with its
    reason); **list switch:** one Finder and one Describer instance judge cats, then spiders, then bicycles, with the
    `id()` of both models unchanged and the weight files' sha256 the same before and after.
  - `python -m workshop.twin.variants --set synthetic --split dev --concepts cats,spiders` writes `variants-synthetic.json`
    with rows for A, B and C (B may be "not run: …"), numbers for C, and `chosen` set.
  - `git status --porcelain` shows no `*.pt` or `*.ts` file.
  - The script ends with `VERIFY 1.3.2: PASS`.
- **Human needs:** none.

### 1.3.3 Tune, analyse, decide
- **Goal:** per-concept calibration and mode thresholds, "but not" refinement, the example-photo gain, the one-command
  report and decision entry, and the proof-test tooling.
- **Owned paths:** `workshop/twin/{calibrate,report}.py`, `workshop/twin/calibration.json`, `workshop/twin/thresholds.json`,
  `workshop/twin/tests/test_calibrate.py`, `tools/ch1_see.ps1`, `tools/verify/1.3.3.ps1`, `docs/reports/ch1-see.md`, `docs/decisions.md`.
- **Steps (exact rules, using the `chosenVariant` from variants):**
  1. Offset: `offset_c = clip(0.5 - q95_c, -1, 1)`, where `q95_c` is the 95th percentile, over dev screens with no box of concept c, of each screen's max `p_raw`.
  2. Thresholds (grid 0.05..0.95, calibrated p, all tuned concepts together): Balanced = smallest t with cleanFalseCover
     ≤ 0.05 for every concept; Light = smallest t with ≤ 0.01; Strict = smallest t with ≤ 0.15; then enforce Strict ≤ Balanced ≤ Light.
  3. butNotExtra: for each ScreenLabel `lookalikes` tag that appears on at least 2 false-cover dev screens, add `"a {tag}"`, then re-sweep once.
  4. Examples: the centroid of 3-5 dev cat-box crops. exampleThreshold = the smallest grid t with clean false-cover ≤ 0.05. Gain = the change in Balanced recall on the remaining dev screens (DV-7). Keep it on only if gain > 0.
  5. New word "snakes" (never tuned): the card validates and the run goes end to end. Report its scores with no threshold.
  6. List switch: record the result of the 1.3.2 test in the report.
  7. `report.py --set S [--test] [--no-cache]` runs steps 1-6, writes `calibration.json`, `thresholds.json`, `results-<set>.json` and
     `docs/reports/ch1-see.md`, and writes the decision between `<!-- ch1-see:begin -->` and `<!-- ch1-see:end -->` in `docs/decisions.md`,
     replacing what is there, as D-<next>.
  8. Report headings: Score table (dev per mode, test if run) · Variants · Calibration and thresholds · Examples gain ·
     Unseen concept · List switch · Successes (10) · Failures (10) (image name + concept + reason) · Chosen models · Gate.
     Decision record: models and versions (torch 2.14.1 CPU, transformers 5.18.0, ultralytics 8.4.171, SigLIP2 HF commit sha,
     YOLOE file sha256), `spaceId`s, licences (SigLIP2 Apache-2.0, YOLOE AGPL-3.0, the text encoder's licence), thresholds,
     calibration, and "Gate: PENDING-HUMAN (real frozen test set); fallback rule per PLAN 1.3 'If rejected'".
  9. `tools/ch1_see.ps1 [-Set synthetic|real] [-Test] [-NoCache] [-Fresh <dir> -Concepts a,b]` wraps with-env.
     `-Fresh` runs `run --images <dir> --gallery` with `--out data/ch1/runs/fresh-<dir name>-<concepts>` and writes a `tally.md` template next to the gallery.
- **Verify `tools/verify/1.3.3.ps1`** (run after 1.3.1 and 1.3.2 have passed):
  - ruff.
  - pytest `test_calibrate.py` on stub data: offset formula, threshold ordering, decision block replaced (not duplicated).
  - `tools\ch1_see.ps1 -Set synthetic -Test`, then check: `calibration.json` and `thresholds.json` parse with Light ≥
    Balanced ≥ Strict; AC-1.3-04 ordering from the results JSON (recall and cleanFalseCover per concept); every step-8
    heading in the report; the decisions block has models, versions, spaceIds, licences, thresholds and calibration;
    `data/ch1/test-runs.jsonl` has ≤ 3 synthetic entries.
  - `-NoCache` re-run: every number in the results JSON is within 0.005 (±0.5 points) of the first run, with no `-Test` this time.
  - The `-Fresh` smoke runs on a folder of 3 synthetic images and `index.html` exists.
  - The script ends with `VERIFY 1.3.3: PASS`.
- **Human needs:** the real-set run and the proof test (§6).

## 4. Acceptance criteria
| AC id | Status | How checked | Threshold (PLAN, verbatim) |
| --- | --- | --- | --- |
| AC-1.3-01 | PENDING-HUMAN | `tools\ch1_see.ps1 -Set real -Test` after 1.2's real frozen test set exists (synthetic number is pipeline-only) | Balanced recall on the test set ≥ 90% |
| AC-1.3-02 | PENDING-HUMAN | same run | ≤ 5% of clean test screenshots get any wrong cover (Balanced) |
| AC-1.3-03 | PENDING-HUMAN | same run | Spiders: recall ≥ 80%, clean false-cover ≤ 5% |
| AC-1.3-04 | AUTO (synthetic dev) + PENDING-HUMAN (real dev) | 1.3.3 verify reads results JSON | On dev: recall Light ≤ Balanced ≤ Strict, and wrong covers Light ≤ Balanced ≤ Strict |
| AC-1.3-05 | AUTO | 1.3.2 list-switch test; report section "List switch" | Switching the list from cats to spiders to a new word needs no model change or re-export |
| AC-1.3-06 | AUTO (card + end to end) / PENDING-HUMAN (real score) | 1.3.1 card test; report "Unseen concept" | A word never used in tuning (for example "snakes") produces a valid concept card and runs end to end; its score is reported (no threshold) |
| AC-1.3-07 | AUTO (cached vs `-NoCache`) / DEFERRED (clean-checkout re-install) | 1.3.3 verify | One command regenerates every number in the report from a clean checkout, within ± 0.5 points |
| AC-1.3-08 | AUTO | `data.log_test_run` guard + `data/ch1/test-runs.jsonl` | The test set has been scored at most 3 times in total, each run logged |
| AC-1.3-09 | AUTO | 1.3.3 verify greps the decision block | Models, versions, `spaceId`s, licences, thresholds and calibration recorded |
| Ch1 gate | PENDING-HUMAN | same real run; decision block updated | at least **90% of cats are covered**, and **fewer than 5% of cat-free screenshots** get any wrong cover. Same check for a second concept (spiders) at no worse than 80% / 5%. |
| PT-1.3 | PENDING-HUMAN (PHONE) | §5 | The reviewer's tally is in line with AC-1.3-01 to AC-1.3-03, allowing for the small sample, and the new word needed no changes. |

Deferred to `progress/DEFERRED.md`:
- the AC-1.3-07 clean-checkout re-install and re-run;
- YOLOE medium;
- CUDA torch speed.

## 5. Proof test PT-1.3 "Fresh screenshots"
**Machine part (AUTO, in 1.3.3 verify):** `tools\ch1_see.ps1 -Fresh <dir> -Concepts cats,spiders` makes a gallery and a `tally.md` template from any folder.

**Human part (about 45 min):**
1. Connect the iQOO and check `adb devices`. On the test accounts, scroll live feeds and take 30 screenshots: 10 with cats, 5 with spiders,
   15 without (include dogs, foxes or text saying "cat" if you see them). About 20 min.
2. `adb pull` the screenshots (usually `/sdcard/DCIM/Screenshots/` or `/sdcard/Pictures/Screenshots/`) into
   `D:\iqoo finale\veil\data\ch1\fresh\<yyyy-mm-dd>\`.
3. From `D:\iqoo finale\veil`, run:
   - `powershell -NoProfile -ExecutionPolicy Bypass -File tools\ch1_see.ps1 -Fresh data\ch1\fresh\<date> -Concepts cats,spiders`
   - the same command with `-Concepts bicycles`.
   About 5 min.
4. Someone who did not build it opens both `index.html` galleries and fills `tally.md`. Per screenshot: covered correctly / wrong cover / missed.
   Note small, cartoon and partly visible cases. About 15 min.
5. **Pass when:** the tally is in line with AC-1.3-01 to 03 (allowing for the small sample), there are no dog, fox or "cat"-text covers, and bicycles needed no code or model change.

## 6. Human items (paste into HUMAN_CHECKS.md)
- [ ] HC-1.3-a **Real gate run** (after 1.2's real labelled set is frozen, about 10 min):
  `powershell -NoProfile -ExecutionPolicy Bypass -File tools\ch1_see.ps1 -Set real -Test`.
  Then record AC-1.3-01/02/03, the real-dev AC-04, and the Chapter 1 gate. If the gate fails, apply the PLAN fallback (cats ≥ 85%, clean false-cover ≤ 5%).
  This uses 1 of the 3 allowed test runs.
- [ ] HC-1.3-b **PT-1.3 Fresh screenshots** on the iQOO plus an independent reviewer's tally (§5, about 45 min).
- [ ] HC-1.3-c **Gallery review** from a user's point of view (verifier D): open `data/ch1/gallery/<run>/index.html` and note repeated false covers (about 10 min).
- [ ] HC-1.3-d **FYI licences:** YOLOE is AGPL-3.0, and the YOLOE text encoder (MobileCLIP family) is Apple research-only if that is what the decision record shows. Fine for the demo; review before any commercial use.
