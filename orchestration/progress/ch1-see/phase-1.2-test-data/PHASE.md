# Phase 1.2 Test data (ground truth) · WAITING_HUMAN
Updated: 2026-10-02 08:38 · Commits: f89482a (1.2.2), f335014 (1.2.3), d6531ad (1.2.1) · Spec: SPEC.md (144 lines, APPROVED) · Phase time: about 30 min (08:06 → 08:36)

## Summary
All the tooling for real test data exists and is proven end to end on a generated set of 77 harmless "feed" screenshots:
- capturing screenshots from the phone;
- labelling in Label Studio and converting to the contract;
- checking labels and measuring agreement between two labellers;
- a fair dev/test split with a near-duplicate check;
- a tamper-evident freeze;
- the scorer, proven correct on perfect, empty and hand-worked cases.

The real ~300 screenshots and their labels are human work (HC-012).

## Sub-phases
| Sub-phase | Status | Verify | Commit |
| --- | --- | --- | --- |
| 1.2.1 Collect screenshots (capture, synth generator, meta check) | VERIFIED | `VERIFY 1.2.1: PASS` | d6531ad |
| 1.2.2 Label them (LS config, converters, check, agreement, rules) | VERIFIED | `VERIFY 1.2.2: PASS` | f89482a |
| 1.2.3 Split, freeze and score | VERIFIED | `VERIFY 1.2.3: PASS` | f335014 |

## Acceptance criteria
| AC | Result | Note |
| --- | --- | --- |
| AC-1.2-01 Enough material | PENDING-HUMAN | count tool works (synthetic run prints LOW, as expected) |
| AC-1.2-02 Everything labelled | PENDING-HUMAN | `labels.check` proven on synthetic |
| AC-1.2-03 Labels trustworthy | PENDING-HUMAN | `agree compare` proven (rate 0, then 1/items with one box dropped) |
| AC-1.2-04 Fair split | AUTO PASS on synthetic · real PENDING-HUMAN | split within 60 ± 5, dupes on one side |
| AC-1.2-05 Test set frozen | AUTO PASS on synthetic · real PENDING-HUMAN | freeze write → check ok → tamper → check fails |
| AC-1.2-06 Scorer correct | PASS | perfect, empty, hand-worked 5-image case and boundary case exact |
| AC-1.2-07 Consent and privacy | AUTO PASS (tooling) · real PENDING-HUMAN | `data/` ignored; sources allowlist |

## Proof test PT-1.2 "Blind label audit": machine part PASS (evidence/PT-1.2-machine.txt); human part PENDING (HC-012 step 5)

## Notes for the next Refiner
- **Shared CLIs** are listed in SPEC section 2. Labels go in `data/labels/screens.json` (ScreenLabel array). Predictions are a Finding array with `image` set; only `decision == "hide"` counts as a cover.
- **Synthetic set:** `python -m workshop.screens.synth --out <dir>` writes 75 + 2 images, labels in `truth.json`, in about 1.3 s. Stand-ins:
  - cat = orange circle with ears;
  - spider = black circle with 8 legs;
  - dog lookalike = brown circle with hanging ears.

  These are not real animals, so a real vision model won't recognise them as cats. For 1.3, use real public photos composed into screens.
- **dHash** (256-bit, maxDist 20) is tuned for textured content. Flat images collide.
- **Pre-commit's ruff-format** reformats Builder code at commit time, and the helper re-stages it. Builders should run `ruff format` themselves.
