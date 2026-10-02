# Phase 1.1 Foundations · WAITING_HUMAN
Updated: 2026-10-02 08:05 · Commits: 23e0c08..8003058 · Spec: SPEC.md (APPROVED)

## Summary
The project now has a real home.
- **Repository.** The `veil/` repository has the agreed layout.
- **One-command setup.** A single command installs every tool the team needs (Python, Android, Flutter, adb, scrcpy, ffmpeg) into `D:\veil-toolchain`, without admin rights or system changes.
- **Hello apps.** A hello Guard app (Android/Kotlin) and a hello Console app (Flutter) build. So does the first version of the Test Feed app, a fake social feed that logs where every item is.
- **Contracts.** The shared "language" (16 data shapes) is written, with 430 tests.
- **Bench check.** One command checks the whole test bench.

All of this was verified on the laptop. What's left needs you: the phone, an AI Hub token, approving the contracts, and a waiver decision (Sitting 1 in `progress/HUMAN_CHECKS.md`).

## Sub-phases
| Sub-phase | Status | Builder model | Fix rounds | Record |
| --- | --- | --- | --- | --- |
| 1.1.1 Repository and tools | VERIFIED (phone launch pending HC-002) | claude-sonnet-5-5 (×2: first cut off by the usage limit, then resumed) | 0 | 1.1.1-repository-and-tools.md |
| 1.1.2 Shared contracts, first version | VERIFIED (approval pending HC-010) | claude-sonnet-5-5 | 0 | 1.1.2-shared-contracts-first-version.md |
| 1.1.3 Device check and accounts | VERIFIED (P1-P2 pending HC-002/003) | claude-sonnet-5-5 | 0 (one self-fix before hand-back) | 1.1.3-device-check-and-accounts.md |

## Acceptance criteria
| AC | Type | Result | Measured | Evidence |
| --- | --- | --- | --- | --- |
| AC-1.1-01 Clean setup | CLEAN | DEFERRED (D-1.1-01) | the clean-room run was stopped at the fast-track switch; it moves to progress/DEFERRED.md | evidence/1.1-AC01-cleanroom.md (partial, if any) |
| AC-1.1-02 Hello apps run | AUTO + PHONE | AUTO PASS · PHONE pending | `pytest -q`: 484 passed; Guard and Console APKs build | evidence/1.1-AC02.txt |
| AC-1.1-03 Contracts complete | AUTO | PASS | 16 types; 36 valid / 33 invalid examples; 430 passed; per-type counts test 16 passed | evidence/1.1-AC03.txt |
| AC-1.1-04 Contract rules written | AUTO + review | PASS | 153 schema-rule tests passed; orchestrator checklist review | evidence/1.1-AC04.txt |
| AC-1.1-05 Contracts agreed | HUMAN | PENDING | – | HC-010 |
| AC-1.1-06 Device known | PHONE | PENDING | template ready; fixture run shows the chip check works | HC-002, HC-007 |
| AC-1.1-07 Cloud phones reachable | AUTO (after token) | PENDING | – | HC-003 |
| AC-1.1-08 Private data protected | AUTO | PASS | `.gitignore:2:/data/*	data/x.png` | evidence/1.1-AC08.txt |

## Proof test PT-1.1 "Fresh-laptop bring-up": PENDING-HUMAN
- Machine readiness (no phone, no token): `bench_check --build never` → `RESULT: 6 PASS, 0 FAIL, 7 SKIP`. The 7 SKIPs are the phone and AI Hub lines, waiting on HC-002 and HC-003.
- Full run: HC-008 (you, watching the phone), then the orchestrator's re-run.

## Human checks
- Sitting 1: HC-006, HC-001, HC-002, HC-007, HC-003, HC-008, HC-009, HC-010, HC-011, HC-005.
- Later: HC-004.

## Deviations from PLAN.md
- **DV-1:** toolchain at `D:\veil-toolchain`, because Flutter forbids spaces in its path.
- **DV-2:** no Android Studio; a portable SDK and JDK 17 instead.
- **DV-3:** the heavy ML packages (torch, transformers, ultralytics) are pinned and locked but not installed until 1.3.
- **DV-4:** the Hugging Face token is optional.
- **DV-5:** the 16th contract type is `ScreenLabel`.
- **DV-6:** `Rect` is an object `{x, y, w, h}`.
- **DV-7:** UiEvent has 6 examples.
- **DV-8:** the AI Hub device is "Samsung Galaxy S26 (Family)", because the QRD was retired.
- **DV-9:** HC-001 is replaced by the bootstrap.
- **Builder deviations** (all accepted):
  - The licence check runs after the SDK install.
  - The `huggingface-hub` dependency override is flagged for 1.3.
  - bench_check runs the bootstrap check outside `VIRTUAL_ENV`.
- **Orchestrator decision:** a portable, project-local toolchain was built overnight without the user, and the Android SDK licences were accepted on the user's behalf (HC-006, FYI).

## What later phases can rely on
- Contract v1.0 shapes: tested, but **not frozen** until HC-010 is approved.
- The device profile: **not yet measured** (HC-002, HC-007).
- Already usable:
  - one-command setup;
  - `tools\with-env.ps1` / `tools/env.sh`;
  - the pinned Python environment;
  - the Guard and Console projects that build;
  - Test Feed v1;
  - bench_check;
  - adb driver helpers.

## Notes for the next Refiner
- **Run commands** via `powershell -NoProfile -ExecutionPolicy Bypass -File tools\with-env.ps1 <cmd>` from `D:\iqoo finale\veil`, or from Git Bash with `source tools/env.sh`. env.sh sets `MSYS_NO_PATHCONV=1`, so Unix paths like `/tmp` don't translate for git or Windows tools; use Windows paths.
- **`bootstrap.ps1 -CheckOnly`** fails with `python` if run inside `uv run` (VIRTUAL_ENV). Run it from a plain shell.
- **ML group pins:** torch 2.14.1, transformers 5.18.0 and ultralytics 8.4.171 are locked. `override-dependencies = ["huggingface-hub==2.1.1"]` overrides tokenizers' `<2.0` cap; check that tokenizers works at runtime when 1.3 installs `--group ml`.
- **torch** from PyPI is CPU-only on Windows. The laptop has a GTX 1650 Ti (4 GB) and CUDA 12.6 installed, so choose the CUDA wheel index deliberately.
- **Line endings:** system git has `core.autocrlf=true` and the repo has `* text=auto`, so checkouts get CRLF. Byte-comparing generators (e.g. `gen_python.py --check`) must tolerate that. The CLEAN run will show whether they do.
- **Memory:** 7.4 GB RAM. Gradle is capped at 2 GB, daemons are off, and only one heavy job runs at a time.
- **Test Feed v1** has placeholder content. Real cat, spider and lookalike images arrive with the phases that need them; keep everything harmless (no explicit material).
