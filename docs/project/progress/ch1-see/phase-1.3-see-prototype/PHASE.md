# Phase 1.3 The SEE prototype · WAITING_HUMAN
Updated: 2026-10-02 14:35 · Commits: da92a19, c6de560, a1ed7ce, bc3a1bd · Spec: SPEC.md (249 lines, APPROVED + A1/A2)
Phase time: refine 8 min; build blocked by a 1.5 GB model download on a slow link and two usage-limit cut-offs; verify about 40 min.

## Summary
"Find what I hate and cover it" works end to end on the laptop:
- SigLIP2 fingerprints screen pieces;
- the Teacher turns a word into "looks like / but not / ignore" prompts;
- the Judge decides "hide" or "leave";
- YOLOE finds objects inside photos;
- calibration and Light/Balanced/Strict thresholds tune it;
- one command (`tools\ch1_see.ps1`) regenerates everything, and reproducibility is proven.

Indicative numbers on 50 real public photos composed into feed screens (not the gate set):
- **Balanced, dev:** cats 100% caught, 5% of clean screens wrongly covered.
- **Test split (small sample):** cats 100% caught, but 28.6% of clean screens wrongly covered. The thresholds overfit a tiny dev set.

The real Chapter 1 gate needs the 300 labelled screenshots (HC-012, then HC-013).

## Sub-phases
| Sub-phase | Status | Verify | Commit |
| --- | --- | --- | --- |
| 1.3.1 Describer and Judge on whole pieces (+ public real-photo set) | VERIFIED (1 fix round: corrupt cache → miss) | `VERIFY 1.3.1: PASS` | da92a19, a1ed7ce |
| 1.3.2 Add the object finder (YOLOE-26s, variants A/B/C) | VERIFIED | `VERIFY 1.3.2: PASS` | c6de560 |
| 1.3.3 Tune, analyse, decide | VERIFIED (1 fix round: a bug in verify check 8) | checks 1-7 full run + check 8 re-run | bc3a1bd |

## Acceptance criteria
| AC | Result | Note |
| --- | --- | --- |
| AC-1.3-01/02/03 Cats, wrong covers, spiders (real test set) | PENDING-HUMAN | `tools\ch1_see.ps1 -Set real -Test` once HC-012 is done |
| AC-1.3-04 Modes behave | PASS (synthetic, public) · real PENDING | Light ≤ Balanced ≤ Strict ordering holds |
| AC-1.3-05 List changes need no rebuild | PASS | cats → spiders → new word, same model files |
| AC-1.3-06 Unseen concept works | PASS | an unseen word builds a valid concept card and runs |
| AC-1.3-07 Reproducible | PASS (no-cache rerun within 0.005) · clean-checkout part DEFERRED | |
| AC-1.3-08 Test set not overused | PASS | test runs logged: synthetic 1+, public 1, real 0 |
| AC-1.3-09 Choices documented | PASS | decision D-004: SigLIP2-B/16 + YOLOE-26s (MobileCLIP2-B text encoder) |

## Proof test PT-1.3 "Fresh screenshots": machine part PASS (`-Fresh` gallery + tally); human part PENDING (HC-013 b)

## Notes for the next Refiner
- **Variants:** A (tiles) and C (YOLOE boxes + SigLIP2 crops) score about the same. B (YOLOE's own per-box fingerprints) is weak: recall 27-36%. Use C when small objects matter, A otherwise.
- **Speed:** about 4-6 s per screen on this CPU (laptop speed is relative only). Cache files are in `data/ch1/cache/<set>-<split>-<variant>/`.
- **Memory:** two model-loading processes at once can be killed for low memory on this 7.4 GB laptop. Run heavy checks one at a time.
- **Downloads:** the HF xet backend crawled on this link. `HF_HUB_DISABLE_XET=1` (plain HTTP) was about 10× faster and resumes.
- **Licences:** YOLOE is AGPL-3.0, and its MobileCLIP2-B text encoder is research-only. Fine for the demo; see PLAN Appendix C.
