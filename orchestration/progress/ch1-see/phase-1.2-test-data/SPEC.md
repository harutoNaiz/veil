MODEL: claude-opus-5-5
# SPEC: Phase 1.2 "Test data (ground truth)"
Status: APPROVED (orchestrator 08:14) · PLAN lines used: 226-234 (chapter intro), 341-437 (Phase 1.2) · Entry: Phase 1.1 built (ScreenLabel/Finding/Rect schemas exist).
Scope: build ALL tooling and prove it end to end on a small SYNTHETIC set. Real 300 screenshots, labels, review and freeze are Human.

## 1. Deviations and risks
- **DV-1 (Human):** real collection, labelling, second-person review and the real freeze need the phone + test accounts (HC-004 open). Rows AC-1.2-01/02/03 and the real-data halves of 04/05/07 are PENDING-HUMAN; tooling is AUTO-verified on synthetic data.
- **DV-2:** "team members' own accounts" (PLAN) becomes **team-owned test accounts** (ground rule 6: test accounts only). Sidecar `source` = the account id (e.g. `test-acct-A`), checked against an allowlist `data/screens/sources.txt` the human maintains.
- **DV-3:** Label Studio is never installed in the uv env or uv.lock. `tools/label-studio.ps1` runs it on demand via `uvx`; first launch (download) is a Human step. No CVAT.
- **DV-4:** picture hash = our own dHash (Pillow + numpy, both already locked). No new dependency (no `uv add` needed in this phase).
- **DV-5:** labels file `data/labels/screens.json` is a JSON **array** of ScreenLabel v1.0 objects; predictions are a JSON array of Finding v1.0 objects with `image` set; only `decision == "hide"` counts as a cover.
- **DV-6:** "cat-emoji" / "cat-text" are boxes with `concept: "cats"` and `tag` set (contract has no separate concept). The scorer counts them by default; `--ignore-tag` lets later phases "decide later" (PLAN 1.2.2 step 1).
- **Risk:** dHash on whole screenshots can cluster different screens of one app (same chrome). Effect is only on split balance; split report shows it. Threshold is a constant, tunable on real data without touching test-set rules.
- **Risk:** small app×concept groups on real data can miss ±5 points; split tool fails loudly and the human re-collects (PLAN "If rejected").
- **Deferred:** none heavy. Label Studio first-launch download (> 5 min) is Human, not Deferred.

## 2. Shared interfaces (all three Builders code against these from minute 0)
Python 3.11, run via `uv run`. Validate with `workshop.contracts.validate.validate(type_name, obj)` (type names `"ScreenLabel"`, `"Finding"`); pydantic models in `workshop.contracts.models` (`ScreenLabel`, `ScreenLabelMeta`, `Finding`, `Rect`). Rect is `{"x","y","w","h"}` ints. Never import across sub-phase packages (each writes its own 5-line IoU if needed).

**Files on disk** (all under git-ignored `data/`):
- `data/screens/<app>-<surface>-<NNNN>.png` (name matches `^[a-z0-9-]+-\d{4}\.png$`) + sidecar `<same stem>.json`:
  `{"app":"instagram","surface":"explore","mode":"dark","orientation":"portrait","source":"test-acct-A","capturedAt":"2026-10-02T10:00:00Z"}`
  The first five keys are exactly `ScreenLabelMeta`; converters copy only those five into `ScreenLabel.meta`.
- `data/screens/sources.txt`: one allowed source id per line (`#` comments).
- `data/labels/screens.json`: array of ScreenLabel (one per PNG). `data/labels/splits.json`:
  `{"seed":12,"hashBits":256,"maxDist":20,"dev":["a.png",...],"test":[...],"clusters":[["a.png","a-dup.png"],...]}`
- Synthetic sets: `data/synth/<owner>/` with the same layout (`*.png`, sidecars, `sources.txt`, `truth.json` = labels array).

**Vocabulary (constants, copy verbatim):** concepts `cats`, `spiders`. Label Studio rectangle labels → (concept, default kind, tag):
`cats→(cats,photo,-)`, `cat-emoji→(cats,emoji,cat-emoji)`, `cat-text→(cats,text,cat-text)`, `spiders→(spiders,photo,-)`, `spider-emoji→(spiders,emoji,spider-emoji)`.
Lookalike choices: `dog, fox, lion, tiger, stuffed-toy, cat-logo, crab, other`. Apps: `instagram, youtube, chrome, whatsapp, x, reddit`.

