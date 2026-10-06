MODEL: claude-sonnet-5-5
Status: DONE. `tools/verify/D-console-bridge.ps1` -> VERIFY D-console-bridge: PASS (pigeon regen, analyze, test, flutter build apk --debug, bridge unit tests, assembleDebug, ktlint).

## D-6.1-apk root cause
Pigeon field `InstalledAppMsg.package` is a Kotlin hard keyword. Input renamed to `packageName` (pigeons/guard_api.dart, pigeon 29.0.6 unchanged); GuardApi.g.kt + guard_api.g.dart regenerated, pigeon_guard.dart updated. APK now builds.

## Bridge design (D-5.2W-console)
- Guard: `guard/bridge/ConsoleBridgeService` (Messenger, JSON in/out), manifest `<permission com.veil.guard.permission.CONSOLE protectionLevel=signature>` + service guarded by it. Pure `BridgeCore` maps ops (hello getState start pause resume stop setMode setSkipList installPack recentCovers) onto `BridgeOps`; `AndroidBridgeOps` forwards to the existing CaptureService command intents (same as the DUMP receiver), prefs, status.json, debug.jsonl, concepts dir.
- Console: `RemoteGuardBackend` (binds com.veil.guard, blocking calls on Pigeon bg thread), MainActivity uses it and polls state every 2 s for the state stream (stats stream = placeholder ticks). Manifest: uses-permission + queries. `guard_factory`: PigeonGuard on Android outside tests (`VEIL_GUARD=fake|pigeon` overrides), FakeGuard otherwise.
- pack_files.dart writes `alsoHide` when non-empty (test/guard/pack_json_extra_test.dart).
- Tests: guard/app/src/test/.../bridge/BridgeCoreTest.kt.

## Known gaps
- Both APKs MUST be signed with the same key (both debug-signed on this machine: ok); otherwise bind fails -> "guard_unavailable".
- Recent covers: ids/times from debug.jsonl plan lines, no thumbnails (thumbnailPath empty; cross-app file access not done). submitFeedback is a no-op. Stats stream carries zeros. Pack JSON is dropped in `<media>/concepts/console-pack.json` as written by Console (not compiled embeddings; Guard lane loader may skip it until Teacher compile exists, D-5.2W-teach).
- compilePack is a local draft (looksLike=[text]).
- flutter analyze runs with --no-fatal-warnings (an unused-import warning in another builder's test/screens/also_hide_test.dart).

## PENDING-HUMAN (on phone)
1. Install guard `app-debug.apk` and console `console/build/app/outputs/flutter-apk/app-debug.apk` (kit.ps1 builds both).
2. Open Guard once; enable its accessibility service; open Console -> status screen should show "connected" (not unavailable).
3. In Console tap Screen capture fix: Guard consent screen appears; accept; Console status flips to running within ~2 s.
4. Change strictness, edit skip list, add a concept: `adb shell run-as com.veil.guard cat shared_prefs/veil_guard.xml` shows mode/skip; `adb logcat | findstr veil` shows the cmd; concept json exists under /sdcard/Android/media/com.veil.guard/concepts/.
5. Pause/Stop from Console -> Guard notification state follows.

## Independent verification (orchestrator)
- 11:53: `tools/verify/D-console-bridge.ps1` re-run → VERIFY D-console-bridge: PASS (evidence/D-console-bridge-verify.txt). Commit 960a605.
