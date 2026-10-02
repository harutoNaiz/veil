# Datasets: the screenshot test set (Phase 1.2)

The real screenshots, labels and splits live in the git-ignored `data/` folder and are never committed. This file records how the test set is split and frozen, and holds its checksum.

## Split method

- Labels file: `data/labels/screens.json` (array of ScreenLabel v1.0). Split file: `data/labels/splits.json`.
- Seed: **12**. Tool: `uv run python -m workshop.eval.split --labels data\labels\screens.json --screens data\screens --seed 12 --out data\labels\splits.json`.
- Near-duplicate screenshots are found first with a 256-bit dHash (grayscale, resized to 17 x 16, one bit per adjacent column pair), **maximum distance 20 bits**. A whole cluster goes to one side.
- Stratum = (app, primary class), where the primary class is cats, else spiders, else clean. Inside each stratum the clusters are shuffled with the seed and test is filled up to `round(0.4 x stratum size)`.
- The split passes only if the dev share of every concept class (cats, spiders, clean) and every app is 60 +/- 5 points and no cluster spans dev and test (AC-1.2-04). `uv run python -m workshop.eval.dupes --screens data\screens --splits data\labels\splits.json` re-checks the near-duplicates.

## Freeze recipe

The checksum is the sha256 of the sorted lines `"<name>\t<sha256(png bytes)>\t<sha256(json.dumps(label, sort_keys=True, separators=(",",":")))>\n"` over the **test** images. Any change to a test PNG, a test label, or the list of test images changes it; dev labels may still change.

- Freeze: `uv run python -m workshop.eval.freeze write --screens data\screens --labels data\labels\screens.json --splits data\labels\splits.json --doc docs\datasets.md`
- Check: the same command with `check`; a mismatch prints `TEST SET CHANGED` and exits 1.
- `workshop/eval/tests/test_frozen_real.py` runs the check on the real data and skips while the block below says `PENDING-HUMAN`.

## Scoring rules (frozen metric definitions)

`uv run python -m workshop.eval.score_screens --labels L --preds P [--splits S --split dev|test] [--ignore-tag T]`

- Evaluated images are the label entries (restricted to the chosen split). A cover is a Finding with `decision == "hide"` whose `image` is in that set; other findings are counted in `droppedPredictions`.
- A cover **hits** a label box when `IoU >= 0.3` or `area(cover ∩ label) / area(label) >= 0.7` (both inclusive).
- Per concept: `recall` = labels hit by at least one cover of that concept / labels (null if none); `precision` = covers hitting at least one label of that concept / covers (null if no covers); `cleanFalseCover` = clean images with at least one cover of that concept / clean images. The overall `cleanFalseCover` counts a cover of any concept.
- Labels with an ignored tag leave the recall denominator; covers that hit only ignored labels leave the precision denominator.
- `cat-emoji` and `cat-text` boxes are `cats` boxes with that tag; they count by default and `--ignore-tag` lets a later phase decide otherwise.

## Frozen test set

<!-- veil:testset -->
- test images: PENDING-HUMAN
- dev images: PENDING-HUMAN
- seed: 12
- checksum: PENDING-HUMAN
- frozen: PENDING-HUMAN
<!-- /veil:testset -->