**Derived image classes (used by counts and split):** `cats` = any box concept cats with tag != cat-text; `spiders` = any box concept spiders; `clean` = `clean == true`; `hard` = `lookalikes` non-empty or any box tag `cat-text`. Primary class for stratifying = cats, else spiders, else clean.

**CLIs (module entry points, exit 0 ok / 1 check failed / 2 bad input / 3 no device):**
- 1.2.1 `python -m workshop.screens.capture --app A --surface S --mode dark|light --source ID [--count 10] [--scroll-fraction 0.6] [--pause 1200] [--out data/screens] [--serial S]`
- 1.2.1 `python -m workshop.screens.synth --out DIR [--n 75] [--near-dupes 2] [--seed 7]` → PNGs + sidecars + `sources.txt` + `truth.json`
- 1.2.1 `python -m workshop.screens.meta_check --screens DIR` (sidecars valid, source allowlisted, `data/` not tracked by git)
- 1.2.2 `python -m workshop.labels.ls_convert to-ls --screens DIR --url-prefix P [--prelabels FINDINGS_OR_LABELS.json] --out tasks.json`
- 1.2.2 `python -m workshop.labels.ls_convert from-ls --export ls.json --screens DIR --labeller ID [--accept-predictions] --out labels.json`
- 1.2.2 `python -m workshop.labels.check --labels L --screens DIR`
- 1.2.2 `python -m workshop.labels.agree sample --labels L --fraction 0.2 --seed N --out names.txt` and `agree compare --official L --blind B [--out report.json]`
- 1.2.3 `python -m workshop.eval.split --labels L --screens DIR --seed 12 --out splits.json` (prints split report; exit 1 if any group off ±5 points or a cross-split near-dupe)
- 1.2.3 `python -m workshop.eval.dupes --screens DIR --splits splits.json` (exit 1 if a near-dupe pair straddles dev/test)
- 1.2.3 `python -m workshop.eval.freeze write|check --screens DIR --labels L --splits S --doc docs/datasets.md`
- 1.2.3 `python -m workshop.eval.counts --labels L [--require]`
- 1.2.3 `python -m workshop.eval.fake_preds perfect|empty|mistakes --labels L [--seed N] --out preds.json`
- 1.2.3 `python -m workshop.eval.score_screens --labels L --preds P [--splits S --split dev|test] [--ignore-tag T]... [--out score.json]`

**Scorer output (exact shape):**
`{"images":N,"cleanImages":K,"cleanFalseCover":float,"droppedPredictions":n,"concepts":{"cats":{"labels":n,"hit":n,"covers":n,"correctCovers":n,"recall":float|null,"precision":float|null,"cleanFalseCover":float}}}`

**Verify scripts:** `tools/verify/1.2.N.ps1`; start with `. "$PSScriptRoot\..\env.ps1"`, `Set-Location` repo root, run each check via `uv run ...`, print one line per check, end with exactly `VERIFY 1.2.N: PASS` (exit 0) or `VERIFY 1.2.N: FAIL` (exit 1). Each also runs `uv run ruff check <owned python paths>`. Run as: `powershell -NoProfile -ExecutionPolicy Bypass -File tools\verify\1.2.N.ps1` from `D:\iqoo finale\veil`.

