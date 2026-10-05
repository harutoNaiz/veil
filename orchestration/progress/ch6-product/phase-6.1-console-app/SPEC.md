# SPEC 6.1 The Console app (Flutter)

MODEL: claude-opus-5-5 · Status: APPROVED (orchestrator) · Source: PLAN.md lines 1834-1932 · Fast track (F1-F12): 3 parallel Sonnet Builders, ~15 min.

## 1. Deviations and risks
- **No real Guard, no phone.** Everything is built and tested against `FakeGuard`. All "real Guard" parts of AC-01/02/04/06 are **PENDING** (need Phase 5.2 and the phone). `main.dart` uses the fake by default; `--dart-define=VEIL_GUARD=pigeon` switches to the bridge.
- **The Kotlin host lives in `console/android`** (not `guard/`). It has a `GuardBackend` interface whose only implementation for now is `NoGuardBackend`: `hello` answers, `requestPermission` opens the real system screens, and every other command fails with `FlutterError("guard_unavailable")`. Chapter 4/5 plugs the real Guard in behind `GuardBackend` later.
- **Kotlin compile and APK build are not checked inline** (7.4 GB RAM, F6). Add `flutter build apk --debug` to `DEFERRED.md`. Verify = `flutter analyze` + `flutter test` + pigeon regen only.
- **The PLAN command list gets extra read-only queries** (`getState`, `installedApps`, `recentCovers`), and **disclosure consent counts as a permission** (`Perm.disclosure`), so consent survives in the Guard's own settings and the app needs no local storage dependency.
- **Example photo picker = interface only** (`PhotoSource`). Tests use the fake. A real picker is deferred to 6.2/phone work (row added to DEFERRED).
- **Generating the "looks like / but not" lists** is `compileConcept`. The fake uses templates; the real generation belongs to the Guard/Workshop (6.2).
- **New deps (only 6.1.1 edits pubspec):** `pigeon` (dev) and `crypto`, pinned to exact versions with no caret. Pigeon must be ≥ 22.7 for `@EventChannelApi`. If that is unavailable, use a `@FlutterApi` callback (`onState`/`onStats`) wrapped in Dart `Stream`s.
- **Shared Flutter lock:** concurrent `flutter` commands queue on the startup lock, so it is safe but slower. The orchestrator runs the 3 verify scripts **after all Builders finish**, because files cross-import (main → HomeShell, HomeShell → StatusScreen).

