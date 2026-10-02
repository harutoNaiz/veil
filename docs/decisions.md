# Decisions

Numbered, newest last. Scripts may append entries between their own markers.

## D-001 · Hackathon build, licences reviewed before any commercial release

Date: 2026-10-02 · Phase 1.1 · Status: accepted

Veil is built as a hackathon/demo build. Every third-party licence is reviewed before any commercial release (PLAN Appendix C). The table below is copied from Appendix C and is the list to work through.

| Part | Licence (as found) | Impact |
| --- | --- | --- |
| SigLIP2 | Apache-2.0 | Fine |
| YOLOE (Ultralytics) | AGPL-3.0 (assumed from Ultralytics' other code; verify) | Commercial use needs an Ultralytics licence or a replacement |
| MobileCLIP / MobileCLIP2 weights (incl. YOLOE-26's text encoder) | Apple research-only | Not usable in a commercial product |
| NudeNet | AGPL-3.0 (reported; verify) | Needs replacement or compliance |
| Toxicity model (mmBERT-small based) | Apache-2.0 | Fine |

## D-002 · Portable, project-local toolchain

Date: 2026-10-02 · Phase 1.1 · Status: accepted

All tools are installed by `tools/bootstrap.ps1` into one folder outside the repository, with no admin rights, no PATH changes and no registry changes. Every shell loads the tools with `tools/env.ps1` (PowerShell) or `tools/env.sh` (Git Bash), for the current shell only.

- **Location (DV-1).** The toolchain path may not contain spaces, because Flutter does not support them. The rule is, in order: `-ToolchainDir` or `$env:VEIL_TOOLCHAIN`; `<parent of the repo>\toolchain` if that has no spaces; otherwise `<drive of the repo>\veil-toolchain`. On the first laptop that is `D:\veil-toolchain`. The repository itself may sit in a path with spaces (`D:\iqoo finale\veil`).
- **No Android Studio (DV-2).** The portable Android command-line SDK and Temurin JDK 17 are used instead. Android Studio's Profiler and Database Inspector are first needed in Phases 3.3 and 5.1; nothing in 1.1 depends on Android Studio.
- **ML packages declared, not installed (DV-3).** torch, torchvision, transformers and ultralytics are pinned in the `ml` dependency group of `pyproject.toml` and locked in `uv.lock`. They are installed from Phase 1.3 with `uv sync --locked --group ml`.
- **Pins.** All versions are in `tools/toolchain.json` and `pyproject.toml` / `uv.lock`:
  - Python 3.11.16, managed by uv 0.12.21 (never the system Python);
  - Temurin JDK 17.0.20.1+1;
  - Android SDK: API 36, build-tools 36.0.0, NDK 28.2.13676358, latest platform-tools;
  - Gradle 9.3.1, Android Gradle Plugin 9.1.0, Kotlin 2.4.0, kotlinx-coroutines 1.11.0;
  - Flutter 3.47.6;
  - scrcpy 4.1, ffmpeg 9.0.2, ktlint 1.8.0.

## D-003 · Contract v1.0 covers 16 types

Date: 2026-10-02 · Phase 1.1 · Status: proposed (needs owner approval, AC-1.1-05)

The shared contracts v1.0 define these 16 types, one JSON Schema each in `contracts/`:
`Rect`, `Frame`, `UiEvent`, `Region`, `Embedding`, `Concept`, `ConceptPack`, `CompiledConcept`, `Finding`, `Track`, `Mask`, `MaskPlan`, `Feedback`, `ModelManifest`, `EngineStats` and `ScreenLabel`.

PLAN 1.1.2 lists 15 types but its deliverables and AC-1.1-03 say 16. The 16th is `ScreenLabel`, the screenshot label format, because Phase 1.2's entry condition reads "the label format schema exists". `Tape` (Phase 2.1) and `LookRequest` (Phase 2.2) are added by those phases as v1.1 additions.

<!-- The target-chip check (D-004 or later) is appended by workshop.bench.device_profile. -->