## 3.1 Sub-phase 1.2.1 Collect screenshots (capture + synthetic generator)
**Goal:** one command per surface captures scroll-by-scroll screenshots with correct sidecars; a synthetic generator gives every tool a known-truth set.
**Owned paths:** `workshop/screens/**`, `tools/verify/1.2.1.ps1`, `data/synth/1.2.1/` (scratch).
**Files:** `workshop/screens/__init__.py`, `capture.py`, `synth.py`, `meta_check.py`, `tests/test_capture.py`, `tests/test_synth.py`, `tests/test_meta_check.py`.
**Key signatures:**
- `capture.capture(serial: str, out: Path, app: str, surface: str, mode: str, source: str, count: int, scroll_fraction: float, pause_ms: int) -> list[Path]` — per shot: `adb.screencap` to next free `<app>-<surface>-NNNN.png`, orientation from PNG size (w > h → landscape), write sidecar, then `drive.scroll(serial, times=1, fraction=scroll_fraction, pause_ms=pause_ms)`. Validate app/surface against `^[a-z0-9-]+$`, mode in {dark, light}, source in `sources.txt` (create the file with the given id if absent and print a notice).
- `main()` → no device: print `no adb device (connect the phone: HC-002)`, exit 3 (same as `drive.py`).
- `synth.generate(out: Path, n: int = 75, near_dupes: int = 2, seed: int = 7) -> list[dict]` (returns the ScreenLabel list it also writes to `truth.json`).
- `meta_check.check(screens: Path) -> list[str]` (problems; empty = ok).
**Synthetic content (harmless, procedural, Pillow only, 360×780 portrait; every 15th image 780×360 landscape):** feed of 2-4 random-height "post" cards on a light or dark ground (every 3rd image dark → ≥ 20%). Stand-ins: **cat** = orange circle + two triangle ears; **spider** = black circle + 8 legs; **dog** (lookalike, unlabelled) = brown circle + two hanging rectangle ears; **cat-emoji** = small yellow circle with ears (16-24 px). Balanced so splitting is exact: `app = APPS[i % 5]` (first five apps), `class = ["cats","spiders","clean"][(i // 5) % 3]` → 75 images = 5 per app×class. Cat images: 1-3 cat boxes (one in five also a cat-emoji box); spider images: 1-2 spider boxes; clean images: no boxes, every 2nd one has a dog (`lookalikes:["dog"]`). Box rect = tight bounds of the drawn shape; `scope` alternates object / wholeElement (wholeElement boxes also carry `postRect`). Boxes on one image never overlap (each shape in its own card). Near-dupes: copies of images 0..k-1 shifted 2 px with ±3 noise, named `<stem>-dup.png`, same truth. `source: "synth"` (written to `sources.txt`), `labeller: "synth"`. Must run in < 10 s.
**Steps:** write synth → tests; write capture with an injected fake adb (monkeypatch `workshop.bench.adb.screencap/screen_size/swipe`, `single_device`) → tests; meta_check → tests; verify script.
**Verify `tools/verify/1.2.1.ps1` checks:** (1) `pytest workshop/screens -q` green: capture with fake adb writes 3 PNG+sidecar pairs with right names/orientation and calls swipe 3 times; capture refuses bad mode/app; synth output: 75+2 PNGs, every truth entry validates as ScreenLabel, width/height match PNG, class counts 25/25/25, ≥ 20% dark, 5 apps; meta_check flags a missing sidecar and an un-allowlisted source. (2) CLI `synth --out data/synth/1.2.1 --n 75 --near-dupes 2` succeeds. (3) CLI `meta_check --screens data/synth/1.2.1` exit 0. (4) CLI `capture ...` with no phone exits 3. (5) `git check-ignore -q data/screens/x.png` succeeds and `git ls-files data` lists only `data/README.md`. (6) ruff. Ends `VERIFY 1.2.1: PASS`.
**Human needs:** phone + test accounts (HC-004) to capture the real ~300 (section 6).