## 2. Shared interfaces (fixed: code against these from minute 0)
`console/lib/guard/guard_client.dart` is owned by 6.1.1 and **written verbatim as its first step**. Nobody else edits it.
```dart
const int kGuardProtocolVersion = 1;
enum Mode { light, balanced, strict }                 // = contracts engine-stats.mode
enum Perm { disclosure, accessibility, restrictedSettings, screenCapture, notifications }
enum CaptureState { running, paused, stopped, awaitingPermission }
enum Connection { connecting, connected, incompatible, unavailable }
enum FeedbackKind { correct, notThis, missed }         // = contracts feedback.kind
enum CoverStyle { solid, blur, mosaic }                // = contracts concept.coverStyle
enum PackResult { accepted, rejectedChecksum, rejectedInvalid }
class FileRef { final String path; final String sha256; const FileRef(this.path, this.sha256); }
class ConceptView { final String conceptId, displayName; final bool enabled; final List<String> looksLike, butNot;
  final CoverStyle coverStyle; final List<FileRef> examplePhotos; const ConceptView({...}); ConceptView copyWith({...}); }
class GuardState { final Connection connection; final int protocolVersion; final bool running; final Mode mode;
  final CaptureState captureState; final Map<Perm, bool> permissions; final List<String> skipList;
  final List<ConceptView> concepts; final String? activePackSha256; const GuardState({...});
  List<Perm> get missing => Perm.values.where((p) => permissions[p] != true).toList();
  bool get setupComplete => missing.isEmpty; GuardState copyWith({...}); }
class StatsTick { final int tMs; final double looksPerSecond, aiMsLastLook, batteryImpactPctPerHour; final int activeCovers; const StatsTick({...}); }
class RecentCover { final String coverId, conceptId, thumbnailPath; final int tMs; final FeedbackKind? mark; const RecentCover({...}); }
class InstalledApp { final String package, label; const InstalledApp(this.package, this.label); }
class GuardIncompatible implements Exception { final int guardVersion; const GuardIncompatible(this.guardVersion); }
abstract class PhotoSource { Future<FileRef?> pick(); }
abstract class GuardClient {
  Future<GuardState> connect();            // hello → version check; mismatch throws GuardIncompatible and state.connection=incompatible
  GuardState get current;                  // last known state, read from the Guard (never cached on disk by the app)
  Stream<GuardState> get states;           // engine state + permissions; emits on every change
  Stream<StatsTick> get stats;             // ~1 per second
  Future<void> start(); Future<void> stop(); Future<void> setMode(Mode m);
  Future<void> setSkipList(List<String> packages); Future<List<InstalledApp>> installedApps();
  Future<ConceptView> compileConcept(String text, List<FileRef> photos);  // draft with looksLike/butNot
  Future<PackResult> applyConcepts(List<ConceptView> concepts);          // writes pack file + setConceptPack
  Future<PackResult> setConceptPack(FileRef pack);                       // checksum/schema check; on reject the old pack stays
  Future<void> submitFeedback(String coverId, FeedbackKind kind);
  Future<List<RecentCover>> recentCovers({int limit = 20});
  Future<void> requestPermission(Perm p);  // opens the system screen; disclosure = consent accepted
  Future<void> dispose();
}
```
`console/lib/guard/fake_guard.dart` (6.1.1): `FakeGuard({int protocolVersion = kGuardProtocolVersion, Set<Perm> granted = const {}, bool autoGrant = true, Duration? statsPeriod = const Duration(seconds: 1)})`. Tests pass `statsPeriod: null` and call `emitStats(StatsTick)` by hand. It exposes `final List<String> calls` (the command names in order) and `void grant(Perm)` / `revoke(Perm)`. Its state survives `dispose()` + `connect()` on the same instance (this simulates an app restart). `setConceptPack` hashes the file; a mismatch or bad JSON returns a rejection and `activePackSha256` is unchanged. It returns 3 canned `RecentCover`s and 4 canned apps. `FakePhotoSource(List<FileRef>)` lives in the same file.
Widget signatures (all take `{super.key, required GuardClient guard}`):
- 6.1.2: `VeilConsoleApp({guard, PhotoSource? photos, Widget Function(GuardClient)? homeBuilder})` in `lib/app.dart`, `OnboardingFlow` in `lib/onboarding/onboarding_flow.dart`, `StatusScreen` in `lib/status/status_screen.dart`.
- 6.1.3: `HomeShell({guard, PhotoSource? photos})` in `lib/screens/home_shell.dart`.
- Semantics rule: every tappable control has a visible text label or a `Semantics(label:)` / `tooltip`. No fixed-height text containers.

## 3. Sub-phases (all three run in parallel)
Run every command from `D:\iqoo finale\veil` as `powershell -NoProfile -ExecutionPolicy Bypass -File tools\with-env.ps1 --cd console <cmd>`. Each verify script uses the `Check` pattern from `tools/verify/3.1.3.ps1`, takes under ~5 min, and ends with `VERIFY 6.1.N: PASS` or `FAIL`.

### 6.1.1 Bridge, fake Guard, app interface
**Goal:** The app can control the Guard and see its state through one interface. Pigeon bridge + fake.
**Owns:** `console/pubspec.yaml`, `console/pubspec.lock`, `console/pigeons/**`, `console/lib/guard/**`, `console/android/**`, `console/test/guard/**`, `tools/verify/6.1.1.ps1`.
**Files:** `pigeons/guard_api.dart`; generated `lib/guard/generated/guard_api.g.dart` and `android/app/src/main/kotlin/com/veil/console/bridge/GuardApi.g.kt`; `lib/guard/{guard_client,fake_guard,pigeon_guard,pack_files,guard_factory}.dart`; Kotlin `bridge/{GuardBackend,NoGuardBackend,GuardHostImpl}.kt`; `MainActivity.kt` (registers the host).
**Steps:**
1. Write `guard_client.dart` verbatim from §2. Then `flutter pub add crypto` and `flutter pub add --dev pigeon`, and change both to exact pins.
2. Pigeon definition. `@HostApi() GuardHostApi`, with every method marked `@TaskQueue(type: TaskQueueType.serialBackgroundThread)` so calls run off the main thread: `hello()→HelloMsg{protocolVersion, contractVersion}`, `getState`, `start`, `stop`, `setMode(String)`, `setSkipList(List<String>)`, `installedApps`, `compilePack(String text, List<FileRefMsg>)`, `setConceptPack(FileRefMsg)→String`, `submitFeedback(String coverId, String kind)`, `recentCovers(int)`, `requestPermission(String)`. `@EventChannelApi()` with `streamState()→StateMsg` and `streamStats()→StatsMsg`. Generate with `dart run pigeon --input pigeons/guard_api.dart`.
3. `pack_files.dart`: `Future<FileRef> writePack(List<ConceptView>, Directory dir)` writes concept-pack JSON (`contractVersion "1.0"`) and the sha256. `Future<bool> verifyFile(FileRef)` checks it.
4. `PigeonGuard implements GuardClient` maps the messages to the §2 types and checks the version in `connect()`. `guard_factory.dart`: `GuardClient createGuard()` reads `String.fromEnvironment('VEIL_GUARD', defaultValue: 'fake')`.
5. Kotlin: `GuardHostImpl` delegates to `GuardBackend`. `NoGuardBackend` opens the accessibility settings, App info (`ACTION_APPLICATION_DETAILS_SETTINGS`, for restricted settings), the notification permission and MediaProjection consent. Before accepting a pack it checks the sha256 with `MessageDigest`. Add **no** `INTERNET` permission to the main manifest.
6. Tests in `test/guard/`:
   - `fake_guard_test` (each command round-trips and shows up in `calls` and `states`)
   - version mismatch → `GuardIncompatible`
   - corrupt pack (bytes changed after hashing) → `rejectedChecksum` with the previous `activePackSha256` kept
   - dispose + reconnect gives the same state
   - `pigeon_guard_test`: mock the `BinaryMessenger` for `hello` and check the version
