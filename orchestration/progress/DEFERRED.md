# Deferred heavy checks

Checks that take more than 5 minutes or are heavy never run inside a phase (FAST TRACK rule F6). They run here as one batch: at a chapter's end, or while the user is away. Run them one at a time (the laptop has 7.4 GB RAM). Record each result and update the phase's `PHASE.md` row.

| ID | Phase · AC | What | How | Est. | Status |
| --- | --- | --- | --- | --- | --- |
| D-1.1-01 | 1.1 · AC-1.1-01 | Clean-room setup from the README only | Delete `D:\veil-cleanroom-1.1` if present. Then run Checker prompt C: clone to `D:\veil-cleanroom-1.1\veil`, follow the README with a fresh toolchain download (about 4.5 GB), build everything, and run bench_check with phone and cloud skipped. Watch item: CRLF checkout vs `gen_python.py --check`. Evidence: `progress/ch1-see/phase-1.1-foundations/evidence/1.1-AC01-cleanroom.md` | 1.5-2 h | TODO (a first attempt was stopped at 08:00 for the fast-track switch; partial folder `D:\veil-cleanroom-1.1` may exist) |
| D-1.3-07 | 1.3 · AC-1.3-07 (clean-checkout part) | Regenerate every Chapter 1 number from a clean checkout | In the D-1.1-01 clean-room clone, run `tools\ch1_see.ps1 -Set public -NoCache` and compare with `data/ch1/results-public.json` (± 0.5 points) | 30-45 min | TODO |
| D-6.1-apk | 6.1 · Kotlin bridge compile | `flutter build apk --debug` compiles the console Kotlin bridge (Pigeon host) | `powershell -NoProfile -ExecutionPolicy Bypass -File tools\with-env.ps1 --cd console flutter build apk --debug` (alone; Gradle) | 5-10 min | TODO |
| D-5.3-perfetto | 5.3 · latency cross-check | Perfetto trace_processor query cross-check of the Guard's own stage timestamps | Download trace_processor; query the Trace sections from a 5-min capture | 20 min | TODO |
| D-6.3-guard | 6.3 · AC-6.3-02 (Guard part) | Kotlin crash and restart tests, plus the Resume notification on the Guard | Needs Gradle and the 5.2 wiring | 30 min | TODO |
| D-6.3-blind | 6.3 · edge cases | Blind-app hint overlay | Needs 4.3 overlay + 5.2 | 20 min | TODO |
| D-6.3-heat | 6.3 · edge cases | 20-minute thermal run | Phone (with HC-022) | 25 min | TODO |
| D-4.2-pt | 4.2 · proof test | Write `tools/verify/pt-4.2.ps1` (Scroll ruler, SPEC §5 machine part) | veil-builder, no Gradle needed | 15 min | DONE (D-small-1) |
| D-5.2W-finder | 5.2-W | Finder (YOLOE) port is null in the live Guard | Wire YOLOE ONNX as the Finder after 3.3 picks runtimes | 30 min | TODO |
| D-5.2W-tox | 5.2-W · HC-018 | Toxicity text model needs an on-device tokenizer | Port the tokenizer (Kotlin) for Horizon-Labs/multilingual-toxicity-small | 45 min | TODO |
| D-5.2W-teacher | 5.2-W | Teacher live concept swap (only a reload command today) | Hot-swap the concept bank without a restart | 20 min | TODO |
| D-5.2W-accel | 5.2-W | GPU crop and faster ONNX backends (QNN/NNAPI) | After 3.3 runtime choice | 45 min | TODO |
| D-5.2W-console | 5.2-W · 6.1 | Real console GuardBackend (separate APK; Guard receivers are DUMP-protected) | Bound service or signature permission | 45 min | TODO |
| D-5.2W-tune | 5.2-W · 5.3 | `tune.py --check` must also cover the new app/src/main/assets/params.json | One-line extension | 5 min | DONE (D-small-1) |
| D-7.0-auc | 7.0.1 · 3.1 | Re-run the toxicity AUC with sigmoid(logits[0]) scoring (3.1 measured with softmax) | Heavy: loads the toxicity model; run alone | 20 min | TODO |