## 3.2 Sub-phase 1.2.2 Label them (Label Studio config, converters, rules, agreement)
**Goal:** a human can label in Label Studio and get a contract-valid `screens.json`; a second labeller's work can be compared automatically.
**Owned paths:** `workshop/labels/**`, `docs/labelling-rules.md`, `tools/label-studio.ps1`, `tools/verify/1.2.2.ps1`, `data/synth/1.2.2/`.
**Files:** `workshop/labels/__init__.py`, `ls_config.xml`, `ls_convert.py`, `check.py`, `agree.py`, `tests/fixtures/ls-export-mini.json` (hand-written, 3 tasks), `tests/test_ls_convert.py`, `tests/test_check.py`, `tests/test_agree.py`.
**ls_config.xml:** `<Image name="image" value="$image"/>`; `<RectangleLabels name="box" toName="image">` with the five labels of section 2; per-region `<Choices name="kind" perRegion="true">` (photo, cartoon, drawing, sticker, emoji, text, other) and `<Choices name="scope" perRegion="true">` (object, wholeElement); per-image `<Choices name="clean">` (clean) and `<Choices name="lookalikes" choice="multiple">` (section 2 list).
**Conversion rules (from-ls):** use `annotations[-1].result` (or `predictions[-1].result` with `--accept-predictions` when no annotation). Rectangle `value.{x,y,width,height}` are percents of `original_width/height`: `x_px = round(x/100*W)`, `w_px = max(1, round(width/100*W))`, same for y/h. Per-region choices join to the rectangle by equal `id`. Kind = region choice else label default; scope default `object`. Image name from `data.name` (to-ls writes it). Width/height read from the PNG; meta from the sidecar's five keys. No boxes + clean ticked → `clean:true`; boxes + clean ticked, or no boxes + clean not ticked → exit 2 listing the image ("unlabelled or contradictory"). Output validated with `validate("ScreenLabel", ...)`, sorted by image.
**to-ls:** one task per PNG `{"data":{"image": P + name, "name": name}}`; with `--prelabels` (a ScreenLabel array or a Finding array, auto-detected) add `"predictions":[{"model_version":"prelabel","result":[...]}]` in the same result format (this is the optional pre-label hook).
**check.py (AC-1.2-02 tool):** every PNG has exactly one entry; every entry has a PNG; each validates; width/height match the PNG; meta present. Prints `LABELS OK <n>` or one line per problem (exit 1).
**agree.py (AC-1.2-03 tool):** `sample` picks `ceil(fraction × n)` names with the seed. `compare` over images in both files: per image and concept, greedy one-to-one pairing by highest IoU (> 0); `items = pairs + unmatched_official + unmatched_blind`; `disagreements = pairs with IoU < 0.5 + unmatched_official + unmatched_blind`; `rate = disagreements / max(items, 1)`; `coverage = |blind ∩ official| / |official|`. Report `{"images","coverage","items","disagreements","rate","pass"}` with `pass = coverage >= 0.20 and rate <= 0.05`; exit 0 if pass else 1.
**tools/label-studio.ps1 (Human run only, never by the Builder):** sets `LABEL_STUDIO_BASE_DATA_DIR=<veil>\data\label-studio`, `LABEL_STUDIO_LOCAL_FILES_SERVING_ENABLED=true`, `LABEL_STUDIO_LOCAL_FILES_DOCUMENT_ROOT=<veil>\data`, then `uvx --python 3.11 label-studio start --port 8080 --no-browser`. Comment block: the 6 human steps of section 6 item 2.
**docs/labelling-rules.md:** PLAN 1.2.2 rules: box every cat/spider ≥ 30% visible; cartoons, drawings, stickers count; 🐱 → label `cat-emoji`; the word "cat" → `cat-text`; scope wholeElement vs object; clean must be ticked explicitly; tick every lookalike present; box = tight around visible part; one box per animal. A "Changes" log section for rule updates after review.
**Verify `tools/verify/1.2.2.ps1` checks:** (1) `pytest workshop/labels -q` green: mini export → exact expected ScreenLabel list (percent→px, kind/scope join, clean, lookalikes, emoji tag); contradictory/unlabelled → exit 2; round trip labels→to-ls(prelabels)→from-ls `--accept-predictions` equals input within ±1 px; check.py flags missing entry, size mismatch, invalid entry; agree: identical → rate 0 and pass; 1 missing box of 20 items → rate 0.05 pass; 2 of 20 → 0.10 fail; a pair at IoU 0.49 → disagreement; coverage < 0.2 → fail. (2) `ls_config.xml` parses (xml.etree) and its label/choice names equal the converter constants. (3) rules doc exists and contains `30%`, `cat-emoji`, `cat-text`, `wholeElement`. (4) `tools/label-studio.ps1` parses (`[scriptblock]::Create`) without running. (5) ruff. Ends `VERIFY 1.2.2: PASS`.
**Human needs:** run Label Studio, label ~300, second labeller re-labels ≥ 20% (section 6).

