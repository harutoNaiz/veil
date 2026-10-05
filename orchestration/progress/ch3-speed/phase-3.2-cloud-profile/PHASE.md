# Phase 3.2 Profile on cloud phones · WAITING_HUMAN
Commits: c61637d (3.2.1), e5fa048 (3.2.2), 5830edf (3.2.3) · Spec: SPEC.md (88 lines)

## Summary
The full cloud-profiling pipeline exists and runs end to end on stand-in (fixture) AI Hub responses:
- job submitter, result collector and layer-placement parser (3.2.1);
- precision chooser (3.2.2);
- per-look budget, ModelManifest writer and validator, and report (3.2.3).

On fixtures, one Balanced look totals 28.6 ms (budget ≤ 45 ms). The fixtures plant one off-chip case (YOLOE float16: two NonZero layers on the CPU) to prove the parser catches it.

The real numbers need your AI Hub token: one command, `tools\cloud_live.ps1` (HC-017).

## Acceptance criteria
AC-3.2-01 to 05 all pass on fixtures. Every real-chip value is PENDING-HUMAN (HC-017).

## Notes and risks for the live run
- **3.2.1's LiveClient is untested**, and its `qai_hub` option names weren't checked against the installed 0.56.0 package. Expect a small fix at the first live run.
- **3.2.2's live scoring of detectors** is a stub (NotImplemented). It's needed before precision can be chosen for YOLOE and NudeNet.
- **Deviation:** the SigLIP2 text encoder is the one allowed off-chip exception (it runs only at setup).