**Verify `6.1.1.ps1`:** (1) pigeon regen produces no diff in the generated files. (2) `flutter analyze lib/guard test/guard`. (3) `flutter test test/guard`. (4) No-network grep: `HttpClient|package:http|Socket|WebSocket` absent from `console/lib`, and `android.permission.INTERNET` absent from `android/app/src/main/AndroidManifest.xml`. (5) The `@TaskQueue` count equals the HostApi method count.

### 6.1.2 Onboarding and status
**Goal:** Get a new user from install to protected, clearly and honestly. Missing pieces get a one-tap fix.
**Owns:** `console/lib/main.dart`, `console/lib/app.dart`, `console/lib/theme.dart`, `console/lib/onboarding/**`, `console/lib/status/**`, `console/test/onboarding/**`, `console/test/widget_test.dart`, `tools/verify/6.1.2.ps1`.
**Steps:**
1. `theme.dart`: light and dark `ThemeData`. `VeilConsoleApp` uses `themeMode: ThemeMode.system`.
2. `app.dart` RootGate: `connect()` first.
   - `GuardIncompatible` → "Update Veil" screen
   - `unavailable` → "Veil service not running"
   - not set up → `OnboardingFlow`
   - otherwise → `homeBuilder ?? HomeShell`
   It rebuilds from `guard.states`. `main.dart`: `runApp(VeilConsoleApp(guard: createGuard()))`.
3. `OnboardingFlow` pages, each with an "Open settings / Allow" button → `requestPermission`, and the page advances when `states` shows it granted:
   - Disclosure: what Veil does, "nothing leaves your phone", explicit **I agree** → `Perm.disclosure`
   - Accessibility service
   - Allow restricted settings: explains the App info → ⋮ → "Allow restricted settings" path
   - Screen capture: "Entire screen", and why it is asked again after locking
   - Notifications: for "Resume Veil"
   - Done
4. `StatusScreen`: one row per `Perm` with ✓ / missing. Each missing row has a one-line reason and a **Fix** button (one tap → `requestPermission(p)`). It also shows running / captureState.
5. Tests:
   - full onboarding against `FakeGuard()` reaches the home placeholder, and `calls` contains every Perm in order
   - `StatusScreen` with `granted:{disclosure, accessibility}` shows 3 Fix buttons; tapping one calls `requestPermission` and the row turns ✓
   - incompatible version → update screen
   - a11y: `meetsGuideline(labeledTapTargetGuideline)` and `androidTapTargetGuideline` on every onboarding page
   - `textScaler: TextScaler.linear(2.0)` gives no overflow exception
   - dark brightness renders
   Replace the old `widget_test.dart` with a smoke test.
**Verify `6.1.2.ps1`:** `flutter analyze lib/main.dart lib/app.dart lib/theme.dart lib/onboarding lib/status test/onboarding test/widget_test.dart`, then `flutter test test/onboarding test/widget_test.dart`.