## 3.3 Sub-phase 1.2.3 Split, freeze and score
**Goal:** fair frozen split with a tamper-evident checksum, a near-dupe check, a count report, and a scorer proven on perfect/empty/hand-worked cases.
**Owned paths:** `workshop/eval/**`, `docs/datasets.md`, `tools/verify/1.2.3.ps1`, `tools/verify/pt-1.2.ps1`, `data/synth/1.2.3/`, `data/synth/pt/`.
**Files:** `workshop/eval/__init__.py`, `score_screens.py`, `split.py`, `dupes.py`, `freeze.py`, `counts.py`, `fake_preds.py`, `tests/test_score_screens.py`, `tests/test_split_dupes.py`, `tests/test_freeze.py`, `tests/test_counts.py`, `tests/test_frozen_real.py`.
**Key signatures:** `score_screens.iou(a: dict, b: dict) -> float`, `contains_frac(cover: dict, label: dict) -> float` (= area(cover ∩ label) / area(label)), `hits(cover, label) -> bool` (= `iou >= 0.3 or contains_frac >= 0.7`, both inclusive), `score(labels: list[dict], findings: list[dict], ignore_tags: frozenset[str] = frozenset()) -> dict`; `dupes.dhash(path: Path, hash_size: int = 16) -> int` (grayscale, resize to 17×16, compare adjacent columns → 256 bits), `dupes.clusters(paths, max_dist: int = 20) -> list[list[str]]`; `split.split(labels, screens: Path | None, seed: int) -> dict`; `freeze.checksum(screens, labels, test_names) -> str`.
**Scoring rules (frozen metric definitions):** evaluated images = label entries (restricted to `--split` if given). Covers = findings with `decision == "hide"` and `image` in the evaluated set (others counted in `droppedPredictions`; a finding failing `validate("Finding")` or lacking `image` → exit 2). Per concept: `recall = labels hit by ≥ 1 same-concept cover / labels` (null if 0 labels); `precision = covers hitting ≥ 1 same-concept label / covers` (null if 0 covers); `cleanFalseCover = clean images with ≥ 1 cover of that concept / clean images`. Overall `cleanFalseCover` = clean images with any cover / clean images. Labels with an ignored tag leave the recall denominator; covers hitting only ignored labels leave the precision denominator.
**Hand-worked 5-image case (put in the unit test verbatim; all rects x,y,w,h; all decisions hide unless noted):**
- s1 (cats A=0,0,100,100; B=200,0,100,100) · s2 (cats C=0,0,100,100; lookalikes dog) · s3 (spiders D=0,0,50,50) · s4 clean · s5 clean.
- p1 cats s1 0,0,100,100 (hits A, IoU 1) · p2 cats s1 150,-50,250,250 (hits B by containment 1.0, IoU 0.16) · p3 cats s2 60,60,100,100 (miss: IoU 0.087, contain 0.16) · p4 spiders s3 0,0,40,50 (hit, IoU 0.8) · p5 cats s4 10,10,50,50 (clean cover) · p6 cats s5 0,0,10,10 decision **leave** (ignored).
- Expected exactly: cats labels 3, hit 2, recall 2/3, covers 4, correctCovers 2, precision 0.5, cleanFalseCover 0.5; spiders labels 1, hit 1, recall 1.0, covers 1, precision 1.0, cleanFalseCover 0.0; overall cleanFalseCover 0.5, cleanImages 2.
- Boundary test: label 0,0,100,100 vs cover 0,0,30,100 → IoU exactly 0.3 → hit; cover 0,0,25,100 → no hit.
**Split rules:** cluster near-dupes first (whole cluster goes to one side); stratum = (app, primary class); within each stratum shuffle clusters with the seed and fill test up to `round(0.4 × stratum size)`. Report dev share per concept class (cats, spiders, clean) and per app; fail (exit 1) if any share is outside 60 ± 5 points or any cluster spans both sides. Without `--screens` (tests only) skip clustering.
**freeze.py:** checksum = sha256 of sorted lines `"<name>\t<sha256(png bytes)>\t<sha256(json.dumps(label, sort_keys=True, separators=(",",":")))>\n"` over the test images. `write` replaces the block between `<!-- veil:testset -->` and `<!-- /veil:testset -->` in the doc with: test image count, dev count, seed, `checksum: sha256:<hex>`, date. `check` recomputes; mismatch → print `TEST SET CHANGED`, exit 1.
**docs/datasets.md (committed template):** split method, seed 12, dHash 256-bit / max distance 20, checksum recipe, scoring rules above, and the block with `checksum: PENDING-HUMAN`. `tests/test_frozen_real.py` runs `freeze check` on real `data/` and the doc; skips if the doc says PENDING-HUMAN or `data/labels/screens.json` is missing (this is the AC-1.2-05 checksum test once frozen).
**counts.py:** prints total, cats, spiders, clean, hard, distinct apps, dark share, landscape count, each with its AC-1.2-01 threshold and OK/LOW; `--require` → exit 1 if any LOW.
**fake_preds.py:** `perfect` = one hide Finding per label box (rect = box rect, conceptId = concept, scope = box scope, layer 2, lane finder, probability 1.0, lookId 0, tMs 0, findingId `f-<n>`, image); `empty` = `[]`; `mistakes` = perfect minus 2 cat boxes (seeded), plus 1 cats cover 0,0,50,50 on a clean image with `dog` lookalike, plus 1 cats cover 0,0,50,50 on a different clean image without lookalikes.
**Verify `tools/verify/1.2.3.ps1` checks:** (1) `pytest workshop/eval -q` green: perfect → recall 1.0, precision 1.0, clean false-cover 0 for both concepts; empty → recall 0, false-cover 0; hand-worked case exact; boundary; dhash: an image vs its 2 px-shifted noisy copy ≤ 20, two different random images > 20; split on a balanced 75-entry fixture → every concept and app within 60 ± 5 and dupes on one side; freeze write→check ok, edit a test label → check fails, edit a dev label → still ok; counts on a fixture exact. (2) ruff. Ends `VERIFY 1.2.3: PASS`.
**Human needs:** run split + freeze on the real set and commit `docs/datasets.md` (section 6).

