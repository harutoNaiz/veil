# Phase 4.1 Screen capture · WAITING_HUMAN (phone)
Commits: 2bafc78 (4.1.1), 1fd9300 (4.1.2), 0f6ff20 (4.1.3) · Spec: SPEC.md (95 lines)

## Summary
The Guard can hold screen-capture permission, and it builds:
- a mediaProjection foreground service with a consent screen;
- a capture state machine with awaiting-permission, keyguard and "Resume Veil" handling;
- an adb command receiver.

Also built:
- **Frame source:** 360 × panel-aspect frames (360×792 on the iQOO 15), latest frame only, released immediately. Pause, resume and rotation reuse one virtual display, so no new consent dialog appears. An unreleased-frame counter and an fps meter are included.
- **Backup path:** accessibility screenshots, switchable at runtime.
- **Blind spots:** detects large black areas.
- **Phone tooling:** a driver routine and a log checker.

JVM tests and the debug build pass. Every on-device criterion is PENDING (phone): HC-020.

## Notes
- The screenshot "interval too short" error code is assumed to be 3 (unconfirmed). Check it on the phone.
- 4.2 must set `ScreenshotBridge.provider` from its accessibility service. Until then AC-4.1-07 stays pending.
- The 10-minute memory run (AC-4.1-03) is deferred to the phone session.
