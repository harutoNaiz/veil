# Phase 2.1 Recordings and replay · WAITING_HUMAN
Updated: 2026-10-02 14:51 · Commits: e487b63 + 4095bfb (2.1.1), 467b669 (2.1.2), 9ac4092 (2.1.3) · Spec: SPEC.md (149 lines, APPROVED)

## Summary
Moving screens can now be replayed on the laptop exactly as the phone would see them:
- a virtual clock;
- events delivered before the frame stamped at the same time;
- a cover renderer that writes MP4;
- self-capture simulation, where our own covers appear in the next frame;
- tape format v1, whose replays are byte-identical every time.

Tools for recording real sessions (adb screenrecord, scroll estimator, downscale) and labelling them over time (Label Studio video config, keyframe interpolation, agreement, split and freeze) exist. All of it is proven on generated sessions whose scroll, cuts and boxes are known exactly. Real recordings are your job (HC-014).

## Sub-phases
| Sub-phase | Status | Commit |
| --- | --- | --- |
| 2.1.1 Record sessions (tools + generated sessions) | VERIFIED (fix round: generated labels' clean ranges, lookalikes) | e487b63, 4095bfb |
| 2.1.2 Label recordings | VERIFIED (fix round: agreement denominator = boxes, per spec) | 467b669 |
| 2.1.3 Replay harness + tape v1 | VERIFIED (fix round: ruff B905) | 9ac4092 |

## Acceptance criteria
| AC | Result |
| --- | --- |
| AC-2.1-01 Enough material | PENDING-HUMAN (index tool proven) |
| AC-2.1-02 Real scroll data | PENDING-HUMAN (needs the 4.2.1 event logger) |
| AC-2.1-03 In sync | PASS on generated sessions (a +100 ms shift correctly fails) · real PENDING-HUMAN |
| AC-2.1-04 Labelled and frozen | tools PASS · real PENDING-HUMAN |
| AC-2.1-05 Replay is deterministic | PASS (3 replays byte-identical) |
| AC-2.1-06 Real-time capable | PASS (dummy pipeline) |
| AC-2.1-07 Self-capture simulated | PASS (within 1 px) |
| AC-2.1-08 Tapes valid | PASS (1801 lines validated) |

## Proof test PT-2.1 "Known scroll replay": machine part PASS (all 9 steps, evidence/PT-2.1-machine.txt); phone part PENDING (HC-014)

## Notes for the next Refiner
- **Tape v1** lives in `contracts/tape.schema.json`, an allowed 17th schema file (noted for HC-010). It already has output kinds `change`, `look`, `tracks`, `maskPlan` and `cache`, plus an `x` field for extras.
- **Generated sessions:** `python -m workshop.recordings.synth_session` writes the video, `.events.jsonl`, exact truth, and a label that validates. Dogs are in the truth (for false-positive tests) but not in the label tracks.
- **Scroll bursts** are moves with gaps ≤ 100 ms.
- **MP4s are not bit-exact**, so determinism is checked on tapes only.