## 4. Acceptance criteria
| AC | Type | How checked | Pass threshold (PLAN, verbatim) |
| --- | --- | --- | --- |
| AC-1.2-01 | HUMAN (count tool AUTO on synthetic) | `workshop.eval.counts --require` on real labels + second-person spot check | ≥ 300 screenshots: ≥ 100 with cats, ≥ 50 with spiders, ≥ 150 clean, ≥ 30 hard lookalikes, ≥ 5 apps, ≥ 20% dark mode |
| AC-1.2-02 | HUMAN (validator AUTO on synthetic) | `workshop.labels.check` on real labels | 100% of screenshots have a label entry; clean ones are explicitly marked clean; every entry validates against the contract |
| AC-1.2-03 | HUMAN (comparison tool AUTO on synthetic) | `workshop.labels.agree compare` official vs blind | A second person independently re-labels ≥ 20%; disagreement ≤ 5%. A missing box, an extra box, or overlap < 0.5 counts as a disagreement |
| AC-1.2-04 | AUTO on synthetic (1.2.3 verify, PT machine) + HUMAN on real | `workshop.eval.split` report + `workshop.eval.dupes` | Dev/test is 60/40 (± 5 points) for each concept and each app; no near-duplicate screenshot appears in both |
| AC-1.2-05 | AUTO on synthetic + HUMAN (real freeze) | `freeze check`; tamper test; `test_frozen_real.py` | Test-set checksum recorded; any change to the test set makes a check fail |
| AC-1.2-06 | AUTO | `tests/test_score_screens.py` via 1.2.3 verify | Perfect predictions give recall 1.0, precision 1.0 and clean false-cover 0; empty predictions give recall 0 and false-cover 0; a 5-image hand-worked case matches exactly |
| AC-1.2-07 | AUTO tooling (1.2.1 verify) + HUMAN (real sources) | `workshop.screens.meta_check`; `git ls-files data` | Every screenshot comes from a team member's own account, with its source recorded; nothing in `data/` is pushed |

