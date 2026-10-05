# Phase 4.3 Drawing covers · WAITING_HUMAN
Commits: f917393 (4.3.1), e31e819 (4.3.2), 2f3f868 (4.3.3) · Spec: SPEC.md (96 lines + A1)

## Summary
- **4.3.1:** the overlay API (OverlayApi.kt, verbatim), plus:
  - OverlayRenderer, which implements signals.OverlayHost;
  - CoverView, PlanDiff, CoverGeometry and MaskPlanJson (kotlinx-serialization);
  - the command receiver and render trace, and render_stats.py;
  - a debug-only OverlayAccessibilityService in src/debug.
- **4.3.2:** GluedBox and GlueController (5 JVM tests), plus drift.py and glue_run.py.
- **4.3.3:** OwnOverlayRegistry, PeekProbe, SelfCapture, LongPressDetector, TouchReplay and CoverTouchLayer (9 JVM tests), own_join.py and selfcap_check.py, pt-4.3.ps1, and the `## Phase 4.3` and `## Chapter 4 gate` sections of docs/reports/ch4-plumbing.md.
- The laptop checks all pass. The phone checks and the Chapter 4 gate are in HC-024.

## Not wired yet (goes to 5.2-W)
- `OverlayHostRegistry.host = OverlayRenderer()` in the production Guard.
- `GlueController.register()` and its RawEvent feed.
- `SelfCapture.install(service)`.
- `CoverTouchLayer(service, log).update(covers)`.

## Notes
- drift.py assumes Test Feed log rows `{tMs, itemY}`. Check this against the real Test Feed log in HC-024.
