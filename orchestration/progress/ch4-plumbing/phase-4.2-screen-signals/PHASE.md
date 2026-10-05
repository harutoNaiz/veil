# Phase 4.2 Screen signals · WAITING_HUMAN
Commits: 02fc4a0 (4.2.1), 8eab490 (4.2.2), 958389e (4.2.3), 7f07ebf (ignore generated fixtures) · Spec: SPEC.md (124 lines)

## Summary
- **4.2.1:** the single Guard accessibility service, GuardAccessibilityService. It feeds an event mapper and logger (UiEvent JSONL, 1,000 events validate), tracks the foreground app, provides the ScreenshotBridge source, and hosts the OverlayHost hook for 4.3. Also pull_log.py.
- **4.2.2:** ScrollTracker and FrameShiftEstimator, plus scroll_ruler.py.
- **4.2.3:** BoundedSnapshotter, plus snap_cost.py and frame_stats.py.
- All JVM tests and the app build pass on the laptop. Everything on the phone is PENDING-HUMAN (HC-023).

## Deviations
- **The proof-test script `tools/verify/pt-4.2.ps1` was not written**: the 4.2.2 Builder ran out of time. HC-023 step 5 falls back to SPEC §5 by hand. Tracked as D-4.2-pt.
- **There is no `drive scroll` tool**, so frame_stats uses `adb shell input swipe`.

## Notes for later phases
- **4.3** hosts its overlay through OverlayHostRegistry in GuardAccessibilityService (amendment A1).
- **Build hygiene:**
  - VS Code's Java extension starts its own Gradle daemon on guard/, which can hang veil Gradle builds on project locks.
  - Verify scripts must wait only for `veil-toolchain` Gradle processes, never for every java.exe.