## 5. Proof test PT-1.2 "Blind label audit"
**Machine part (AUTO, after all three Builders):** `tools/verify/pt-1.2.ps1` (owned by 1.2.3, written against section 2 CLIs; the orchestrator runs it once all three verifies pass): synth 75 + 2 dupes into `data/synth/pt` → `labels.check` on truth (OK) → to-ls with truth as prelabels → from-ls `--accept-predictions` → `agree compare` vs truth: rate 0 → copy with 1 box dropped: rate = 1/items as computed → `split` (exit 0) → `dupes` (exit 0, dupes on one side) → `freeze write` to a temp doc → `check` ok → tamper one test PNG byte → `check` exit 1 → `fake_preds` perfect/empty/mistakes → `score_screens` each; mistakes must give cats `recall = (C-2)/C`, `precision = (C-2)/C`, overall `cleanFalseCover = 2/K` (C = cat labels, K = clean images, both read from truth), spiders recall 1.0 → `counts` prints. Ends `PT-1.2 MACHINE: PASS`.
**Human part (verifier ≠ labeller; about 2 h, after the real set is labelled and frozen):**
1. `uv run python -m workshop.labels.agree sample --labels data/labels/screens.json --fraction 0.1 --seed <your pick> --out data/labels/pt-sample.txt` (30 of 300); load only those in a fresh Label Studio project, no predictions; label blind (~40 min); export; `from-ls` → `data/labels/pt-blind.json`.
2. `agree compare --official data/labels/screens.json --blind data/labels/pt-blind.json --out data/evidence/1.2/pt-agree.json` → disagreement ≤ 5% (AC-1.2-03).
3. Hand-make three Finding files on 5-10 real test images (~30 min): perfect, empty, mistakes (2 missed cats, 1 cover on a dog, 1 cover on a clean screenshot). Write the expected recall/precision/clean false-cover by hand on paper first.
4. Run `score_screens` on each; numbers must match the hand calculation exactly (AC-1.2-06).
5. Run `split` and `dupes` on the real set: exit 0 (AC-1.2-04). Save outputs + hand calculation in `data/evidence/1.2/` and summarise in `docs/acceptance/1.2.md`.

## 6. Human items (ready to paste into HUMAN_CHECKS.md)
```
HC-1.2 Phase 1.2 real test data (blocked on HC-004 test accounts; est. 8-10 h total, can be split)
[ ] 1. Collect (~2.5 h): phone connected, test accounts logged in. Add each account id to data\screens\sources.txt.
       Per surface: uv run python -m workshop.screens.capture --app instagram --surface explore --mode dark --source test-acct-A --count 10
       Cover Instagram feed/reels/explore/profile/DMs, YouTube home/playing, Chrome news/image search, WhatsApp chat, X or Reddit.
       Targets: >=100 cats, >=50 spiders, >=150 clean, >=30 lookalikes (dog, fox, lion, stuffed toy, cat logo, word "cat"), >=20% dark, a few landscape.
       Then: uv run python -m workshop.screens.meta_check --screens data\screens  -> exit 0
[ ] 2. Label (~5 h): powershell -File tools\label-studio.ps1 (first run downloads Label Studio). In the browser: create project,
       paste workshop\labels\ls_config.xml as labelling config, add local storage path <veil>\data\screens, import tasks from
       uv run python -m workshop.labels.ls_convert to-ls --screens data\screens --url-prefix "/data/local-files/?d=screens/" --out data\labels\ls-tasks.json
       Label every image per docs\labelling-rules.md (tick "clean" on clean ones). Export JSON -> data\labels\ls-export.json, then
       uv run python -m workshop.labels.ls_convert from-ls --export data\labels\ls-export.json --screens data\screens --labeller labeller-a --out data\labels\screens.json
       uv run python -m workshop.labels.check --labels data\labels\screens.json --screens data\screens   -> LABELS OK
       uv run python -m workshop.eval.counts --labels data\labels\screens.json --require                  -> all OK (AC-1.2-01)
[ ] 3. Second person (~1.5 h): agree sample --fraction 0.2 -> blind-label those in a fresh project -> from-ls -> data\labels\blind.json
       agree compare --official data\labels\screens.json --blind data\labels\blind.json -> pass (AC-1.2-03). Fix disagreements, update rules "Changes".
       Second person also spot-checks the counts (PLAN 1.2.1 "Done when").
[ ] 4. Split and freeze (~5 min): uv run python -m workshop.eval.split --labels data\labels\screens.json --screens data\screens --seed 12 --out data\labels\splits.json
       uv run python -m workshop.eval.freeze write --screens data\screens --labels data\labels\screens.json --splits data\labels\splits.json --doc docs\datasets.md
       Commit docs\datasets.md only (never data\). After this the test set never changes.
[ ] 5. Proof test human part: SPEC.md section 5 steps 1-5 (~2 h, verifier is not the main labeller).
```
