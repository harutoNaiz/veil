# Phase 6.1 The Console app (Flutter) · WAITING_HUMAN
Commits: 0e82610 (6.1.1), d6f3e63 (6.1.2), 9ddef28 (6.1.3) · Spec: SPEC.md (143 lines)

## Summary
The Console app is built against a fake Guard behind its own `GuardClient` interface. Pigeon bridge: 12 commands off the main thread, two event streams, protocol version check, packs passed as files with checksums.
- **Onboarding:** disclosure, accessibility with restricted settings, capture consent, notifications, and a status screen with one-tap fixes.
- **Main screens:** Concept Studio, Strictness, Skip list, Live stats, Recent covers.
- **Checks:** `flutter analyze` and `flutter test` pass (guard, onboarding and screens suites); a no-network grep is clean.

## Pending
- **"Real Guard" acceptance rows:** need 5.2 and a phone.
- **Kotlin bridge compile:** `flutter build apk --debug` is deferred (D-6.1-apk).
- **People:** 3 first-time users and a TalkBack check (HC-019).
