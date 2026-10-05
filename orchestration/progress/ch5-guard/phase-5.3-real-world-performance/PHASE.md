# Phase 5.3 Real-world performance · WAITING_HUMAN
Commits: 25b18a5 (5.3.1), ed55e66 (5.3.2), f5ff3fd (5.3.3) · Spec: SPEC.md (146 lines)

## Summary
All the measurement tooling is built and tested on synthetic fixtures. It is a standard-library Python package, `workshop/perf/`, with no Gradle:
- latency parser and capture (5.3.1);
- jank, memory, heat and kill probes (5.3.2);
- battery A/B, the Chapter 5 report, the twin-params sync check (`tune --check`) and the `pt-5.3.ps1` driver (5.3.3).

Every on-phone number is PENDING-HUMAN (HC-021). `docs/reports/ch5-guard.md` was generated from empty evidence, so every row shows PENDING-HUMAN.

## Acceptance criteria
- AC-5.3-08 (twin sync) passes automatically.
- All other ACs are PHONE (HC-021).

## Deviations from PLAN.md
- Latency comes from the Guard's own `kind=stage` debug lines, not from Perfetto queries. The Perfetto cross-check is D-5.3-perfetto.

## Notes for the next Refiner / 5.2-W
5.2-W (live wiring) must add:
- the `kind=stage` debug lines and Trace sections;
- a `mode` command (`--es cmd mode --es value <m>`) in CaptureCommandReceiver. `workshop/perf/battery/session.py` relies on it.
