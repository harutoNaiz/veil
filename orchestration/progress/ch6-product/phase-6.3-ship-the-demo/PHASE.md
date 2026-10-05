# Phase 6.3 Ship the demo · WAITING_HUMAN
Commits: ef1929a (6.3.1), b199e45 (6.3.2), d9ca91b (6.3.3) · Spec: SPEC.md (~190 lines)

## Summary
- **6.3.1:** recovery hooks in FakeGuard and a "Resume Veil" button. `flutter test` prints `RECOVERY crash=5/5 lock=5/5 kill=5/5`. Also a logcat session checker (crashes, ANRs, stuck covers) and the edge-case and known-issues documents.
- **6.3.2:** a final-report generator and linter, producing `docs/reports/final.md` with fixed F-ids. Phone metrics come from `data/final/phone-metrics.json` (the template is `workshop/final/phone-metrics.template.json`).
- **6.3.3:** the demo script, phone prep, pitch outline, Q&A sheet and rehearsal log, plus `trace_claims.py`. It checks that every number cites an F-id. It passes against the real `final.md`, re-run by the orchestrator after 6.3.2 landed.

## F-id map
- Phone metrics: F-01 (time to cover p95), F-02 (Balanced battery per hour), F-31 to F-34, F-36.
- Chapter 1: F-03 to F-06. Chapter 2: F-07 to F-09. Chapter 3: F-10 and F-11 (pending, because the profile values are fixtures).
- Packs: F-20 onward.

## Acceptance criteria
- AC-6.3-04, 05 and 08 pass automatically.
- AC-6.3-02 passes automatically on FakeGuard; the real-Guard part is D-6.3-guard.
- AC-6.3-01, 03, 06, 07 and the Chapter 6 gate need the phone or a person (HC-022).

## Deferred
D-6.3-guard, D-6.3-blind, D-6.3-heat.
