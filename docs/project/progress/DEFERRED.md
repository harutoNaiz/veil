# Deferred heavy checks

Checks that take more than 5 minutes or are heavy never run inside a phase (FAST TRACK rule F6). They run here as one batch: at a chapter's end, or while the user is away. Run them one at a time (the laptop has 7.4 GB RAM). Record each result and update the phase's `PHASE.md` row.

| ID | Phase · AC | What | How | Est. | Status |
| --- | --- | --- | --- | --- | --- |
| D-1.1-01 | 1.1 · AC-1.1-01 | Clean-room setup from the README only | Delete `D:\veil-cleanroom-1.1` if present. Then run Checker prompt C: clone to `D:\veil-cleanroom-1.1\veil`, follow the README with a fresh toolchain download (about 4.5 GB), build everything, and run bench_check with phone and cloud skipped. Watch item: CRLF checkout vs `gen_python.py --check`. Evidence: `progress/ch1-see/phase-1.1-foundations/evidence/1.1-AC01-cleanroom.md` | 1.5-2 h | TODO (a first attempt was stopped at 08:00 for the fast-track switch; partial folder `D:\veil-cleanroom-1.1` may exist) |
| D-1.3-07 | 1.3 · AC-1.3-07 (clean-checkout part) | Regenerate every Chapter 1 number from a clean checkout | In the D-1.1-01 clean-room clone, run `tools\ch1_see.ps1 -Set public -NoCache` and compare with `data/ch1/results-public.json` (± 0.5 points) | 30-45 min | TODO |
