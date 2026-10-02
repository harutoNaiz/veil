# Phase 2.2 Deciding when to look (the Gatekeeper) · WAITING_HUMAN
Updated: 2026-10-02 · Commits: 09a6c9c (2.2.1), 9251e1f (2.2.2), d521a07 (2.2.3) · Spec: SPEC.md (162 lines, APPROVED)

## Summary
The Gatekeeper decides when to look, and it saves work without missing things.
- **Change detector:** 32×64 thumbnail, 32 tiles, compares with the last analysed frame, shifts by scroll, flags scene cuts, whole-number maths only.
- **Scheduler:** pure function with Idle, Watching, Hot and Throttled states; it never queues.
- **On generated sessions (Balanced):**
  - looks at 9.1% of frames (limit < 15%);
  - 98.2% of new content gets a look within 0.2 s (target 95%);
  - 100% of scene cuts found, 0 false cuts.
- **Proof test, fresh 180 s session:**
  - all 135 triggers looked at within 200 ms;
  - only check-ups while idle;
  - nothing queues even with 0.5 s looks.

## Sub-phases
| Sub-phase | Status | Commit |
| --- | --- | --- |
| 2.2.1 Change detector | VERIFIED | 09a6c9c |
| 2.2.2 Burst scheduler | VERIFIED | 9251e1f |
| 2.2.3 Gatekeeper pipeline, look budget, timeline | VERIFIED | d521a07 |

## Acceptance criteria
| AC | Result |
| --- | --- |
| AC-2.2-01 Synthetic cases | PASS |
| AC-2.2-02 Scene cuts found | PASS on generated sessions (100%, 0 false/min) · real PENDING-HUMAN |
| AC-2.2-03 Pure and repeatable | PASS |
| AC-2.2-04 Never queues | PASS (1080/1080 busy frames skipped, queue 0) |
| AC-2.2-05 Light on effort | PASS on generated sessions (9.1%; PT 7.6%) · real PENDING-HUMAN |
| AC-2.2-06 Quick to notice | PASS on generated sessions (98.2%; PT 96.7%) · real PENDING-HUMAN |
| AC-2.2-07 Heat respected | PASS (unit test) |
| AC-2.2-08 Whole numbers only | PASS (AST check) |

## Proof test PT-2.2 "Look timeline": machine part PASS (evidence/PT-2.2-machine.txt, charts in `veil/data/evidence/pt-2.2/`); human review PENDING (HC-015)

## Deviations
- **`cut_tile_level` tuned to 24** (code default 40), beyond the spec's three tunable parameters. PLAN gives the scene-cut level only as a "starting point", and the per-mode look rates are unchanged.
- **A cut where the true scene changed is not counted as a false cut.**
- **The revealed-strip rectangle extends to the screen edge** when it touches the bar band.

## Notes for the next Refiner
- **Light and Balanced look the same** on generated sessions: both analyse 9.1% of frames. Looks are mostly change-driven, so the base rate (1 vs 3 per s) shows only in video stretches. Check this on real recordings (HC-015).
- **The pure function for 5.1** is `workshop.twin.gatekeeper.GatekeeperPipeline` plus `scheduler.step(state, tick, p)`, with the parameters in `params.json`.
- **Hot and Throttled** have unit tests only; replays don't exercise them yet.