### 6.1.3 Main screens
**Goal:** Everything the user needs day to day, wired to `GuardClient`.
**Owns:** `console/lib/screens/**`, `console/test/screens/**`, `tools/verify/6.1.3.ps1`.
**Steps:**
1. `HomeShell`: a `NavigationBar` with Concepts, Strictness, Skip list, Stats and Recent. The AppBar has a Start/Stop switch and a status icon that pushes `StatusScreen` (badge if `missing` is non-empty).
2. `concept_studio_screen.dart`:
   - Type a dislike → "Add example photo" (`PhotoSource`) → `compileConcept` → show the **Looks like** and **But not** chips
   - Choose a cover style (SegmentedButton solid/blur/mosaic) → Save → `applyConcepts`
   - The list has an on/off `Switch` per concept (→ `applyConcepts`)
   - A rejected pack shows a SnackBar "Pack rejected; previous pack still active"
3. `strictness_screen.dart`: Light / Balanced / Strict radio → `setMode`, each with a plain trade-off line (speed of covering vs battery vs false covers).
4. `skip_list_screen.dart`: `installedApps()` with a checkbox each → `setSkipList`.
5. `live_stats_screen.dart`: built from `stats`. Shows looks/s, covers on screen, AI time (ms), battery impact %/h, with "—" until the first tick.
6. `recent_covers_screen.dart`: `recentCovers()`. A thumbnail (`Image.file` with an `errorBuilder` icon, local only) plus 3 buttons, **Correct / Not this / Missed one** → `submitFeedback`. The marked state is shown.
7. Tests (each screen against `FakeGuard(granted: Perm.values.toSet(), statsPeriod: null)`):
   - each action lands in `fake.calls` with the right args
   - the stats screen updates after `emitStats`
   - reopen: pump `HomeShell`, set mode strict, unmount, pump a new `HomeShell` on the same fake → strict is shown within `pump(Duration(seconds: 1))`
   - a11y on every screen: labeled tap targets, 200% text gives no overflow, dark renders
**Verify `6.1.3.ps1`:** `flutter analyze lib/screens test/screens`, then `flutter test test/screens`.

## 4. Acceptance
| ID | Criterion | Pass threshold | Status |
| --- | --- | --- | --- |
| AC-6.1-01 | Bridge complete | Every command round-trips against the fake Guard and the real Guard; the protocol version is checked on connect | AUTO (fake, 6.1.1) · PENDING (real Guard) |
| AC-6.1-02 | Reopens correctly | After the app is killed and reopened, it shows the Guard's correct state within 1 s (real Guard) | AUTO proxy (6.1.3 reopen test) · PENDING (real Guard, PHONE) |
| AC-6.1-03 | Files, not channels | Packs and photos move as files; a corrupted file is rejected and the previous pack stays active | AUTO (6.1.1) |
| AC-6.1-04 | Onboarding works | 3 first-time users finish setup without help (real Guard) | HUMAN · PENDING (real Guard) |
| AC-6.1-05 | Missing pieces explained | Each missing permission is shown with a one-tap fix | AUTO (6.1.2) |
| AC-6.1-06 | Screens work | Every action on every main screen works with the real Guard; widget tests pass against the fake | AUTO (fake, 6.1.3) · PENDING (real Guard) |
| AC-6.1-07 | Accessible | Every control has a screen-reader label; text at 200% size does not clip | AUTO (6.1.2, 6.1.3) + HUMAN TalkBack spot-check |
| AC-6.1-08 | No stray network | The only network calls go to Workshop endpoints | AUTO static (6.1.1 grep + manifest) · PHONE network log DEFERRED |

## 5. Proof test PT-6.1 "First-time user"
- **Machine (now):** the widget tests from the 3 verify scripts against `FakeGuard`: full onboarding, every screen action reaching the Guard (`calls`), reopen showing the correct state, corrupt pack rejected. Result: PASS-fake.
- **Phone (PENDING, Phase 5.2 + iQOO):** Flutter `integration_test` against the real Guard (every screen and action, plus kill and reopen within 1 s), recorded with scrcpy.
- **Human (PENDING-HUMAN):** a fresh install on the iQOO. 3 people who have never seen Veil are each told only "Make it hide cats". The observer notes every hesitation, wrong tap or question and does not help. Pass = all 3 finish unaided and understand each permission step. Onboarding failures → change the wording or flow and retest with 3 *new* people.

## 6. Human items (one line each in HUMAN_CHECKS.md)
- [ ] HC-6.1-a: 3 first-time users × onboarding + "hide cats" on the iQOO, with observer notes and scrcpy (needs the real Guard).
- [ ] HC-6.1-b: TalkBack pass over onboarding and the 5 main screens, plus system font size at max (200%) visual check.
- [ ] HC-6.1-c: Read the disclosure screen wording: honest, prominent, consent is clear.
- [ ] DEFERRED: `flutter build apk --debug` (Kotlin host compiles); real photo picker; on-phone network log showing no non-Workshop traffic.
