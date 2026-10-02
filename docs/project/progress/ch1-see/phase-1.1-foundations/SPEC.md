# SPEC · Phase 1.1 Foundations
MODEL: claude-opus-5-5
Status: APPROVED (orchestrator, 2026-10-02 03:40). Deviations DV-1..DV-9 accepted. W-1 goes to the user as a human check.
Based on: PLAN.md Phase 1.1 (lines 236-339), plus "How to read this plan", "Fixed decisions", "Proposed repository layout", "Acceptance contracts" and "Test bench" (lines 1-224), and the later phases' use of the contract types (lines 340-2202, read for consistency only) · veil commit none (the repository does not exist yet) · records read: none (first phase); progress/HUMAN_CHECKS.md (HC-001..HC-005, all OPEN); progress/LOG.md

---

## 1. Reality check

### 1.1 Already exists and will be reused

- Nothing of `veil/` exists yet. `progress/ch1-see/phase-1.1-foundations/evidence/` exists and is empty.
- On the laptop (probed 2026-10-02 02:40-03:15):
  - Git 2.54.0.windows.1 (global identity set), Git Bash, Windows PowerShell 5.1.26100.
  - `C:\Windows\System32\curl.exe` and `C:\Windows\System32\tar.exe` (bsdtar 3.8.4; it extracts `.zip` and supports `--strip-components`). The bootstrap uses these two and nothing else that is preinstalled.
  - Disk: D: 107 GB free, C: 34 GB free. RAM 7.4 GB, 12 logical CPUs. PowerShell ExecutionPolicy: CurrentUser = RemoteSigned.
- Present but deliberately **not** used: system Python 3.14 and 3.10, Temurin JDK 11 (it is on PATH, so our env script must shadow it), CUDA 12.6, Chocolatey, and an old `%USERPROFILE%\.gradle` (1.7 GB, left untouched).

### 1.2 Facts verified (2026-10-02)

| Item | Pinned | Source (checked today) |
| --- | --- | --- |
| uv | 0.12.21 (2026-09-29), `uv-x86_64-pc-windows-msvc.zip`, sha256 `5d223efa0bf00208c3853246af09420419dfbd352536aa6bb8163d6170e23890`. The zip holds `uv.exe`, `uvx.exe` and `uvw.exe` at its top level, so it is extracted with no strip | https://github.com/astral-sh/uv/releases/tag/0.12.21 (checksum also re-computed locally) |
| uv flags | `uv python install --no-bin --no-registry` (env `UV_PYTHON_INSTALL_BIN=0`, `UV_PYTHON_INSTALL_REGISTRY=0`); `UV_PYTHON_INSTALL_DIR`, `UV_PYTHON_PREFERENCE`, `UV_CACHE_DIR`, `UV_TOOL_DIR` exist | https://docs.astral.sh/uv/reference/cli/#uv-python-install · https://docs.astral.sh/uv/reference/environment/ |
| CPython | 3.11.16, the newest 3.11 that uv 0.12.21 offers (python-build-standalone 20260929) | https://github.com/astral-sh/uv/blob/0.12.21/crates/uv-python/download-metadata.json |
| JDK | Temurin 17.0.20.1+1 zip, sha256 `e53a79c3c3d86865bd7e787903884331068e71321714ffd44f145785affc7cb0`, URL `https://github.com/adoptium/temurin17-binaries/releases/download/jdk-17.0.20.1%2B1/OpenJDK17U-jdk_x64_windows_hotspot_17.0.20.1_1.zip` | https://api.adoptium.net/v3/assets/latest/17/hotspot?os=windows&architecture=x64&image_type=jdk |
| Android command-line tools | 23.0: `commandlinetools-win-16111833_latest.zip`, sha1 `57d04f2d75eb8e8fffc5000a987e5de4b5a63e9d`, 154,957,218 bytes | https://dl.google.com/android/repository/repository2-3.xml |
| Android SDK packages | `platform-tools` (sdkmanager installs the latest, 37.0.1 today), `platforms;android-36` (rev 2), `build-tools;36.0.0`, `ndk;28.2.13676358`. API 37 (Android 17) platforms also exist (`android-37.0` to `37.2`) | same XML |
| AGP | 9.1.0, the same as Flutter 3.47.6's template. AGP 9.1.x needs Gradle 9.3.1 (minimum and default), build-tools 36.0.0, JDK 17, defaults to NDK 28.2.13676358, and has a runtime dependency on KGP 2.2.10. 9.1.1 supports API ≤ 37.0 | https://developer.android.com/build/releases/agp-9-1-0-release-notes |
| AGP 9 built-in Kotlin | On by default. Apply only `com.android.application`; never `org.jetbrains.kotlin.android`. `jvmTarget` defaults from `compileOptions`. A newer KGP is chosen with `buildscript { dependencies { classpath("org.jetbrains.kotlin:kotlin-gradle-plugin:<v>") } }` | https://developer.android.com/build/migrate-to-built-in-kotlin · https://developer.android.com/build/releases/agp-9-0-0-release-notes |
| Gradle | 9.3.1 bin, sha256 `b266d5ff6b90eada6dc3b20cb090e3731302e553a27c5d3e4df1f0d76beaff06` (the `-all` zip is `17f277867f6914d61b1aa02efab1ba7bb439ad652ca485cd8ca6842fccec6e43`) | https://services.gradle.org/distributions/gradle-9.3.1-bin.zip.sha256 |
| Kotlin / coroutines | KGP 2.4.0 (Flutter's template version; 2.4.10 and 2.4.20 also exist). kotlinx-coroutines-android 1.11.0 | Maven Central metadata: https://repo1.maven.org/maven2/org/jetbrains/kotlin/kotlin-gradle-plugin/maven-metadata.xml · https://repo1.maven.org/maven2/org/jetbrains/kotlinx/kotlinx-coroutines-android/maven-metadata.xml |
| Flutter | 3.47.6 stable (2026-10-01, Dart 3.13.5). `flutter_windows_3.47.6-stable.zip`, sha256 `a01bb0d26de91bc23c97cd9ccfaad281a612fb8304213fdd5df1119a09404796`, 1,933,193,895 bytes. Fallback if 3.47.6 misbehaves: 3.47.5, sha256 `0ccd71931f49c2fbe394b1eeb6d79af3d624058a043ea0d03d34160581624fb8` | https://storage.googleapis.com/flutter_infra_release/releases/releases_windows.json |
| Flutter's Android template (3.47.6) | Gradle 9.3.1, AGP 9.1.0, KGP 2.4.0, compileSdk 36, targetSdk 36, minSdk 24, NDK 28.2.13676358, Java ≥ 17. Its `gradle.properties` sets **`org.gradle.jvmargs=-Xmx8G`** plus `android.newDsl=false` and `android.builtInKotlin=false` | https://github.com/flutter/flutter/blob/3.47.6/packages/flutter_tools/lib/src/android/gradle_utils.dart · .../templates/app/android.tmpl/gradle.properties.tmpl |
| Flutter path rule | "Select a location that doesn't have special characters or spaces in its path." There is also an open bug where Flutter fails when the SDK path contains a space | https://docs.flutter.dev/install/manual · https://github.com/flutter/flutter/issues/173716 |
| ktlint | 1.8.0 (2025-11-14; the project moved to github.com/ktlint). Asset `ktlint` is a self-executing jar, run as `java -jar`, sha256 `a3fd620207d5c40da6ca789b95e7f823c54e854b7fade7f613e91096a3706d75` | https://github.com/ktlint/ktlint/releases/tag/1.8.0 |
| scrcpy | 4.1 (2026-07-12), `scrcpy-win64-v4.1.zip`, sha256 `5b12172b3264b2889f4583ee64752ce832e29bc8b1089dca81093459697165db`, top folder `scrcpy-win64-v4.1/`. Headless record: `scrcpy --no-window --no-audio --record=f.mp4 --time-limit=5`. The `ADB` env var selects which adb to use | https://github.com/Genymobile/scrcpy/releases/tag/v4.1 · https://github.com/Genymobile/scrcpy/blob/v4.1/doc/recording.md · app/scrcpy.1 |
| ffmpeg | 9.0.2 essentials, `ffmpeg-9.0.2-essentials_build.zip`, sha256 `60f467265b1e312373dbcd92200c2618a74850f98d3d078e94296bb3fa2047ba`. It includes `ffprobe.exe` | https://github.com/GyanD/codexffmpeg/releases/tag/9.0.2 |
| Python packages (newest that support Python 3.11 on win_amd64) | numpy 2.4.6 (numpy 2.5.x needs Python ≥ 3.12), opencv-python 4.14.0.94, pillow 12.3.0, pydantic 2.13.5, jsonschema 4.26.0, referencing 0.37.0, flask 3.1.3, onnx 1.23.1, onnxruntime 1.30.0, huggingface_hub 2.1.1, qai-hub 0.56.0, pytest 9.1.1, ruff 0.16.10, pre-commit 4.6.2, datamodel-code-generator 0.83.0, hatchling 1.32.4. ML group: torch 2.14.1, torchvision 0.29.1, transformers 5.18.0 (accepts huggingface-hub <3), ultralytics 8.4.171 | https://pypi.org/pypi/<name>/json (each one checked) |
| protobuf window | qai-hub 0.56.0 needs `protobuf<=6.31.1`. onnx 1.23.1 needs `protobuf>=6.31.1`. The only overlap is **6.31.1**, which exists and has a win_amd64 abi3 wheel | PyPI `requires_dist` |
| qai-hub API (0.56.0) | `submit_profile_job` is deprecated; use `submit_inference_job(model, device, profile=True)` → `InferenceJob.download_profile()["execution_summary"]["estimated_inference_time"]` (µs). `get_devices()` returns `Device(name, os, attributes)`. The token lives in `~/.qai_hub/client.ini` (or the file named by env `QAIHUB_CLIENT_INI`). CLI: `qai-hub configure --api_token`, `qai-hub list-devices` | the wheel's `qai_hub/client.py` and `qai_hub/_cli.py` (downloaded to scratch and read) · https://workbench.aihub.qualcomm.com/docs/hub/generated/qai_hub.get_devices.html |
| AI Hub devices | "Snapdragon 8 Elite Gen 5 QRD" was **removed on 2026-09-28**. The replacement is "Samsung Galaxy S26 (Family)" (Snapdragon 8 Elite Gen 5 for Galaxy, SM8850-AD, listed since 2026-06-09). Its chipset attribute should read `chipset:qualcomm-snapdragon-8-elite-gen5`, but this is unverified without a token, so code matches it with a regex | https://workbench.aihub.qualcomm.com/docs/hub/release_notes.html |
| Hugging Face | `google/siglip2-base-patch16-224` is public and not gated, so anonymous download works. The CLI is `hf` (`hf auth login`) | https://huggingface.co/api/models/google/siglip2-base-patch16-224 |
| pre-commit | 4.4.0 added `language: unsupported` (the new name for `system`); 4.6.2 is current | https://github.com/pre-commit/pre-commit/blob/v4.6.2/CHANGELOG.md |
| datamodel-code-generator | 0.83.0 flags exist: `--input-file-type jsonschema`, `--output-model-type pydantic_v2.BaseModel`, `--target-python-version`, `--use-standard-collections`, `--use-union-operator`, `--enum-field-as-literal`, `--use-schema-description`, `--use-field-description`, `--field-constraints`, `--use-double-quotes`, `--disable-timestamp`, `--use-title-as-name`, `--extra-fields`, `--use-one-literal-as-default`, `--formatters` (accepts `builtin`) | https://github.com/koxudaxi/datamodel-code-generator/blob/0.83.0/src/datamodel_code_generator/arguments.py |
| Target phone | iQOO 15: Snapdragon 8 Elite Gen 5 (SM8850-AC), Android 16, OriginOS 6, 2K 144 Hz LTPO. `ro.board.platform` = `canoe` is **unverified**; the chip check therefore relies on `ro.soc.model` | https://www.gsmarena.com/vivo_iqoo_15_5g-14198.php |
| Accessibility service declaration | `android:permission="android.permission.BIND_ACCESSIBILITY_SERVICE"`, `android:exported="true"`, intent-filter `android.accessibilityservice.AccessibilityService`, `<meta-data android:name="android.accessibilityservice" …>`. The restricted-settings path is App info → ⋮ → Allow restricted settings | https://developer.android.com/guide/topics/ui/accessibility/service · https://support.google.com/android/answer/12623953 |

### 1.3 Deviations from PLAN.md (none changes a threshold, a deliverable or a guarantee)

- **DV-1 · Toolchain location.** The orchestrator chose `D:\iqoo finale\toolchain`, but that path contains a space, which Flutter's docs forbid (see 1.2). The toolchain therefore goes to the first of these that has no whitespace:
  1. `-ToolchainDir` / `$env:VEIL_TOOLCHAIN`;
  2. `<parent of repo>\toolchain`;
  3. `<drive of repo>\veil-toolchain`.
  
  On this laptop that is **`D:\veil-toolchain`**. It is still outside the repo, on D:, with no PATH or registry changes and no admin. The repository path `D:\iqoo finale\veil` keeps its space; see risk R1.
- **DV-2 · No Android Studio.** PLAN's Test bench lists Android Studio. Tonight we use the portable command-line SDK and Temurin JDK 17 instead (orchestrator decision; ORCHESTRATOR ground rule 4's "Android Studio jbr" becomes "toolchain jdk17"). Android Studio's Profiler and Database Inspector are first needed in 3.3 and 5.1. Perfetto works in the browser. The user may install Android Studio later; nothing in this phase depends on it.
- **DV-3 · Heavy ML packages declared, not installed.** PLAN 1.1.1 Do 2 says to "add" torch, open_clip_torch or transformers, and ultralytics. They are added to `pyproject.toml` in a dependency group `ml`, with pinned versions resolved into `uv.lock`, but not installed until Phase 1.3 (`uv sync --group ml`). transformers is chosen over open_clip_torch, since PLAN says "or" and SigLIP2's reference implementation is in transformers. The PyPI torch wheel is CPU-only on Windows; 1.3's Refiner picks the CUDA index for the GTX 1650 Ti. No AC needs them.
- **DV-4 · Hugging Face token optional.** All planned models are public (verified for SigLIP2). The bench checks anonymous download. Creating a token stays in the human sitting as optional (PLAN 1.1.3 Do 5).
- **DV-5 · The 16th contract type is `ScreenLabel`.** PLAN lists 15 types in 1.1.2 Do 1, while AC-1.1-03 and the deliverables say 16. The 16th is the screenshot label format, because PLAN 1.2's entry condition reads "Phase 1.1 accepted (**the label format schema exists**)". The other candidates belong to later phases: `Tape` is a named 2.1 deliverable (`contracts/tape.schema.json`), and `LookRequest` is fixed by 2.2's guarantee. Both are added by those phases as v1.1 additions. This is recorded as decision D-003 and in `contracts/README.md` for owner approval (AC-1.1-05).
- **DV-6 · `Rect` is an object `{x, y, w, h}`, not the array `[x, y, w, h]` from PLAN 1.2.2's example.** An object can carry `contractVersion` (AC-1.1-04) and gives clean typed models. 1.2's label export uses `ScreenLabel`, whose boxes hold this Rect.
- **DV-7 · UiEvent has 6 valid examples, one per event kind,** instead of "2-3". AC-1.1-03 only asks for at least 2.
- **DV-8 · AI Hub device for the "same chip family" check:** "Samsung Galaxy S26 (Family)" (8 Elite Gen 5 for Galaxy, SM8850-AD), because the QRD was removed on 2026-09-28. The iQOO is SM8850-AC, so it is the same family.
- **DV-9 · HC-001 (manual system-wide installs) is superseded** by `tools\bootstrap.ps1`. The user only confirms `bootstrap.ps1 -CheckOnly` (Human sitting step 1).
- **Test Feed app: built now, not deferred.** Its first version (placeholder blocks, ruler, position and tap log) is part of 1.1.3, as PLAN's proof test needs it. Real cat, spider and Layer 1 images come with the phases that need them.

### 1.4 Risks and how this spec handles them

| # | Risk | Handling |
| --- | --- | --- |
| R1 | The repo path `D:\iqoo finale\veil` contains a space. Gradle and Flutter Android builds usually cope (no native code, and the SDKs are on a space-free path), but this is not guaranteed | All SDKs, caches and the toolchain live on a space-free path (DV-1). If `flutter build apk` or Gradle fails with a path cut at `D:\iqoo`, the Builder stops and reports SPEC_ISSUE with the log. It must not move the repo. The repair option is to build through a `subst` drive, which needs orchestrator approval |
| R2 | AGP 9 built-in Kotlin with a KGP 2.4.0 override is a new combination | Gradle 9.3.1, AGP 9.1.0 and KGP 2.4.0 are exactly Flutter 3.47.6's tested set. Fallback: delete the `buildscript {}` block, so AGP's bundled KGP 2.2.10 is used, and record it. Do **not** opt out of built-in Kotlin |
| R3 | 7.4 GB RAM. Flutter's template asks Gradle for an 8 GB heap, and Gradle and Kotlin daemons linger | Every Gradle project sets `-Xmx2g`, `org.gradle.daemon=false`, `org.gradle.workers.max=2` and `kotlin.compiler.execution.strategy=in-process`. Verification uses `--no-daemon`. Only one heavy build runs at a time (wave plan, bench order). If an OutOfMemoryError appears, raise to `-Xmx3g` in that project only and record it |
| R4 | Narrow dependency windows: protobuf must be 6.31.1, and numpy is capped at 2.4.x by Python 3.11 | Exact pins plus a committed `uv.lock`. If `uv lock` fails because of the `ml` group, the Builder may move an `ml` pin to the newest version that resolves within the same major, and must record it. Main pins stay unchanged |
| R5 | About 4.5 GB of downloads (Flutter alone is 1.9 GB, the NDK 0.75 GB); Windows Defender slows extraction | Downloads go to `<toolchain>\_downloads\`, are SHA-checked and skipped when already present. The bootstrap is idempotent and resumable. Expect 30-60 min on first run |
| R6 | vivo/OriginOS may ask for an on-phone confirmation for each `adb install` | Bench check skips installs whose APK is already on the phone byte-for-byte (sha256 compare). The first install happens in the Human sitting, while the user watches the phone |
| R7 | The phone may already run Android 17 (API 37) | `targetSdk = 36` runs fine on 37. The device profile records the real SDK. Moving to 37 later needs `platforms;android-37.0` and AGP ≥ 9.1.1, and is noted for the next Refiner |
| R8 | datamodel-code-generator can choke on `if/then/else` or cross-file `$ref` | The generator bundles all schemas into one file with local refs only and strips `if`, `then` and `else`. The JSON Schema stays the authority: the models are typing helpers, and `jsonschema` does all validation |
| R9 | The pre-commit hook calls `uv`, `java` and `dart` from the toolchain, so a commit from a bare shell fails | The orchestrator commits from an env-loaded shell (section 3.6) |
| R10 | `sdkmanager --licenses` accepts Google's SDK licences on the user's behalf | Done by the bootstrap and logged in `<toolchain>\bootstrap.log`. The orchestrator must report it to the user as an FYI item (Human sitting step 0) |
| R11 | `ro.board.platform` for SM8850 is unknown (likely `canoe`) | The chip-family rule is `ro.soc.model` starting with `SM8850`, OR `ro.board.platform == "canoe"`. Anything else is FLAGGED in `docs/decisions.md` |
| R12 | No phone and no AI Hub token tonight | Everything is built so those checks run the moment they exist. Until then the bench check reports those lines as `SKIP` with a reason, and its exit code is 2 |

### 1.5 PLAN step map (every "Do" step and fixture → where it is in this spec)

| PLAN | Spec |
| --- | --- |
| 1.1.1 Do 1: repo, layout, README | 1.1.1 steps 1, 2, 13 |
| 1.1.1 Do 2: Python 3.11, venv, packages | Section 3.4; 1.1.1 step 8 (DV-3 for torch, transformers, ultralytics) |
| 1.1.1 Do 3: Android, empty `guard/` app targeting the phone's Android version, Kotlin + coroutines | 1.1.1 steps 7 and 9: targetSdk 36 = the iQOO 15's Android 16, confirmed by AC-1.1-06; DV-2; R7 |
| 1.1.1 Do 4: Flutter SDK, empty `console/` app, runs on the phone | 1.1.1 steps 7 and 10; the phone launch is the `console-app` bench line |
| 1.1.1 Do 5: pre-commit with ruff, ktlint, dart format | 1.1.1 step 11 |
| 1.1.1 Do 6: `docs/decisions.md` with decision #1 | 1.1.1 step 12 (D-001) |
| 1.1.2 Do 1: schemas for the types | 1.1.2 steps 1-3 (16 types; DV-5) |
| 1.1.2 Do 2: conventions; `contractVersion` | 1.1.2 step 2 (CONVENTIONS, contractVersion) |
| 1.1.2 Do 3: the `spaceId` rule in the schema description | 1.1.2 step 2 (SPACE_RULE) and `rules.py` |
| 1.1.2 Do 4: generate pydantic models (Kotlin and Dart later) | 1.1.2 step 7; Kotlin and Dart are out of scope |
| 1.1.2 Do 5: 2-3 examples per schema | 1.1.2 step 5 (plus invalid examples; DV-7) |
| 1.1.2 Do 6: validation test | 1.1.2 step 8 |
| 1.1.3 Do 1: Developer options, USB debugging, adb | Human sitting step 2; `adb` bench line |
| 1.1.3 Do 2: record `ro.soc.model` and `ro.board.platform`; flag a non-8-Elite-Gen-5 chip | 1.1.3 steps 2 and 5 (`device_profile`, `update_decisions`) |
| 1.1.3 Do 3: `docs/device-profile.md` | 1.1.3 step 5; row P1 |
| 1.1.3 Do 4: AI Hub account, `qai-hub configure`, list devices | Human sitting step 4; `aihub-*` bench lines; AC-1.1-07 |
| 1.1.3 Do 5: Hugging Face account and token | Human sitting step 5 (optional, DV-4); `huggingface` bench line |
| 1.1.3 Do 6: sideloaded accessibility service and the restricted-settings path | Probe service (1.1.1 step 9); Human sitting step 7; `a11y_probe` |
| Test fixture 1: Test Feed app | 1.1.3 step 1 (v1) |
| Test fixture 2: driver scripts | 1.1.3 step 2 (`adb.py`, `drive.py`, first version) |
| Test fixtures 3-5: Guard debug log, checker scripts, test accounts | Not in 1.1. They are built with 4.x, 5.2 and 2.3; test accounts are HC-004, needed from 1.2 |
| Proof test PT-1.1 | Section 6; `bench_check` |

---

## 2. Waves

```
Wave 1: 1.1.1                  (phone: no · heavy build: YES — downloads ~4.5 GB, Gradle + Flutter builds)
Wave 2: 1.1.2 ∥ 1.1.3          (phone: 1.1.3 only, and only after HC-002 · heavy build: 1.1.3 only — Gradle :testfeed)
Phase verification (after wave 2, one at a time):
  a. AUTO checks (orchestrator)
  b. CLEAN check AC-1.1-01 (Checker; heavy: fresh toolchain download + all builds; nothing else may run)
  c. PHONE checks + proof test, once the Human sitting is done (orchestrator)
```

- Wave 2's owned paths are disjoint (see section 4). 1.1.2 is light: Python and JSON only. 1.1.3 is the only one that builds with Gradle.
- 1.1.2 and 1.1.3 both need what 1.1.1 creates (toolchain, `pyproject.toml`, `uv.lock`, the guard Gradle project), so neither can start in wave 1.
- Rough wall time: wave 1 is 2-3 h (mostly downloads). In wave 2, 1.1.2 takes about 1-1.5 h and 1.1.3 about 1.5-2 h. The CLEAN check takes 1.5-2 h, because it re-downloads everything.

---

## 3. Shared setup

All of it is created by **1.1.1** and is read-only for 1.1.2 and 1.1.3.

### 3.1 Toolchain layout (outside the repo; not in git)

```
D:\veil-toolchain\                (= $env:VEIL_TOOLCHAIN; rule in DV-1)
  _downloads\                     verified archives (kept, so re-runs skip downloads)
  uv\uv.exe uvx.exe uvw.exe
  python\                         uv-managed CPython 3.11.16 (UV_PYTHON_INSTALL_DIR)
  jdk17\bin\java.exe              Temurin 17.0.20.1+1
  gradle\bin\gradle.bat           Gradle 9.3.1 (only used to generate wrappers)
  android-sdk\                    ANDROID_HOME
    cmdline-tools\latest\bin\sdkmanager.bat
    platform-tools\adb.exe
    platforms\android-36\  build-tools\36.0.0\  ndk\28.2.13676358\  licenses\
  flutter\bin\flutter.bat         Flutter 3.47.6
  scrcpy\scrcpy.exe               scrcpy 4.1
  ffmpeg\bin\ffmpeg.exe ffprobe.exe
  ktlint\ktlint.jar               ktlint 1.8.0
  uv-tools\  uv-tools\bin\        UV_TOOL_DIR / UV_TOOL_BIN_DIR
  cache\uv  cache\gradle  cache\pub  cache\pip  cache\huggingface  cache\torch  cache\ultralytics  cache\pre-commit
  bootstrap.log
  <each component dir>\.veil-pin  marker: "<version> <hash>"
```

Caches under `cache\` are shared by every Builder and every build. They are not "owned" source, so writing to them is allowed.

### 3.2 Environment set by `tools\env.ps1` / `tools/env.sh` (current shell only)

| Variable | Value |
| --- | --- |
| `VEIL_TOOLCHAIN` | resolved toolchain dir (DV-1) |
| `VEIL_REPO` | repo root |
| `JAVA_HOME` | `%VEIL_TOOLCHAIN%\jdk17` |
| `ANDROID_HOME`, `ANDROID_SDK_ROOT` | `%VEIL_TOOLCHAIN%\android-sdk` |
| `ADB` | `%ANDROID_HOME%\platform-tools\adb.exe` (so scrcpy uses the same adb) |
| `GRADLE_USER_HOME` | `%VEIL_TOOLCHAIN%\cache\gradle` |
| `PUB_CACHE` | `%VEIL_TOOLCHAIN%\cache\pub` |
| `UV_CACHE_DIR` | `%VEIL_TOOLCHAIN%\cache\uv` |
| `UV_PYTHON_INSTALL_DIR` | `%VEIL_TOOLCHAIN%\python` |
| `UV_PYTHON_PREFERENCE` | `only-managed` (never the system Python 3.10/3.14) |
| `UV_PYTHON_INSTALL_BIN` | `0` |
| `UV_PYTHON_INSTALL_REGISTRY` | `0` |
| `UV_TOOL_DIR`, `UV_TOOL_BIN_DIR` | `%VEIL_TOOLCHAIN%\uv-tools`, `%VEIL_TOOLCHAIN%\uv-tools\bin` |
| `PIP_CACHE_DIR` | `%VEIL_TOOLCHAIN%\cache\pip` |
| `HF_HOME` | `%VEIL_TOOLCHAIN%\cache\huggingface` |
| `TORCH_HOME` | `%VEIL_TOOLCHAIN%\cache\torch` |
| `YOLO_CONFIG_DIR` | `%VEIL_TOOLCHAIN%\cache\ultralytics` |
| `PRE_COMMIT_HOME` | `%VEIL_TOOLCHAIN%\cache\pre-commit` |
| `PYTHONUTF8` | `1` |
| `PATH` (prepended, no duplicates when re-sourced) | `uv`, `jdk17\bin`, `android-sdk\platform-tools`, `android-sdk\cmdline-tools\latest\bin`, `flutter\bin`, `scrcpy`, `ffmpeg\bin`, `gradle\bin`, `uv-tools\bin` |
| `env.sh` only | `MSYS_NO_PATHCONV=1` and `MSYS2_ARG_CONV_EXCL=*` (stops Git Bash from mangling `/sdcard/...` adb arguments). Windows-form values for the variables above; POSIX-form PATH entries via `cygpath` |

adb keys (`%USERPROFILE%\.android\adbkey`), the debug keystore and tiny tool configs stay in their default user-profile places. That keeps the phone's "always allow" pairing stable across shells.

### 3.3 `tools\toolchain.json` (pins; the single source of truth for the bootstrap)

```json
{
  "pinsVersion": 1,
  "archives": [
    {"name": "uv", "version": "0.12.21", "url": "https://github.com/astral-sh/uv/releases/download/0.12.21/uv-x86_64-pc-windows-msvc.zip", "sha256": "5d223efa0bf00208c3853246af09420419dfbd352536aa6bb8163d6170e23890", "dir": "uv", "strip": 0},
    {"name": "jdk", "version": "17.0.20.1+1", "url": "https://github.com/adoptium/temurin17-binaries/releases/download/jdk-17.0.20.1%2B1/OpenJDK17U-jdk_x64_windows_hotspot_17.0.20.1_1.zip", "sha256": "e53a79c3c3d86865bd7e787903884331068e71321714ffd44f145785affc7cb0", "dir": "jdk17", "strip": 1},
    {"name": "gradle", "version": "9.3.1", "url": "https://services.gradle.org/distributions/gradle-9.3.1-bin.zip", "sha256": "b266d5ff6b90eada6dc3b20cb090e3731302e553a27c5d3e4df1f0d76beaff06", "dir": "gradle", "strip": 1},
    {"name": "android-cmdline-tools", "version": "23.0", "url": "https://dl.google.com/android/repository/commandlinetools-win-16111833_latest.zip", "sha1": "57d04f2d75eb8e8fffc5000a987e5de4b5a63e9d", "dir": "android-sdk/cmdline-tools/latest", "strip": 1},
    {"name": "flutter", "version": "3.47.6", "url": "https://storage.googleapis.com/flutter_infra_release/releases/stable/windows/flutter_windows_3.47.6-stable.zip", "sha256": "a01bb0d26de91bc23c97cd9ccfaad281a612fb8304213fdd5df1119a09404796", "dir": "flutter", "strip": 1},
    {"name": "scrcpy", "version": "4.1", "url": "https://github.com/Genymobile/scrcpy/releases/download/v4.1/scrcpy-win64-v4.1.zip", "sha256": "5b12172b3264b2889f4583ee64752ce832e29bc8b1089dca81093459697165db", "dir": "scrcpy", "strip": 1},
    {"name": "ffmpeg", "version": "9.0.2", "url": "https://github.com/GyanD/codexffmpeg/releases/download/9.0.2/ffmpeg-9.0.2-essentials_build.zip", "sha256": "60f467265b1e312373dbcd92200c2618a74850f98d3d078e94296bb3fa2047ba", "dir": "ffmpeg", "strip": 1},
    {"name": "ktlint", "version": "1.8.0", "url": "https://github.com/ktlint/ktlint/releases/download/1.8.0/ktlint", "sha256": "a3fd620207d5c40da6ca789b95e7f823c54e854b7fade7f613e91096a3706d75", "dir": "ktlint", "file": "ktlint.jar"}
  ],
  "androidPackages": ["platform-tools", "platforms;android-36", "build-tools;36.0.0", "ndk;28.2.13676358"],
  "python": "3.11.16"
}
```

### 3.4 Python project (`pyproject.toml`, verbatim)

```toml
[project]
name = "veil-workshop"
version = "0.1.0"
description = "Veil Workshop: Python twin, evaluation, model export, bench tools and contract types"
requires-python = ">=3.11,<3.12"
dependencies = [
  "numpy==2.4.6",
  "opencv-python==4.14.0.94",
  "pillow==12.3.0",
  "pydantic==2.13.5",
  "jsonschema==4.26.0",
  "referencing==0.37.0",
  "flask==3.1.3",
  "onnx==1.23.1",
  "onnxruntime==1.30.0",
  "huggingface_hub==2.1.1",
  "qai-hub==0.56.0",
]

[dependency-groups]
dev = [
  "pytest==9.1.1",
  "ruff==0.16.10",
  "pre-commit==4.6.2",
  "datamodel-code-generator==0.83.0",
]
# Installed from Phase 1.3 with `uv sync --group ml` (DV-3). Pinned and locked now.
ml = [
  "torch==2.14.1",
  "torchvision==0.29.1",
  "transformers==5.18.0",
  "ultralytics==8.4.171",
]

[tool.uv]
default-groups = ["dev"]
environments = ["sys_platform == 'win32'", "sys_platform == 'linux'"]

[build-system]
requires = ["hatchling==1.32.4"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["workshop"]

[tool.ruff]
line-length = 100
target-version = "py311"
extend-exclude = ["workshop/contracts/models.py", "console", "guard"]

[tool.ruff.lint]
select = ["E", "F", "W", "I", "B", "UP"]

[tool.pytest.ini_options]
addopts = "-ra --import-mode=importlib"
testpaths = ["workshop", "contracts"]
```

Also create `.python-version` with the single line `3.11.16`.

### 3.5 How commands are written in this spec

- Every command runs in **Windows PowerShell 5.1** with the working directory `D:\iqoo finale\veil`, unless it says otherwise.
- **`WE <cmd>`** is shorthand for `powershell -NoProfile -ExecutionPolicy Bypass -File tools\with-env.ps1 <cmd>`. It loads `tools\env.ps1`, then runs `<cmd>` from the repo root. With a leading `--cd <dir>`, it runs from `<dir>` (relative to the repo root) instead.
- From Git Bash use `cd "/d/iqoo finale/veil" && powershell.exe -NoProfile -ExecutionPolicy Bypass -File tools/with-env.ps1 <cmd>`, or `source tools/env.sh && <cmd>`.
- Never run two heavy commands at once. Heavy means: Gradle builds, `flutter build`, the bootstrap, the bench check with builds, and AI Hub plus model work.

### 3.6 Notes for the orchestrator (not Builder work)

- **Before wave 1**, save these three values to evidence, to prove later that nothing persistent changed:
  1. `powershell -NoProfile -Command "[Environment]::GetEnvironmentVariable('Path','User')"` → `evidence\userpath-before.txt`;
  2. the same for `'JAVA_HOME','User'`;
  3. `Test-Path HKCU:\Software\Python\Astral`.
- **Commits** trigger the pre-commit hook, which needs the toolchain. Commit from Git Bash as `cd "/d/iqoo finale/veil" && source tools/env.sh && git add -A && git commit -F <msgfile>`. If the hook fails, that is a Builder fix (prompt F), never a `--no-verify`.
- **Licences (R10):** add the FYI "Android SDK licences accepted by the bootstrap" to the human sitting.
- `veil/docs/acceptance/1.1.md` is the orchestrator's file. Builders must not create `docs/acceptance/`.

---

## 4. Sub-phase 1.1.1 Repository and tools

- **Goal:** a `veil/` git repository with PLAN's layout, a portable one-command toolchain bootstrap, a pinned Python 3.11 environment, a hello Guard app (Kotlin + coroutines) and a hello Console app (Flutter) that build from a clean checkout, a formatting pre-commit hook, `docs/decisions.md` with decision #1, and a README that a newcomer can follow.
- **Owned paths:** all of `D:\iqoo finale\veil\`, **except** `contracts/**`, `workshop/contracts/**`, `workshop/bench/**`, `guard/testfeed/**`, `tools/bench_check.ps1`, `tools/bench_check.sh`, `docs/device-profile.md`, `docs/bench-check.md` and `docs/acceptance/**`.
  - The toolchain dir `D:\veil-toolchain\**`, created by running the bootstrap.
- **Read-only inputs:** this spec; `D:\iqoo finale\PLAN.md` (Appendix C for D-001).

### Steps

1. **Create the repo.** `New-Item -ItemType Directory "D:\iqoo finale\veil"`, then `git -C "D:\iqoo finale\veil" init -b main`.
   - Do not commit.
   - Create these folders, each with the file listed:
     - `contracts/` (leave empty; 1.1.2 fills it; git does not track empty dirs);
     - `workshop/` with `__init__.py` holding the docstring `"""Veil Workshop: twin, evaluation, model export, bench tools."""`;
     - `guard/`;
     - `console/`;
     - `data/README.md`;
     - `docs/`;
     - `tools/hooks/`.
2. **`.gitignore`** (verbatim):
   ```gitignore
   # Private data (AC-1.1-08): never committed
   /data/*
   !/data/README.md

   # Python
   .venv/
   __pycache__/
   *.py[cod]
   .pytest_cache/
   .ruff_cache/

   # Android / Gradle
   .gradle/
   .kotlin/
   build/
   local.properties
   captures/
   .cxx/
   *.iml
   .idea/

   # Flutter (console/.gitignore covers the rest)
   .dart_tool/

   # OS / editors
   .DS_Store
   Thumbs.db
   .vscode/
   ```
   **`.gitattributes`** (verbatim):
   ```gitattributes
   * text=auto
   *.bat text eol=crlf
   *.cmd text eol=crlf
   *.ps1 text eol=crlf
   *.sh text eol=lf
   gradlew text eol=lf
   *.jar binary
   *.png binary
   *.apk binary
   ```
   **`.editorconfig`** (verbatim):
   ```ini
   root = true

   [*]
   charset = utf-8
   end_of_line = lf
   insert_final_newline = true
   indent_style = space
   indent_size = 4

   [*.{kt,kts}]
   ktlint_code_style = android_studio
   max_line_length = 120

   [*.{json,yaml,yml,dart,toml}]
   indent_size = 2

   [*.{bat,cmd,ps1}]
   end_of_line = crlf
   ```
   **`data/README.md`:** 6-10 lines. Explain that `data/` is private and git-ignored (screenshots, recordings, labels, evidence), that it is never pushed to public remotes, and list the planned subfolders: `screens/` (1.2), `labels/` (1.2), `recordings/` (2.1) and `evidence/<phase>/`.
3. **`tools\toolchain.json`**: exactly the content in section 3.3.
4. **`tools\toolchain-dir.ps1`**: defines one function.
   ```powershell
   function Resolve-VeilToolchainDir {
     param([Parameter(Mandatory)][string]$RepoRoot, [string]$Override = "")
     # Order: $Override; $env:VEIL_TOOLCHAIN; "<parent of RepoRoot>\toolchain" if it has no whitespace;
     # otherwise "<drive root of RepoRoot>veil-toolchain" (e.g. D:\veil-toolchain).
     # Throw "Toolchain path must not contain spaces: <p>. Set VEIL_TOOLCHAIN to a path without spaces." if the result has whitespace.
     # Return the full path without a trailing backslash.
   }
   ```
5. **`tools\env.ps1`**, dot-sourced as `. .\tools\env.ps1`:
   - `$repo = Split-Path -Parent $PSScriptRoot`;
   - dot-source `toolchain-dir.ps1`;
   - `$tc = Resolve-VeilToolchainDir -RepoRoot $repo`;
   - set every variable in section 3.2 for the current process;
   - prepend the PATH entries after first removing any existing PATH entries that start with `$tc`, so the result is idempotent;
   - print one line, `Veil env: toolchain=<tc>`, unless `$env:VEIL_ENV_QUIET -eq '1'`.
   
   It must not call `[Environment]::SetEnvironmentVariable` or `setx`, or write to the registry or profile files.

   **`tools/env.sh`**, for Git Bash, sourced as `source tools/env.sh`:
   - computes the same rule using `cygpath -w`/`cygpath -u` (a parent path containing a space → `<drive>:\veil-toolchain`);
   - exports the same variables, Windows-form for the `*_HOME`/`*_DIR` values, POSIX-form for PATH;
   - also exports `MSYS_NO_PATHCONV=1` and `MSYS2_ARG_CONV_EXCL='*'`.
6. **`tools\with-env.ps1`** (verbatim logic; it reads `$args` and has no `param` block, so flags like `-q` pass through):
   ```powershell
   $ErrorActionPreference = 'Stop'
   $env:VEIL_ENV_QUIET = '1'
   . "$PSScriptRoot\env.ps1"
   $repo = Split-Path -Parent $PSScriptRoot
   $a = @($args)
   if ($a.Count -ge 2 -and $a[0] -eq '--cd') { Set-Location (Join-Path $repo $a[1]); $a = @($a | Select-Object -Skip 2) } else { Set-Location $repo }
   if ($a.Count -lt 1) { Write-Error 'usage: with-env.ps1 [--cd <dir>] <command> [args...]' }
   $exe = $a[0]; $rest = @($a | Select-Object -Skip 1)
   $ErrorActionPreference = 'Continue'
   & $exe @rest
   exit $LASTEXITCODE
   ```
7. **`tools\bootstrap.ps1`**, the one-command setup.
   - Signature: `param([string]$ToolchainDir = "", [switch]$CheckOnly, [switch]$NoRepoSetup)`.
   - Set `$ErrorActionPreference='Stop'` and `$ProgressPreference='SilentlyContinue'`.
   - Write every native call through a helper `Invoke-Native([string]$Exe, [string[]]$Arguments, [string]$StdinText = $null)`. The helper:
     - sets `$ErrorActionPreference='Continue'` locally (this matters on PowerShell 5.1: native stderr plus `2>&1` would otherwise throw);
     - captures `& $Exe @Arguments 2>&1 | ForEach-Object { "$_" }`, piping `$StdinText` into it when given;
     - returns `[pscustomobject]@{ ExitCode = $LASTEXITCODE; Output = <string[]> }`;
     - appends everything to `bootstrap.log` with timestamps.
   
   Algorithm:
   1. `$repo = Split-Path -Parent $PSScriptRoot`. Dot-source `toolchain-dir.ps1`. `$tc = Resolve-VeilToolchainDir -RepoRoot $repo -Override $ToolchainDir`. Set `$env:VEIL_TOOLCHAIN = $tc`. Create `$tc`, `$tc\_downloads` and the `cache\*` subdirs from section 3.1. Print `Toolchain: <tc>`.
   2. Unless `-CheckOnly`:
      1. **Free space.** If any component's `.veil-pin` is missing or out of date and the drive of `$tc` has less than 15 GB free, stop with an error.
      2. **Archives.** For each entry of `archives` in `toolchain.json`, in order:
         - If `$tc\<dir>\.veil-pin` equals `"<version> <hash>"`, print `<name> <version>: already installed` and move on.
         - Otherwise download to `$tc\_downloads\<last URL segment, URL-decoded>`. If that file already exists with the right hash, skip the download. If not, run `curl.exe -L --fail --retry 5 --retry-delay 5 -sS -o "<file>.part" <url>`, then rename to `<file>`.
         - Verify the SHA-256, or SHA-1 when the pin has `sha1`, with `Get-FileHash`. On a mismatch, delete the file and throw.
         - Delete `$tc\<dir>` if it exists, then create it.
         - Extract with `& "$env:SystemRoot\System32\tar.exe" -xf <file> -C $tc\<dir> --strip-components <strip>`.
         - For `ktlint`, which has `file` instead of `strip`, copy the download to `$tc\ktlint\ktlint.jar` instead of extracting.
         - Write `.veil-pin`.
      3. Dot-source `env.ps1` with `$env:VEIL_ENV_QUIET='1'`.
      4. **Android licences.** Run `sdkmanager.bat --sdk_root=$env:ANDROID_HOME --licenses` with StdinText = 60 lines of `y`. Expect exit 0 and the file `$env:ANDROID_HOME\licenses\android-sdk-license`. Log the licence file names. Fallback if piping fails: `cmd.exe /c "(for /l %i in (1,1,60) do @echo y) | sdkmanager.bat --sdk_root=$env:ANDROID_HOME --licenses"`. The toolchain path has no spaces, so no quoting is needed.
      5. **Android packages.** `sdkmanager.bat --sdk_root=$env:ANDROID_HOME --install <each androidPackages entry>`. Expect exit 0.
      6. **Python.** `uv python install <python> --no-bin --no-registry`.
      7. **Flutter.** `flutter.bat --version`, which on first run sets up the Dart SDK. Then `flutter.bat precache --android`. Then `flutter.bat doctor -v`, which is logged only and never fails the bootstrap.
      8. **Repo setup**, unless `-NoRepoSetup` or `uv.lock` is absent: `uv sync --locked` in `$repo`. If `$repo\.git` exists, also run `uv run --no-sync pre-commit install`.
   3. **Checks (always).** Dot-source `env.ps1` with `$env:VEIL_ENV_QUIET='1'`, then evaluate each row and print a table `component | expected | found | OK/FAIL`.

      | Component | Command | Expected in the output |
      | --- | --- | --- |
      | `uv` | `uv --version` | `0.12.21`, and `(Get-Command uv).Source` is under `$tc` |
      | `java` | `java -version` | `"17.0.20.1"`, and `(Get-Command java).Source` is under `$tc` |
      | `gradle` | `gradle --version` | `Gradle 9.3.1` |
      | `android-sdk` | `sdkmanager.bat --sdk_root=$env:ANDROID_HOME --list_installed` | lists `platforms;android-36`, `build-tools;36.0.0`, `ndk;28.2.13676358` and `platform-tools` |
      | `adb` | `adb version` | `Android Debug Bridge`, and the source is under `$tc` |
      | `flutter` | `flutter.bat --version --machine` | JSON `frameworkVersion` is `3.47.6` |
      | `scrcpy` | `scrcpy --version` | first line starts with `scrcpy 4.1` |
      | `ffmpeg` | `ffmpeg -version` | first line contains `9.0.2` |
      | `ktlint` | `java -jar $tc\ktlint\ktlint.jar --version` | `1.8.0` |
      | `python` | `uv python find 3.11.16` | a path under `$tc\python` |
      | `repo-venv` | `uv run --no-sync python --version`, only if `$repo\.venv` exists | `Python 3.11.16` |

      Print `BOOTSTRAP OK` and `exit 0` if every row is OK. Otherwise print `BOOTSTRAP FAILED: <rows>` and `exit 1`.
8. **Python environment:**
   1. write `pyproject.toml` and `.python-version` exactly as in section 3.4;
   2. run the bootstrap once to get the tools; on the first run it skips repo setup because there is no `uv.lock` yet;
   3. run `WE uv lock`, then `WE uv sync --locked`. `uv.lock` must be committed.
   
   Create:
   - `workshop/hello.py`: `def main() -> int`. It prints `Python <full version>`, then one `name==version` line for each main dependency, read with `importlib.metadata.version` in pyproject order, then `ml group: not installed (installed from Phase 1.3)` if `importlib.util.find_spec("torch") is None` (otherwise `ml group: installed`), and finally `Veil workshop OK`. It returns 0, and `if __name__ == "__main__": raise SystemExit(main())`.
   - `workshop/tests/test_env.py` with:
     - `test_python_is_311`: `sys.version_info[:2] == (3, 11)`;
     - `test_main_pins_installed`: parse `pyproject.toml` with `tomllib` and, for every `name==version` in `[project].dependencies`, assert `importlib.metadata.version(name) == version`;
     - `test_onnxruntime_runs_tiny_model`: build an `Add` graph `y = a + b` over two inputs of shape `[1, 4]` with `onnx.helper` (opset 17, `ir_version=10`), check it with `onnx.checker.check_model`, run it with `onnxruntime.InferenceSession(model.SerializeToString(), providers=["CPUExecutionProvider"])`, and assert the output equals `a + b`;
     - `test_opencv_and_pillow`: on a `numpy.zeros((8, 8, 3), uint8)` image, assert that `cv2.cvtColor(img, cv2.COLOR_BGR2GRAY).shape == (8, 8)` and that `PIL.Image.fromarray(img).size == (8, 8)`.
9. **Guard (Android, Kotlin + coroutines)**, a Gradle root at `guard/` with module `:app` (package `com.veil.guard`). Files, verbatim where shown:
   - `guard/settings.gradle.kts`:
     ```kotlin
     pluginManagement {
         repositories {
             google()
             mavenCentral()
             gradlePluginPortal()
         }
     }
     dependencyResolutionManagement {
         repositoriesMode.set(RepositoriesMode.FAIL_ON_PROJECT_REPOS)
         repositories {
             google()
             mavenCentral()
         }
     }
     rootProject.name = "veil-guard"
     include(":app")
     if (file("testfeed/build.gradle.kts").exists()) include(":testfeed")
     ```
   - `guard/build.gradle.kts`:
     ```kotlin
     buildscript {
         repositories {
             google()
             mavenCentral()
         }
         dependencies {
             // AGP 9 built-in Kotlin; pin KGP to Flutter 3.47.6's version (see SPEC R2 for the fallback)
             classpath("org.jetbrains.kotlin:kotlin-gradle-plugin:2.4.0")
         }
     }
     plugins {
         alias(libs.plugins.android.application) apply false
     }
     ```
   - `guard/gradle/libs.versions.toml`:
     ```toml
     [versions]
     agp = "9.1.0"
     coroutines = "1.11.0"
     junit = "4.13.2"

     [libraries]
     kotlinx-coroutines-android = { module = "org.jetbrains.kotlinx:kotlinx-coroutines-android", version.ref = "coroutines" }
     junit = { module = "junit:junit", version.ref = "junit" }

     [plugins]
     android-application = { id = "com.android.application", version.ref = "agp" }
     ```
   - `guard/gradle.properties`:
     ```properties
     org.gradle.jvmargs=-Xmx2g -XX:MaxMetaspaceSize=768m -XX:+HeapDumpOnOutOfMemoryError -Dfile.encoding=UTF-8
     org.gradle.daemon=false
     org.gradle.parallel=false
     org.gradle.workers.max=2
     kotlin.compiler.execution.strategy=in-process
     ```
   - `guard/app/build.gradle.kts`:
     ```kotlin
     plugins {
         alias(libs.plugins.android.application)
     }

     android {
         namespace = "com.veil.guard"
         compileSdk = 36
         defaultConfig {
             applicationId = "com.veil.guard"
             minSdk = 31
             targetSdk = 36
             versionCode = 1
             versionName = "0.1.0"
         }
         buildTypes {
             release { isMinifyEnabled = false }
         }
         compileOptions {
             sourceCompatibility = JavaVersion.VERSION_17
             targetCompatibility = JavaVersion.VERSION_17
         }
     }

     dependencies {
         implementation(libs.kotlinx.coroutines.android)
         testImplementation(libs.junit)
     }
     ```
   - **Wrapper.** After writing the files above, run `WE --cd guard gradle wrapper --gradle-version 9.3.1 --distribution-type bin --gradle-distribution-sha256-sum b266d5ff6b90eada6dc3b20cb090e3731302e553a27c5d3e4df1f0d76beaff06 --no-daemon`. Commit `gradlew`, `gradlew.bat`, `gradle/wrapper/gradle-wrapper.jar` and `gradle/wrapper/gradle-wrapper.properties`.
   - `guard/app/src/main/AndroidManifest.xml`:
     - `<application android:label="Veil Guard" android:theme="@android:style/Theme.DeviceDefault">`.
     - Activity `.MainActivity`: `android:exported="true"`, with a MAIN/LAUNCHER intent-filter.
     - Service `.probe.ProbeAccessibilityService`, declared exactly per the Android docs: `android:permission="android.permission.BIND_ACCESSIBILITY_SERVICE"`, `android:exported="true"`, `android:label="@string/probe_label"`, intent-filter action `android.accessibilityservice.AccessibilityService`, and meta-data `android.accessibilityservice` → `@xml/probe_accessibility_service`.
   - `guard/app/src/main/res/values/strings.xml`:
     - `probe_label` = "Veil probe (does nothing)";
     - `probe_description` = "Test-only service used in Phase 1.1 to check that this phone lets a sideloaded app enable an accessibility service. It reads nothing.".
   - `guard/app/src/main/res/xml/probe_accessibility_service.xml`: `<accessibility-service android:description="@string/probe_description" android:accessibilityEventTypes="typeWindowStateChanged" android:accessibilityFeedbackType="feedbackGeneric" android:notificationTimeout="100" android:canRetrieveWindowContent="false" />`.
   - Kotlin sources go in `guard/app/src/main/java/com/veil/guard/`. Use the `java` dir; AGP 9 compiles Kotlin from it.
     ```kotlin
     // DeviceInfo.kt
     data class DeviceInfo(
         val socModel: String, val socManufacturer: String, val hardware: String, val board: String,
         val manufacturer: String, val model: String,
         val androidRelease: String, val sdkInt: Int, val buildDisplay: String,
         val ramTotalBytes: Long,
         val screenWidthPx: Int, val screenHeightPx: Int, val densityDpi: Int,
         val refreshRatesHz: List<Float>,
     )
     object DeviceInfoFormat {
         /** One-line JSON, keys in the constructor order above; strings JSON-escaped; floats with one decimal (e.g. 144.0). No org.json (unit-testable on the JVM). */
         fun toHelloJson(info: DeviceInfo): String
         /** Lines: "Veil Guard · hello", "Chip: <socModel> (<socManufacturer>)", "Android: <release> (API <sdk>)",
          *  "RAM: <GiB with 1 decimal> GiB (<bytes> bytes)", "Screen: <w> × <h> px, <dpi> dpi, <rates joined by '/'> Hz" */
         fun toDisplayText(info: DeviceInfo): String
     }
     // DeviceInfoReader.kt
     /** Must be called on the main thread (reads Activity.display). Uses Build.SOC_MODEL, Build.SOC_MANUFACTURER, Build.HARDWARE,
      *  Build.BOARD, Build.MANUFACTURER, Build.MODEL, Build.VERSION.RELEASE, Build.VERSION.SDK_INT, Build.DISPLAY,
      *  ActivityManager.MemoryInfo.totalMem, activity.display!!.mode.physicalWidth/physicalHeight,
      *  resources.displayMetrics.densityDpi, display.supportedModes.map { it.refreshRate }.distinct().sorted(). */
     fun readDeviceInfo(activity: Activity): DeviceInfo
     // MainActivity.kt
     class MainActivity : Activity() {
         // onCreate: build ScrollView{TextView(textSize 18f, padding 48)}; then scope.launch (MainScope()):
         //   val info = readDeviceInfo(this@MainActivity)
         //   val text = withContext(Dispatchers.Default) { DeviceInfoFormat.toDisplayText(info) to DeviceInfoFormat.toHelloJson(info) }
         //   textView.text = text.first; Log.i(TAG, "VEIL_HELLO " + text.second)
         // onDestroy: scope.cancel()
         companion object { const val TAG = "VeilHello" }
     }
     // probe/ProbeAccessibilityService.kt
     class ProbeAccessibilityService : AccessibilityService() {
         override fun onServiceConnected() { Log.i("VeilProbe", "VEIL_PROBE connected") }
         override fun onAccessibilityEvent(event: AccessibilityEvent?) {}   // ignores everything
         override fun onInterrupt() {}
     }
     ```
   - `guard/app/src/test/java/com/veil/guard/DeviceInfoFormatTest.kt` (JUnit 4) uses one sample `DeviceInfo`. It asserts:
     - the exact `toHelloJson` string;
     - that `toDisplayText` contains `Chip: SM8850 (QTI)` and `Android: 16 (API 36)`.
   - Run `WE java -jar D:\veil-toolchain\ktlint\ktlint.jar --format "guard/**/*.kt" "guard/**/*.kts" "!guard/**/build/**"`. It must end clean.
10. **Console (Flutter):**
    1. Run `WE flutter create --org com.veil --project-name veil_console --platforms android --description "Veil Console" console`. Do not pass `--android-language`; Kotlin is the default.
    2. Make exactly these edits:
       - In `console/android/app/build.gradle.kts`, set `namespace = "com.veil.console"` and `applicationId = "com.veil.console"`.
       - Move `console/android/app/src/main/kotlin/com/veil/veil_console/MainActivity.kt` to `.../kotlin/com/veil/console/MainActivity.kt`, change its `package` line to `package com.veil.console`, and delete the empty old folder.
       - In `console/android/app/src/main/AndroidManifest.xml`, set `android:label="Veil Console"`.
       - In `console/android/gradle.properties`, replace the `org.gradle.jvmargs=-Xmx8G …` line with `org.gradle.jvmargs=-Xmx2g -XX:MaxMetaspaceSize=1g -XX:ReservedCodeCacheSize=256m -XX:+HeapDumpOnOutOfMemoryError -Dfile.encoding=UTF-8`, and append three lines: `org.gradle.daemon=false`, `org.gradle.workers.max=2` and `kotlin.compiler.execution.strategy=in-process`. Keep Flutter's `android.newDsl=false` and `android.builtInKotlin=false` lines unchanged.
       - In `console/android/gradle/wrapper/gradle-wrapper.properties`, set `distributionUrl=https\://services.gradle.org/distributions/gradle-9.3.1-bin.zip` and add `distributionSha256Sum=b266d5ff6b90eada6dc3b20cb090e3731302e553a27c5d3e4df1f0d76beaff06`. This shares the Gradle download with `guard/`.
       - Replace `console/lib/main.dart`:
         ```dart
         import 'package:flutter/material.dart';

         void main() {
           debugPrint('VEIL_CONSOLE_HELLO');
           runApp(const VeilConsoleApp());
         }

         class VeilConsoleApp extends StatelessWidget {
           const VeilConsoleApp({super.key});

           @override
           Widget build(BuildContext context) {
             return const MaterialApp(
               title: 'Veil Console',
               home: Scaffold(
                 body: Center(
                   child: Column(
                     mainAxisSize: MainAxisSize.min,
                     children: [
                       Text('Veil Console', style: TextStyle(fontSize: 32, fontWeight: FontWeight.bold)),
                       SizedBox(height: 12),
                       Text('Hello from Phase 1.1'),
                     ],
                   ),
                 ),
               ),
             );
           }
         }
         ```
       - Replace `console/test/widget_test.dart` with one `testWidgets('shows the Veil Console title', …)`. It pumps `const VeilConsoleApp()` and expects `find.text('Veil Console')` and `find.text('Hello from Phase 1.1')` each to find one widget.
       - Replace `console/README.md` with 3 lines that point to the top-level README.
    3. Run `WE --cd console dart format lib test`.
    4. Commit Flutter's generated `console/.gitignore`, `.metadata`, `pubspec.yaml`, `pubspec.lock` and `analysis_options.yaml`. Do not commit `android/gradlew*` or `gradle-wrapper.jar`; Flutter's own `.gitignore` excludes them and regenerates them.
11. **Pre-commit hook.** Write `.pre-commit-config.yaml` (verbatim):
    ```yaml
    default_install_hook_types: [pre-commit]
    repos:
      - repo: local
        hooks:
          - id: ruff-format
            name: ruff format (Python)
            entry: uv run --no-sync ruff format
            language: unsupported
            types_or: [python, pyi]
            exclude: ^workshop/contracts/models\.py$
          - id: ruff-check
            name: ruff check --fix (Python)
            entry: uv run --no-sync ruff check --fix --exit-non-zero-on-fix
            language: unsupported
            types_or: [python, pyi]
            exclude: ^workshop/contracts/models\.py$
          - id: ktlint
            name: ktlint --format (Kotlin, guard/)
            entry: uv run --no-sync python tools/hooks/ktlint_hook.py
            language: unsupported
            files: ^guard/.*\.kts?$
            exclude: /build/
          - id: dart-format
            name: dart format (Flutter, console/)
            entry: uv run --no-sync python tools/hooks/dart_format_hook.py
            language: unsupported
            files: ^console/.*\.dart$
    ```
    The two hook scripts each define `main(argv: list[str]) -> int`:
    - `tools/hooks/ktlint_hook.py` runs `[<JAVA_HOME>\bin\java.exe, "-jar", <VEIL_TOOLCHAIN>\ktlint\ktlint.jar, "--format", "--relative", *argv]`.
    - `tools/hooks/dart_format_hook.py` runs `[<VEIL_TOOLCHAIN>\flutter\bin\cache\dart-sdk\bin\dart.exe, "format", *argv]`.
    
    Both read `VEIL_TOOLCHAIN` and `JAVA_HOME` from the environment. If either variable or the tool file is missing, print `run '. .\tools\env.ps1' (or 'source tools/env.sh') first; toolchain not found: <path>` and return 2. Otherwise return the tool's exit code. Then run `WE uv run --no-sync pre-commit install`. ktlint only covers `guard/`; the Flutter-generated Android shell in `console/android` is excluded on purpose.
12. **`docs/decisions.md`**. Create it with the heading `# Decisions` and the line `Numbered, newest last. Scripts may append entries between their own markers.`, followed by:
    - **`## D-001 · Hackathon build, licences reviewed before any commercial release`**
      - `Date: 2026-10-02 · Phase 1.1 · Status: accepted`.
      - Body: Veil is built as a hackathon/demo build, and every third-party licence is reviewed before any commercial release (PLAN Appendix C). Copy Appendix C's 5-row table verbatim: SigLIP2 Apache-2.0; YOLOE AGPL-3.0 (assumed; verify); MobileCLIP/MobileCLIP2 Apple research-only; NudeNet AGPL-3.0 (reported; verify); toxicity model Apache-2.0.
    - **`## D-002 · Portable, project-local toolchain`**. Summarise DV-1, DV-2 and DV-3 plus the pins:
      - "all versions in `tools/toolchain.json` and `pyproject.toml`/`uv.lock`";
      - Python 3.11.16 via uv;
      - Temurin 17;
      - Android SDK API 36, build-tools 36.0.0, NDK 28.2.13676358;
      - Gradle 9.3.1, AGP 9.1.0, Kotlin 2.4.0;
      - Flutter 3.47.6;
      - scrcpy 4.1, ffmpeg 9.0.2, ktlint 1.8.0;
      - no admin, PATH or registry changes;
      - the toolchain path rule.
    - **`## D-003 · Contract v1.0 covers 16 types`**. List the 16 types from section 4 of 1.1.2, explain that ScreenLabel is the 16th (DV-5), and that Tape (2.1) and LookRequest (2.2) are added later as v1.1.
    - The literal line `<!-- The target-chip check (D-004 or later) is appended by workshop.bench.device_profile. -->`.
13. **`README.md`** uses exactly these `##` headings, in this order. Each section gives copy-paste PowerShell commands, matching this spec:
    1. **What is in this repository**: PLAN's layout table plus `tools/`.
    2. **Before you start**:
       - Windows 10/11 x64, Git for Windows, internet;
       - about 15 GB free on a drive whose path for the toolchain has no spaces;
       - no admin needed and nothing installed system-wide.
    3. **One-command setup**:
       - `powershell -ExecutionPolicy Bypass -File tools\bootstrap.ps1`;
       - where the toolchain goes, and how to choose it with `-ToolchainDir` or `$env:VEIL_TOOLCHAIN`;
       - what it downloads, sizes and time;
       - that it accepts the Android SDK licences;
       - re-running is safe;
       - `-CheckOnly`.
    4. **Every new terminal**:
       - `. .\tools\env.ps1`, or for Git Bash `source tools/env.sh`;
       - if scripts are blocked, `Set-ExecutionPolicy -Scope Process Bypass`;
       - `tools\with-env.ps1` for one-off commands.
    5. **Workshop (Python)**:
       - `uv sync --locked`, `uv run python -m workshop.hello`, `uv run pytest`;
       - ML packages come from Phase 1.3: `uv sync --locked --group ml`.
    6. **Contracts**:
       - `uv run pytest contracts`;
       - `uv run python contracts/scripts/gen_python.py` (regenerate types; `--check` to verify);
       - `uv run python -m workshop.contracts.validate <file>`;
       - link `contracts/README.md`.
    7. **Guard (Android app)**:
       - `cd guard; .\gradlew.bat --no-daemon :app:assembleDebug`;
       - install with `adb install -r app\build\outputs\apk\debug\app-debug.apk`;
       - launch with `adb shell am start -n com.veil.guard/.MainActivity`.
    8. **Test Feed app**:
       - `.\gradlew.bat --no-daemon :testfeed:assembleDebug`;
       - install `testfeed\build\outputs\apk\debug\testfeed-debug.apk`;
       - launch `com.veil.testfeed/.FeedActivity`;
       - link `guard/testfeed/README.md`.
    9. **Console (Flutter app)**:
       - `cd console; flutter pub get; flutter test; flutter build apk --debug`;
       - install `build\app\outputs\flutter-apk\app-debug.apk`;
       - launch `com.veil.console/.MainActivity`.
    10. **Connect the phone**:
        - Developer options;
        - USB debugging, "Install via USB", and "USB debugging (Security settings)" if shown;
        - Stay awake;
        - accept the RSA prompt with "Always allow";
        - `adb devices`;
        - vivo/iQOO may ask to confirm each USB install: tap Install.
    11. **Device profile**: `uv run python -m workshop.bench.device_profile --write`.
    12. **Bench check**:
        - `.\tools\bench_check.ps1`;
        - exit codes 0/1/2;
        - link `docs/bench-check.md`.
    13. **Accounts: Qualcomm AI Hub and Hugging Face**:
        - `uv run qai-hub configure --api_token <TOKEN>` typed in your own terminal, never in a file or chat;
        - `uv run qai-hub list-devices`;
        - optional `uv run hf auth login`.
    14. **Formatting and the pre-commit hook**:
        - `uv run pre-commit install` (the bootstrap does it);
        - `uv run pre-commit run --all-files`;
        - commit from a shell that loaded the env.
    15. **Low-memory laptops**:
        - one build at a time;
        - `--no-daemon`;
        - heaps capped at 2 GB.
    16. **Private data**: `data/` is git-ignored; verify with `git check-ignore data/x.png`.
    17. **Troubleshooting**:
        - "flutter.bat missing → antivirus";
        - "path with spaces";
        - "install prompt on phone";
        - "OutOfMemoryError";
        - "adb unauthorized".
    
    Sections 6, 8, 11 and 12 describe commands that 1.1.2 and 1.1.3 deliver. Use the exact commands above.
14. Run the whole Verification table below and make it pass. Fill in the Builder sections of `1.1.1-repository-and-tools.md`.

### Must not

- Must not change user or system environment variables, the registry, profile scripts, or anything under `C:\Program Files`.
- Must not install a system-wide anything, delete `%USERPROFILE%\.gradle`, or use the system Python or JDK 11.
- Must not commit, push or create branches.
- Must not write `contracts/**`, `workshop/contracts/**`, `workshop/bench/**`, `guard/testfeed/**` or `docs/acceptance/**`.
- Must not install the `ml` group, and must not opt out of AGP built-in Kotlin in `guard/`.
- Must not run Gradle and Flutter builds at the same time.

### Verification (the orchestrator runs these)

| # | Command (run from veil/) | Expected result | Covers |
| --- | --- | --- | --- |
| 1 | `powershell -NoProfile -ExecutionPolicy Bypass -File tools\bootstrap.ps1 -CheckOnly` | Exit 0. The last line is `BOOTSTRAP OK`. The table shows uv 0.12.21, java 17.0.20.1, Gradle 9.3.1, the 4 SDK packages, adb, flutter 3.47.6, scrcpy 4.1, ffmpeg 9.0.2, ktlint 1.8.0, python 3.11.16 and repo-venv 3.11.16, all OK, with paths under `D:\veil-toolchain` | 1.1.1 Do 2-4; tools |
| 2 | `powershell -NoProfile -ExecutionPolicy Bypass -File tools\bootstrap.ps1` (second run) | Exit 0 in under 5 min. Every archive prints `already installed`. No new download appears in `bootstrap.log` | idempotent setup |
| 3 | `WE uv lock --locked` then `WE uv sync --locked` | Both exit 0 | Do 2 |
| 4 | `WE uv run --locked python -m workshop.hello` | Exit 0. The output includes `Python 3.11.16`, `numpy==2.4.6`, `onnxruntime==1.30.0`, `ml group: not installed (installed from Phase 1.3)` and the final line `Veil workshop OK` | "hello world" (laptop) |
| 5 | `WE uv run --locked pytest workshop -q` | `4 passed`, 0 failed | AC-1.1-02 (Python tests run) |
| 6 | `WE --cd guard .\gradlew.bat --no-daemon :app:assembleDebug :app:testDebugUnitTest` | `BUILD SUCCESSFUL`. `guard\app\build\outputs\apk\debug\app-debug.apk` exists | Do 3; AC-1.1-02 (Android builds) |
| 7 | `WE --cd console flutter test` | `All tests passed!` | Do 4 |
| 8 | `WE --cd console flutter build apk --debug` | Exit 0. `console\build\app\outputs\flutter-apk\app-debug.apk` exists | Do 4; AC-1.1-02 (Flutter builds) |
| 9 | `WE --cd console flutter analyze` | `No issues found!` | Do 4 |
| 10 | `WE uv run --locked pre-commit run --all-files` | Exit 0. Every hook prints `Passed`, or `Skipped` when it has no files | Do 5 |
| 11 | `git check-ignore -v data/x.png` | Prints `.gitignore:2:/data/*	data/x.png`, exit 0 | AC-1.1-08 |
| 12 | `git status --short --untracked-files=all` | No path contains `/build/`, `.venv/`, `.dart_tool/`, `.gradle/` or `local.properties` | hygiene |
| 13 | `Select-String -Path docs\decisions.md -Pattern '^## D-00[123] '` | 3 matches. D-001's heading reads `Hackathon build, licences reviewed before any commercial release` | Do 6 |
| 14 | `Select-String -Path README.md -Pattern '^## '` | The 17 headings of step 13, in order | Do 1 |
| 15 | `WE java -jar D:\veil-toolchain\ktlint\ktlint.jar "guard/**/*.kt" "guard/**/*.kts" "!guard/**/build/**"` (a literal path; `$env:` would not expand inside `WE`) | Exit 0, no violations | Do 5 (Kotlin) |
| 16 | `powershell -NoProfile -Command "[Environment]::GetEnvironmentVariable('Path','User')"` and `...('JAVA_HOME','User')` | Identical to the orchestrator's pre-wave snapshot (section 3.6) | no persistent changes |
| 17 | `powershell -NoProfile -Command "Test-Path HKCU:\Software\Python\Astral"` | `False` | no registry changes |
| 18 | `git -C . rev-parse --is-inside-work-tree` and `Test-Path .git\hooks\pre-commit` | `true` and `True` | repo and hook installed |

"Done when" (PLAN): "A teammate who did not write it can clone, follow the README, and run all three 'hello world' targets on the phone and laptop."
- The laptop part is rows 4-9 here, plus the CLEAN check AC-1.1-01.
- The phone part ("hello apps launch on the iQOO") waits for HC-002. That makes this sub-phase VERIFIED for machine work and WAITING_HUMAN for the phone part.

- **Needs a human:** None to build it.
  - The phone launch of both hello apps is checked in the phase's PHONE checks and the bench check once HC-002 is done.
  - The Builder reports DONE, with the phone launch noted as pending HC-002 rather than NEEDS_HUMAN.
- **Size:** L.

---

## 4. Sub-phase 1.1.2 Shared contracts, first version

- **Goal:** JSON Schemas (draft 2020-12) for the 16 shared types, with the conventions and the `spaceId` rule written into each schema. Also generated pydantic v2 models, 2-3 valid and 1-3 invalid examples per type, and tests that validate them all.
- **Owned paths:** `contracts/**` (schemas, examples, tests, scripts, README, VERSION) and `workshop/contracts/**`.
- **Read-only inputs:**
  - `pyproject.toml` and `uv.lock` (jsonschema, referencing, pydantic, datamodel-code-generator and numpy are already pinned);
  - `tools/with-env.ps1`;
  - PLAN.md lines 59-87 (glossary, fixed decisions) and 236-339.

### Steps

1. **Files.**
   - `contracts/VERSION` contains the single line `1.0`.
   - There are 16 schema files directly in `contracts/` (PLAN deliverable `contracts/*.schema.json`):
     `rect.schema.json`, `frame.schema.json`, `ui-event.schema.json`, `region.schema.json`, `embedding.schema.json`, `concept.schema.json`, `concept-pack.schema.json`, `compiled-concept.schema.json`, `finding.schema.json`, `track.schema.json`, `mask.schema.json`, `mask-plan.schema.json`, `feedback.schema.json`, `model-manifest.schema.json`, `engine-stats.schema.json`, `screen-label.schema.json`.
2. **Schema rules, applied to every file:**
   - `"$schema": "https://json-schema.org/draft/2020-12/schema"`. No `$id`.
   - Cross-file references are relative file names: `{"$ref": "rect.schema.json"}`. In-file references use `"#/$defs/<Key>"`.
   - `"title"` is the PascalCase type name (`Rect`, `UiEvent`, …).
   - `"type": "object"` and `"additionalProperties": false` on every object.
   - No inline object schemas. Every nested object lives in the file's `$defs` under a short key, with `"title": "<FileTitle><Key>"` (e.g. key `Node` in `ui-event.schema.json` has the title `UiEventNode`).
   - **No `null`** anywhere: optional fields are omitted, never null.
   - All counts, pixels and times use `"type": "integer"`.
   - Enum strings are lowerCamelCase.
   - **`contractVersion`**: `{"type": "string", "const": "1.0", "description": "Contract version this object follows."}` is a property of every schema (for UiEvent, of every variant). It is **required everywhere except `Rect`**, where it is optional, because a Rect is always embedded in a message that carries the version.
   - **Top-level `description`** = `<one-line purpose> ` + CONVENTIONS, where CONVENTIONS is exactly:
     > `Veil contract v1.0. Units: positions and sizes are integer screen pixels with the origin at the top-left of the display in its current orientation (x grows right, y grows down); times are integer milliseconds on one monotonic clock (Android SystemClock.uptimeMillis; replays use a virtual clock in the same unit); fingerprints are L2-normalised vectors stored as float16.`
   - The **fingerprint-bearing types** `Embedding`, `CompiledConcept` and `Feedback` (plus `ModelManifest`, which describes fingerprint models) also append SPACE_RULE to their description, exactly:
     > `A fingerprint may only be compared with a concept from the same model family: both must carry the same spaceId.`
     
     Each of those three types lists `spaceId` in `required`.
   - Shared string formats, written inline per property:

     | Format | Pattern |
     | --- | --- |
     | Id | `^[A-Za-z0-9][A-Za-z0-9._:-]{0,63}$` |
     | Slug (conceptId, packId, spaceId) | `^[a-z0-9][a-z0-9._-]{0,63}$` |
     | Package name | `^[A-Za-z][A-Za-z0-9_]*(\.[A-Za-z0-9_]+)+$` |
     | sha256 | `^[0-9a-f]{64}$` |
     | Base64 | `^[A-Za-z0-9+/]*={0,2}$` plus `minLength` 4 |
     | `tMs` and other `*Ms` times | integer ≥ 0 |
3. **Field lists.** Each field is written as name: type, req (required) or opt (optional), then constraints and meaning.

   **3.1 `Rect`**: "An axis-aligned rectangle on the screen."
   - `contractVersion`: const "1.0", opt.
   - `x`, `y`: integer, req; −100000..100000; top-left corner. Negative values are allowed for items scrolled partly or fully off-screen.
   - `w`, `h`: integer, req; 1..100000.

   **3.2 `Frame`**: "Metadata of one captured screen frame; pixels are never part of a contract."
   - `contractVersion`: req.
   - `frameId`: integer ≥ 0, req; increases with every delivered frame within a capture session.
   - `sessionId`: Id, opt.
   - `tMs`: req; capture time.
   - `width`, `height`: integer 1..8192, req; frame pixels at capture scale (e.g. 360 × 800).
   - `screenWidth`, `screenHeight`: integer 1..16384, req; full-resolution screen in the current orientation. Conversion: `x_frame = x_screen × width / screenWidth`.
   - `rotation`: integer enum [0, 90, 180, 270], req.
   - `source`: enum ["mediaProjection", "accessibilityScreenshot", "replay", "screenshotFile"], req.
   - `foregroundPackage`: package name, opt.
   - `ownOverlay`: array of Rect, maxItems 64, req (may be empty); Veil's own covers visible at capture time, in screen px (PLAN 4.3.3 `ownOverlay`, AC-4.3-05).
   - `blindRects`: array of Rect, maxItems 16, opt; areas known to be black or protected (4.1.3).
   - `image`: string 1..260, opt; file name when the frame is stored on disk.

   **3.3 `UiEvent`**: "One screen signal from the accessibility service: scrolled, window changed, content changed, nodes snapshot, screen off or screen on."
   - The top level is `oneOf` of `$defs` `Scrolled`, `WindowChanged`, `ContentChanged`, `NodesSnapshot`, `ScreenOff` and `ScreenOn`. The top level has `title` and `description` and no `type`; its `$defs` also hold `Node`.
   - Every variant is an object with:
     - `contractVersion`: req;
     - `eventId`: integer ≥ 0, req; per-session sequence;
     - `tMs`: req;
     - `type`: const <variant value>, req;
     - `packageName`: package name, opt.
   - **`Scrolled`** (`type` const `"scrolled"`):
     - `dx`, `dy`: integer, req. How far the **content** moved on screen, in screen pixels: +dy means it moved down, −dy means it moved up (the user scrolled towards later content), +dx means it moved right. This is the opposite sign to Android's scroll delta (PLAN 4.2.2).
     - `containerRect`: Rect, opt.
     - `containerId`: string ≤ 128, opt.
     - `estimated`: boolean, opt; true when derived from frame differences (2.1.1, 4.2.2).
   - **`WindowChanged`** (`"windowChanged"`): `packageName` is req here; `className`: string ≤ 200, opt; `windowId`: integer, opt.
   - **`ContentChanged`** (`"contentChanged"`): `rect`: Rect, opt; `changeTypes`: array of string ≤ 32, maxItems 8, opt.
   - **`NodesSnapshot`** (`"nodesSnapshot"`):
     - `nodes`: array of Node, maxItems 300, req (PLAN 4.2.3 node limit).
     - `truncated`: boolean, req; true if the node limit or time budget was hit.
     - `durationMs`: integer ≥ 0, req.
   - **`Node`**:
     - `kind`: enum ["image", "video", "web", "text", "list", "post", "other"], req.
     - `rect`: Rect, req.
     - `nodeId`: string ≤ 128, opt.
     - `text`: string ≤ 2000, opt.
     - `contentDescription`: string ≤ 500, opt.
     - `className`: string ≤ 200, opt.
   - **`ScreenOff`** (`"screenOff"`) and **`ScreenOn`** (`"screenOn"`): common fields only.

   **3.4 `Region`**: "A piece of the screen proposed by the Spotter for describing and judging."
   - `contractVersion`: req.
   - `regionId`: Id, req; unique within its look.
   - `lookId`: integer ≥ 0, req.
   - `frameId`: integer ≥ 0, opt.
   - `tMs`: req.
   - `rect`: Rect, req.
   - `source`: enum ["whole", "tile", "layout", "finder", "crop"], req (1.3.1 pieces v0; 5.2.2 three sources).
   - `kind`: enum ["screen", "post", "image", "video", "text", "object", "unknown"], req.
   - `objectness`: number 0..1, opt; the finder's score.
   - `postRect`: Rect, opt; bounds of the enclosing post, for whole-post covers (2.3.2).
   - `parentRegionId`: Id, opt.
   - `text`: string ≤ 2000, opt; for text regions (5.2.3).
   - `phash`: string `^[0-9a-f]{16}$`, opt; 64-bit picture hash of the crop, used as the memory key (2.3.2).
   - `ownOverlayFraction`: number 0..1, opt; the share hidden by Veil's own covers (2.3.1 self-capture rule).

   **3.5 `Embedding`** (fingerprint-bearing): "A fingerprint (meaning vector) of an image piece or a text prompt."
   - `contractVersion`: req.
   - `spaceId`: slug, req.
   - `modelId`: Id, req; matches `ModelManifest.modelId`.
   - `dim`: integer 1..4096, req.
   - `vectorF16`: string, req; standard base64 with padding of `dim` little-endian IEEE-754 binary16 values, L2-normalised. The byte length 2 × dim is checked by `rules.py`.
   - `kind`: enum ["image", "text", "region", "centroid"], req.
   - `regionId`: Id, opt.
   - `text`: string ≤ 500, opt; the prompt, for text kind.

   **3.6 `Concept`**: "The user-facing definition of one dislike: the concept card's words, lookalikes and settings."
   - `contractVersion`: req.
   - `conceptId`: slug, req.
   - `displayName`: string 1..64, req.
   - `layer`: integer enum [1, 2], req.
   - `enabled`: boolean, req.
   - `looksLike`: array of string 1..200, 1..32 items, req.
   - `butNot`: array of string 1..200, 0..32 items, req.
   - `ignore`: array of string 1..200, 0..16 items, opt; when omitted the Teacher uses the shared ignore list.
   - `keywords`: array of string 1..64, 0..64 items, opt; text-lane keyword rules (5.2.3).
   - `examplePhotos`: array of ExamplePhoto, 0..16, opt (6.1.1: files plus checksum). **ExamplePhoto** = {`path`: string 1..260, req; `sha256`: sha256, req}.
   - `scope`: enum ["object", "wholeElement"], req.
   - `coverStyle`: enum ["solid", "blur", "mosaic"], req.
   - `showLabel`: boolean, req.
   - `strictness`: enum ["light", "balanced", "strict"], opt; a per-concept override, where omitted means the global mode applies.
   - `sensitive`: boolean, opt.
   - **Conditional:** `"if": {"properties": {"layer": {"const": 1}}, "required": ["layer"]}, "then": {"properties": {"coverStyle": {"const": "solid"}}}`. Layer 1 is always solid (2.3.2, AC-2.3-06).

   **3.7 `ConceptPack`**: "A named, versioned set of concepts (a topic pack)."
   - `contractVersion`: req.
   - `packId`: slug, req.
   - `name`: string 1..80, req.
   - `version`: string `^\d+\.\d+\.\d+$`, req.
   - `description`: string ≤ 2000, req.
   - `sensitive`: boolean, req (6.2.3).
   - `concepts`: array of Concept (`$ref concept.schema.json`), 1..64, req.
   - `accuracy`: Accuracy, opt. **Accuracy** = {`recall`: number 0..1, req; `cleanFalseCoverRate`: number 0..1, req; `testImages`: integer ≥ 1, req; `testSet`: string 1..100, req} (6.2.3: measured accuracy in the description).
   - `licence`: string ≤ 64, opt.

   **3.8 `CompiledConcept`** (fingerprint-bearing): "A concept compiled into fingerprints for one model family, ready for the Judge."
   - `contractVersion`: req.
   - `conceptId`: slug, req.
   - `spaceId`: slug, req.
   - `textModelId`: Id, req.
   - `conceptSha256`: sha256, req; the hash of the canonical JSON of the source Concept (see `rules.concept_sha256`). This lets phone-built and Workshop-built cards be compared (5.1 guarantee).
   - `looksLike`: array of Embedding, 1..32, req.
   - `butNot`: array of Embedding, 0..32, req.
   - `ignore`: array of Embedding, 0..16, req.
   - `exampleCentroid`: Embedding, opt.
   - `exampleCount`: integer 0..16, req.
   - `exceptions`: array of Embedding, **maxItems 64**, req ("that's not it" fingerprints, 6.2.1, AC-6.2-02).
   - `calibrationOffset`: number −1..1, req (1.3.3).
   - `userOffset`: number **−0.15..0.15**, req (6.2.1 cap, AC-6.2-02).
   - `thresholds`: Thresholds, req. **Thresholds** = {`light`, `balanced`, `strict`: number 0..1, all req}.
   - `margin`: number 0..1, req (1.3.1 Judge v0 margin).
   - `exampleThreshold`: number 0..1, opt (5.1.3).

   **3.9 `Finding`**: "The Judge's verdict on one piece for one concept, or a Layer 1 detector hit."
   - `contractVersion`: req.
   - `findingId`: Id, req.
   - `lookId`: integer ≥ 0, req.
   - `tMs`: req.
   - `frameId`: integer ≥ 0, opt.
   - `image`: string 1..260, opt; the screenshot file name in offline evaluation (1.2.3 scorer input).
   - `regionId`: Id, opt.
   - `rect`: Rect, req.
   - `conceptId`: slug, req; Layer 1 ids look like `l1.nudity` and `l1.abuse`.
   - `layer`: integer enum [1, 2], req.
   - `lane`: enum ["describer", "finder", "layer1", "text"], req.
   - `decision`: enum ["hide", "nearMiss", "leave"], req. 2.3.1: `hide` is a confident finding; `nearMiss` is a near-threshold finding that only keeps existing covers alive.
   - `probability`: number 0..1, req.
   - `score`: number −1..1, opt.
   - `margin`: number −2..2, opt.
   - `scope`: enum ["object", "wholeElement"], req.

   **3.10 `Track`**: "The Follower's state for one cover that follows an item across frames and scrolls."
   - `contractVersion`: req.
   - `trackId`: integer ≥ 1, req; assigned in creation order (deterministic tie-breaking, 2.3.1).
   - `conceptId`: slug, req.
   - `layer`: [1, 2], req.
   - `rect`: Rect, req; the current position after scroll shifts.
   - `state`: enum ["tentative", "confirmed", "parked", "released"], req.
   - `sightings`: integer ≥ 0, req.
   - `firstSeenMs`, `lastSeenMs`, `holdUntilMs`, `maxHoldUntilMs`: integer ≥ 0, req.
   - `parkedUntilMs`: integer ≥ 0, opt.
   - `selfCaptureFraction`: number 0..1, req.
   - `peeked`: boolean, req.
   - `scope`: enum ["object", "wholeElement"], req.
   - `lastFindingId`: Id, opt.

   **3.11 `Mask`**: "One cover to draw."
   - `contractVersion`: req.
   - `maskId`: integer ≥ 1, req.
   - `rect`: Rect, req; already padded.
   - `style`: enum ["solid", "blur", "mosaic"], req.
   - `layer`: [1, 2], req.
   - `peekable`: boolean, req.
   - `label`: string 1..64, opt; e.g. "Hidden · cats".
   - `conceptIds`: array of slug, 1..8, req.
   - `trackIds`: array of integer ≥ 1, 1..32, req.
   - **Conditional:** `if layer const 1 then {style const "solid", peekable const false}` (AC-2.3-06).

   **3.12 `MaskPlan`**: "The complete set of covers to draw now."
   - `contractVersion`: req.
   - `planId`: integer ≥ 0, req; increases with every new plan.
   - `tMs`: req.
   - `screenWidth`, `screenHeight`: integer 1..16384, req.
   - `rotation`: [0, 90, 180, 270], req.
   - `masks`: array of Mask, **maxItems 24**, req (2.3.2 "at most 24 covers").
   - `basedOnFrameId`: integer ≥ 0, opt.
   - `reason`: enum ["look", "scroll", "expire", "peek", "clear", "appChange"], req.

   **3.13 `Feedback`** (fingerprint-bearing): "A user correction on a Layer 2 cover."
   - `contractVersion`: req.
   - `feedbackId`: Id, req.
   - `tMs`: req.
   - `kind`: enum ["notThis", "missed", "correct"], req (6.1.3 and 6.2.1).
   - `conceptId`: slug, req.
   - `layer`: integer **const 2**, req; Layer 1 cannot be corrected (6.2.1, AC-6.2-02).
   - `spaceId`: slug, req.
   - `embedding`: Embedding, opt.
   - `rect`: Rect, opt.
   - `trackId`: integer ≥ 1, opt.
   - `source`: enum ["longPress", "recentCovers", "screenshot"], req.
   - `thumbnailPath`: string 1..260, opt; a phone-local file only.
   - **Conditional:** `if kind const "notThis" then required ["embedding"]`.

   **3.14 `ModelManifest`**: "Everything the phone needs to load and use one model file." (Content per PLAN 3.2.3.)
   - `contractVersion`: req.
   - `modelId`: Id, req.
   - `name`: string 1..100, req.
   - `version`: string 1..40, req.
   - `task`: enum ["imageEmbedding", "textEmbedding", "objectFinder", "nsfwDetector", "toxicityClassifier", "ocr", "other"], req.
   - `inputs`, `outputs`: array of TensorSpec, 1..16, req. **TensorSpec**:
     - `name`: string 1..64, req;
     - `shape`: array of integer **≥ 1**, 1..8 items, req; fixed shapes only (AC-3.1-01);
     - `dtype`: enum ["float32", "float16", "uint8", "int8", "uint16", "int16", "int32", "int64", "bool"], req.
   - `preprocessing`: Preprocessing, req. **Preprocessing**:
     - `kind`: enum ["image", "text", "none"], req;
     - opt: `resizeWidth`, `resizeHeight` (integer 1..4096), `resizeMode` (enum ["stretch", "letterbox", "centerCrop"]), `colorOrder` (enum ["RGB", "BGR"]), `layout` (enum ["NCHW", "NHWC"]), `scale` (number), `mean` and `std` (array of number, 1..4), `tokenizer` (string ≤ 100), `maxTokens` (integer 1..1024).
   - `fingerprint`: Fingerprint, opt. **Fingerprint**:
     - `spaceId`: slug, req;
     - `dim`: integer 1..4096, req;
     - `role`: enum ["image", "text", "region"], req;
     - `pairedWith`: Id, req; the modelId of the paired encoder (for image and region models, their text encoder). This satisfies AC-3.2-04: "`spaceId` and paired text encoder set for every fingerprint model".
   - `precision`: enum ["float32", "float16", "w8a16", "w8a8", "w4a16"], req.
   - `runtime`: enum ["onnxruntime-qnn", "onnxruntime-cpu", "litert-npu", "litert-cpu", "mlkit"], req.
   - `batch`: integer 1..64, req.
   - `file`: File, req. **File** = {`path`: string 1..260, req; `sha256`: sha256, req; `bytes`: integer ≥ 1, req}.
   - `sourceUrl`: string `^https://`, req.
   - `licence`: string 1..64, req.
   - `notes`: string ≤ 2000, opt.
   - **Conditional:** `if task in ["imageEmbedding", "textEmbedding", "objectFinder"] then required ["fingerprint"]`.

   **3.15 `EngineStats`**: "Periodic statistics published by the Guard (5.2.1 after each look; 6.1 stats ticks about once a second)."
   - `contractVersion`: req.
   - `tMs`: req.
   - `windowMs`: integer 1..600000, req.
   - `mode`: enum ["light", "balanced", "strict"], req.
   - `schedulerState`: enum ["idle", "watching", "hot", "throttled"], req (2.2.2).
   - `captureState`: enum ["running", "paused", "stopped", "awaitingPermission"], req (4.1 guarantee).
   - `captureStopReason`: string ≤ 120, opt.
   - `captureSource`: enum ["mediaProjection", "accessibilityScreenshot", "replay"], opt.
   - `foregroundPackage`: package name, opt.
   - `looksPerSecond`: number ≥ 0, req.
   - `looksTotal`, `framesSeen`, `framesAnalysed`, `framesSkipped`, `cacheHits`, `cacheMisses`, `activeTracks`: integer ≥ 0, all req.
   - `activeCovers`: integer 0..24, req.
   - `aiMsLastLook`, `lookMsP50`, `lookMsP95`: number ≥ 0, opt.
   - `memoryPssKb`: integer ≥ 0, opt.
   - `thermalStatus`: integer 0..6, opt (Android PowerManager THERMAL_STATUS_*).
   - `batteryImpactPctPerHour`: number ≥ 0, opt (an estimate).

   **3.16 `ScreenLabel`**: "Ground-truth labels for one screenshot (the Phase 1.2 label format)."
   - `contractVersion`: req.
   - `image`: string `^[A-Za-z0-9._-]+\.png$`, req.
   - `width`, `height`: integer 1..16384, req.
   - `clean`: boolean, req; true means no labelled concept is present.
   - `boxes`: array of Box, maxItems 200, req.
   - `lookalikes`: array of slug, maxItems 16, opt; lookalike content present, e.g. ["dog", "fox"], used for AC-1.2-01's count.
   - `meta`: Meta, opt. **Meta**:
     - `app`: slug, req;
     - `surface`: string 1..40, req;
     - `mode`: enum ["dark", "light"], req;
     - `orientation`: enum ["portrait", "landscape"], req;
     - `source`: string 1..40, req (1.2.1 sidecar).
   - `labeller`: string ≤ 40, opt.
   - `reviewed`: boolean, opt.
   - **Box**:
     - `rect`: Rect, req;
     - `concept`: slug, req;
     - `kind`: enum ["photo", "cartoon", "drawing", "sticker", "emoji", "text", "other"], req;
     - `tag`: slug, opt; e.g. `cat-emoji`, `cat-text` (1.2.2);
     - `scope`: enum ["object", "wholeElement"], req;
     - `visibleFraction`: number 0..1, opt;
     - `postRect`: Rect, opt.
   - **Conditional:** `"if": {"properties": {"clean": {"const": true}}, "required": ["clean"]}, "then": {"properties": {"boxes": {"maxItems": 0}}}, "else": {"properties": {"boxes": {"minItems": 1}}}`.
4. **`contracts/README.md`** is written so the owner can review it in about 15 minutes. It contains:
   - Status: `DRAFT v1.0, awaiting owner approval (AC-1.1-05)`.
   - A table of the 16 types: type, file, one-line purpose, produced by, consumed by, fingerprint-bearing (yes/no).
   - Conventions: CONVENTIONS and SPACE_RULE verbatim, plus the no-null rule, `additionalProperties: false`, the base64 float16 encoding, and the id formats.
   - "Why ScreenLabel is the 16th type" (DV-5).
   - The freeze rule, copied from PLAN's 1.1 guarantee: "Contract v1.0 is frozen. Any change needs a version bump, a note to all owners, and a re-run of every test that uses the changed type." Also: Tape (2.1) and LookRequest (2.2) arrive as additive v1.1.
   - How to validate, regenerate and add an example.
   - **"Review checklist (AC-1.1-04)"** with five checkbox lines:
     1. every schema carries `contractVersion`;
     2. every fingerprint-bearing type (Embedding, CompiledConcept, Feedback) requires `spaceId`;
     3. the spaceId rule is written in those schemas;
     4. units and coordinate rules are stated in every schema;
     5. `pytest contracts/` passes.
     
     Each line names the test that enforces it.
5. **Examples.** They go in `contracts/examples/<file stem>/` (e.g. `contracts/examples/ui-event/`), named `valid-NN-<what>.json` and `invalid-NN-<why>.json`. Each file is one JSON object, pretty-printed with a 2-space indent and a trailing newline. Valid examples must be realistic (an Instagram feed on a 1440 × 3168 screen, cats and spiders). Vectors in examples use `dim` 8, made with `contracts/scripts/make_vector.py`; `embedding/valid-02` uses dim 768.

   | Type dir | Valid | Invalid (expected failing keyword(s)) |
   | --- | --- | --- |
   | rect | 01-basic, 02-offscreen-negative | 01-zero-width (minimum), 02-float-x (type) |
   | frame | 01-media-projection, 02-replay-with-own-overlay | 01-missing-ownOverlay (required), 02-bad-rotation (enum) |
   | ui-event | 01-scrolled, 02-window-changed, 03-content-changed, 04-nodes-snapshot, 05-screen-off, 06-screen-on | 01-scrolled-missing-dy (oneOf), 02-unknown-type (oneOf) |
   | region | 01-finder-box, 02-grid-tile | 01-bad-source (enum), 02-missing-rect (required) |
   | embedding | 01-text-prompt-dim8, 02-region-dim768 | 01-missing-spaceId (required), 02-bad-base64 (pattern) |
   | concept | 01-cats-layer2, 02-layer1-nudity | 01-layer1-blur (const), 02-empty-looksLike (minItems) |
   | concept-pack | 01-spiders-pack, 02-spoiler-pack-sensitive | 01-bad-semver (pattern), 02-no-concepts (minItems) |
   | compiled-concept | 01-cats-siglip2, 02-cats-yoloe-text | 01-missing-spaceId (required), 02-user-offset-too-big (maximum) |
   | finding | 01-hide-cat, 02-nearmiss-dog | 01-probability-above-1 (maximum), 02-bad-decision (enum) |
   | track | 01-confirmed, 02-parked | 01-bad-state (enum), 02-trackId-zero (minimum) |
   | mask | 01-layer2-blur, 02-layer1-solid | 01-layer1-peekable (const), 02-layer1-blur (const) |
   | mask-plan | 01-two-covers, 02-empty-clear | 01-25-masks (maxItems), 02-missing-reason (required) |
   | feedback | 01-not-this-fox, 02-missed-one | 01-layer1 (const), 02-notThis-without-embedding (required), 03-missing-spaceId (required) |
   | model-manifest | 01-siglip2-image-w8a16, 02-nudenet-320n | 01-dynamic-shape (minimum), 02-fingerprint-model-without-fingerprint (required) |
   | engine-stats | 01-balanced-running, 02-awaiting-permission | 01-negative-framesSkipped (minimum), 02-bad-captureState (enum) |
   | screen-label | 01-cats-explore-grid, 02-clean-with-lookalikes | 01-clean-with-boxes (maxItems), 02-jpg-image (pattern) |

   `contracts/examples/invalid-index.json` maps every invalid file's path, relative to `contracts/examples/` (e.g. `"rect/invalid-01-zero-width.json"`), to the list of acceptable keywords from the table.
6. **Python (`workshop/contracts/`):**
   ```python
   # __init__.py
   CONTRACT_VERSION: str = "1.0"
   TYPE_FILES: dict[str, str]  # 16 entries in the order of section 3: {"Rect": "rect.schema.json", ..., "ScreenLabel": "screen-label.schema.json"}
   TYPES: tuple[str, ...]      # tuple(TYPE_FILES)
   FINGERPRINT_TYPES: tuple[str, ...] = ("Embedding", "CompiledConcept", "Feedback")
   CONVENTIONS: str            # exact sentence of step 2
   SPACE_RULE: str             # exact sentence of step 2
   def example_dir(type_name: str) -> str: ...      # "ui-event"
   def model_class(type_name: str) -> type: ...     # getattr(workshop.contracts.models, type_name), imported lazily

   # validate.py
   REPO_ROOT: Path            # Path(__file__).resolve().parents[2]
   SCHEMA_DIR: Path           # REPO_ROOT / "contracts"
   def load_schema(type_name: str) -> dict: ...
   def registry() -> referencing.Registry: ...      # functools.cache; every schema registered under its file name, DRAFT202012
   def validator(type_name: str) -> jsonschema.Draft202012Validator: ...
       # Draft202012Validator({"$ref": TYPE_FILES[type_name]}, registry=registry())  — relative refs then resolve by file name
   def validate(type_name: str, instance: object) -> None: ...   # raises jsonschema.ValidationError (best_match)
   def error_keywords(type_name: str, instance: object) -> set[str]: ...  # every error.validator, recursing into error.context
   def type_for_path(path: Path) -> str: ...       # from the examples sub-folder name, or --type
   def main(argv: list[str] | None = None) -> int: ...
       # CLI: python -m workshop.contracts.validate FILE [FILE ...] [--type T] [--jsonl]
       # prints "OK <Type> <file>" or "INVALID <Type> <file>: <message>"; --jsonl validates each line; exit 0 iff all valid

   # rules.py   (cross-field rules JSON Schema cannot express; operate on plain dicts)
   class SpaceMismatchError(ValueError): ...
   class VectorError(ValueError): ...
   def encode_f16(vec) -> str: ...            # float64 L2-normalise, cast to "<f2", base64.b64encode(...).decode("ascii")
   def decode_f16(b64: str, dim: int) -> "np.ndarray": ...   # float32 array; VectorError if len(bytes) != 2*dim or non-finite
   def check_embedding(e: Mapping) -> None: ...               # decode; abs(norm - 1) <= 0.01
   def check_same_space(a: str, b: str) -> None: ...          # SpaceMismatchError if a != b
   def check_compiled_concept(cc: Mapping) -> None: ...       # every nested Embedding: spaceId == cc["spaceId"], same dim, check_embedding
   def check_feedback(fb: Mapping) -> None: ...               # if "embedding": its spaceId == fb["spaceId"], check_embedding
   def concept_sha256(concept: Mapping) -> str: ...           # sha256 of json.dumps(concept, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
   def check_rules(type_name: str, instance: Mapping) -> None: ...   # dispatches the three checks above; no-op for other types
   ```
   `models.py` is **generated**; never edit it by hand.
7. **Code generation.** `contracts/scripts/gen_python.py [--check] [--out PATH]`, default out `workshop/contracts/models.py`:
   1. Load the 16 schemas in `TYPE_FILES` order.
   2. Build one bundle `{"$schema": ".../2020-12/schema", "title": "VeilContracts", "$defs": {}}`. For each schema, deep-copy it and drop `$schema` and `$id`.
   3. Move each nested `$defs` entry `K` to `bundle["$defs"][Title + K]`.
   4. Rewrite refs: `"#/$defs/K"` (in-file) → `"#/$defs/<Title><K>"`; `"<file>.schema.json"` → `"#/$defs/<that file's Title>"`; `"<file>.schema.json#/$defs/K"` → `"#/$defs/<that Title><K>"`.
   5. Set `bundle["$defs"][Title] = schema`.
   6. Recursively delete the keys `if`, `then` and `else` from the bundle. The models are typing helpers; jsonschema enforces the conditionals.
   7. Write the bundle to a temp dir and run, via `subprocess.run([sys.executable, "-m", "datamodel_code_generator", ...], check=True)`, with these flags: `--input <tmp>/bundle.json --input-file-type jsonschema --output <tmp>/models.py --output-model-type pydantic_v2.BaseModel --target-python-version 3.11 --use-standard-collections --use-union-operator --enum-field-as-literal all --use-schema-description --use-field-description --field-constraints --use-double-quotes --disable-timestamp --use-title-as-name --extra-fields forbid --use-one-literal-as-default --formatters builtin`. If `--formatters builtin` is rejected, use `--formatters black isort`, which are both datamodel-code-generator dependencies, and record that.
   8. Prepend the header `# GENERATED by contracts/scripts/gen_python.py from contracts/*.schema.json (contract v1.0). Do not edit.`
   9. Without `--check`, write the file. With `--check`, compare bytes with the existing file and exit 1 if they differ.
   
   `contracts/scripts/make_vector.py --dim N --seed S` prints the base64 of `encode_f16(np.random.default_rng(S).standard_normal(N))`.
8. **Tests (`contracts/tests/`), all parametrized by type or example file:**
   - **`test_schemas.py`:**
     - `test_exactly_16_schema_files`: the glob `contracts/*.schema.json` equals the set of `TYPE_FILES` values;
     - `test_valid_draft_2020_12[type]`: `Draft202012Validator.check_schema`;
     - `test_contract_version_defined[type]`: present with const "1.0", in every UiEvent variant too;
     - `test_contract_version_required_except_rect[type]`;
     - `test_fingerprint_types_require_space_id[type in FINGERPRINT_TYPES]`;
     - `test_conventions_stated[type]`: CONVENTIONS is a substring of the top-level description;
     - `test_space_rule_stated[type in FINGERPRINT_TYPES + ("ModelManifest",)]`;
     - `test_defs_titles[type]`: every `$defs` title is `<Title><Key>`;
     - `test_no_null_anywhere[type]`: no `"null"` type anywhere;
     - `test_objects_closed[type]`: every `"type": "object"` has `additionalProperties: false`.
   - **`test_examples.py`:**
     - `test_counts[type]`: at least 2 valid and at least 1 invalid; prints the counts;
     - `test_valid_example[file]`;
     - `test_invalid_example[file]`: not valid, and `error_keywords(...) ∩ index[file]` is non-empty;
     - `test_invalid_index_complete`: index keys == the invalid files on disk.
   - **`test_models.py`:**
     - `test_model_parses_valid_example[file]`: `model_class(T).model_validate(obj)`;
     - `test_model_dump_revalidates[file]`: `model_dump(mode="json", exclude_none=True)` validates against the schema.
   - **`test_codegen.py`:** `test_models_up_to_date` runs `gen_python.py --check` and expects exit 0.
   - **`test_rules.py`:**
     - `test_rules_pass_on_valid_examples[file]`;
     - `test_space_mismatch_raises`: a CompiledConcept whose nested embedding has another spaceId;
     - `test_bad_vector_length_raises`;
     - `test_encode_decode_roundtrip`: cosine ≥ 0.999;
     - `test_concept_sha256_is_key_order_independent`.
9. Run `WE uv run --locked python contracts/scripts/gen_python.py`, then the whole Verification table. Fill in the Builder sections of `1.1.2-shared-contracts-first-version.md`.

### Must not

- Must not edit `pyproject.toml` or `uv.lock`. If a dependency is missing, report SPEC_ISSUE.
- Must not write Kotlin or Dart contract types (out of scope, 5.1/6.1).
- Must not add schemas beyond the 16 (Tape and LookRequest belong to 2.1 and 2.2).
- Must not hand-edit `models.py`.
- Must not run Gradle or Flutter.

### Verification (the orchestrator runs these)

| # | Command (run from veil/) | Expected result | Covers |
| --- | --- | --- | --- |
| 1 | `(Get-ChildItem contracts\*.schema.json).Count` | `16` | deliverable |
| 2 | `WE uv run --locked pytest contracts -q` | 0 failed. At least 100 passed (16 types × examples + rule tests). No errors | AC-1.1-03; Do 6 |
| 3 | `WE uv run --locked pytest contracts/tests/test_examples.py -q -k "counts or invalid"` | All pass. Every type has ≥ 2 valid and ≥ 1 invalid, and every invalid example is rejected for its indexed reason | AC-1.1-03 |
| 4 | `WE uv run --locked pytest contracts/tests/test_schemas.py -q` | All pass (contractVersion, spaceId, conventions, spaceId rule) | AC-1.1-04 |
| 5 | `WE uv run --locked python contracts/scripts/gen_python.py --check` | Exit 0 | Do 4 |
| 6 | `WE uv run --locked python -c "from workshop.contracts import TYPES; print(len(TYPES))"` | `16` | Do 1 |
| 7 | `WE uv run --locked python -m workshop.contracts.validate contracts/examples/rect/valid-01-basic.json contracts/examples/ui-event/valid-04-nodes-snapshot.json` | Two `OK` lines, exit 0 | validator CLI |
| 8 | `WE uv run --locked python -m workshop.contracts.validate contracts/examples/mask/invalid-01-layer1-peekable.json` | An `INVALID` line, exit 1 | validator CLI |
| 9 | `WE uv run --locked ruff check contracts workshop/contracts` and `WE uv run --locked ruff format --check contracts workshop/contracts` | Both exit 0 (`models.py` excluded) | formatting |
| 10 | `Select-String -Path contracts\README.md -Pattern 'Review checklist \(AC-1.1-04\)','ScreenLabel'` | Both found | AC-1.1-04, AC-1.1-05 prep |

"Done when" (PLAN): "The validation test passes and all four owners have reviewed and agreed the shapes."
- The test is rows 2-4. The agreement is HUMAN (AC-1.1-05) and goes to the Human sitting.
- Machine work makes the sub-phase VERIFIED; the phase stays WAITING_HUMAN until approval.

- **Needs a human:** The owner approves v1.0 (Human sitting step 8). The Builder does nothing for this beyond writing `contracts/README.md`.
- **Size:** M.

---

## 4. Sub-phase 1.1.3 Device check and accounts

- **Goal:** everything needed to know the phone and reach the cloud. That means a device-profile script and a chip check; AI Hub and Hugging Face checks; the first Test Feed app; adb driver helpers; and one `bench_check` command that runs the Phase 1.1 proof test and reports SKIP-with-reason for whatever needs the phone or a token.
- **Owned paths:**
  - `guard/testfeed/**`
  - `workshop/bench/**`
  - `tools/bench_check.ps1`, `tools/bench_check.sh`
  - `docs/device-profile.md`, `docs/bench-check.md`
  - **`docs/decisions.md` is NOT owned:** only the script edits it at run time, between its markers.
- **Read-only inputs:**
  - from 1.1.1: `guard/` (settings already include `:testfeed` when it exists), `tools/env.ps1`, `tools/with-env.ps1`, `tools/bootstrap.ps1`, `pyproject.toml`, `uv.lock`;
  - `docs/decisions.md`;
  - `contracts/` (only through `pytest contracts`).

### Steps

1. **Test Feed app v1 (`guard/testfeed/`, package `com.veil.testfeed`).**
   - **`build.gradle.kts`:** a copy of `guard/app/build.gradle.kts` with namespace and applicationId `com.veil.testfeed`, and only `testImplementation(libs.junit)` as a dependency.
   - **Manifest:** label "Veil Test Feed", theme `@android:style/Theme.DeviceDefault.Light.NoActionBar`, and activity `.FeedActivity` exported with a MAIN/LAUNCHER intent-filter.
   - Kotlin in `src/main/java/com/veil/testfeed/`:
     ```kotlin
     data class FeedItem(val id: String, val kind: String, val heightDp: Int, val color: Int, val label: String)
     object FeedItems {
         val KINDS = listOf("clean", "cat", "clean", "spider", "lookalike", "clean", "ruler", "repost")
         /** 60 items, i = 0..59: id "item-%03d", kind KINDS[i % 8], heightDp 480 for "ruler" else 320,
          *  color by kind (clean 0xFFECEFF1, cat 0xFFFFCC80, spider 0xFFB39DDB, lookalike 0xFFA5D6A7, ruler 0xFFFFFFFF, repost 0xFFFFCC80),
          *  label "#%03d <kind>" (+ " of item-001" for repost). Deterministic. */
         fun defaultFeed(): List<FeedItem>
     }
     data class IntRect(val x: Int, val y: Int, val w: Int, val h: Int)
     data class ItemLayout(val itemId: String, val kind: String, val contentY: Int, val h: Int)   // px, in scroll-content coordinates
     data class VisibleItem(val itemId: String, val kind: String, val rect: IntRect)          // screen px, unclipped
     object FeedGeometry {
         /** Items whose [contentY, contentY+h) intersects [scrollY, scrollY+viewport.h); rect.y = viewport.y + contentY - scrollY,
          *  rect.x = viewport.x, rect.w = viewport.w, rect.h = h. Order = feed order. */
         fun visible(items: List<ItemLayout>, scrollY: Int, viewport: IntRect): List<VisibleItem>
     }
     object FeedJson {   // manual JSON building, no org.json (JVM-testable)
         fun session(tMs: Long, screenW: Int, screenH: Int, densityDpi: Int, viewport: IntRect, items: List<ItemLayout>): String
         fun frame(tMs: Long, scrollY: Int, visible: List<VisibleItem>): String
         fun tap(tMs: Long, x: Int, y: Int, itemId: String?): String
         fun pause(tMs: Long): String
     }
     class FeedLogger(file: java.io.File) { fun log(line: String); fun flush(); fun close() }   // BufferedWriter, truncates file on create
     class RulerView(context: Context) : View(context)   // 1 px tick every 10 px (20 px long), 60 px tick + label "<px>" every 100 px
     class FeedActivity : Activity()
     ```
   - **`FeedActivity` behaviour:**
     - **Layout:** a `ScrollView` holding a vertical `LinearLayout` with one child per item. A child is a `FrameLayout` with its kind's colour, the item's height in px plus an 8 dp bottom margin, and a large `TextView` label; for `ruler` items the child is a `RulerView` instead.
     - **Log file:** `filesDir/feedlog.jsonl` (`FeedLogger`), truncated in `onCreate`.
     - **After first layout:** log `session`, including every item's `contentY` and `h`, and the viewport from `getLocationOnScreen` plus the width and height.
     - **Each frame:** a `Choreographer.FrameCallback` runs while resumed. When `scrollY` differs from the last logged value, or on the first frame, it logs `frame` with `tMs = frameTimeNanos / 1_000_000`, which is on the same CLOCK_MONOTONIC base as `SystemClock.uptimeMillis()`.
     - **Taps:** `dispatchTouchEvent` logs a `tap` on an ACTION_UP within touch slop and under 500 ms of its ACTION_DOWN, using `event.eventTime` and the hit-tested itemId.
     - **Flushing:** every 500 ms via a `Handler`, and in `onPause` (which also logs `pause`).
     - **Logcat:** tag `VeilFeed`, `VEIL_FEED session items=60` at start.
   - **Log line formats** (one JSON object per line; documented in `guard/testfeed/README.md`):
     - `{"type":"session","v":1,"tMs":…,"screenWidthPx":…,"screenHeightPx":…,"densityDpi":…,"viewport":{"x":…,"y":…,"w":…,"h":…},"items":[{"itemId":"item-000","kind":"clean","contentY":0,"h":…},…]}`
     - `{"type":"frame","tMs":…,"scrollY":…,"visible":[{"itemId":"item-003","kind":"spider","rect":{"x":…,"y":…,"w":…,"h":…}},…]}`
     - `{"type":"tap","tMs":…,"x":…,"y":…,"itemId":"item-004"}`, with `itemId` omitted when the tap misses every item.
     - `{"type":"pause","tMs":…}`
     - Rects use the contract's `Rect` shape and screen pixels.
   - **JVM unit tests** (`src/test/java/com/veil/testfeed/`):
     - `FeedItemsTest`: 60 items, unique ids, deterministic, item-006 is a ruler of 480 dp;
     - `FeedGeometryTest`: scrollY 0, a mid-scroll partial overlap, and past the end;
     - `FeedJsonTest`: an exact string for one frame line.
   - Run ktlint `--format` on `guard/testfeed/**`.
2. **`workshop/bench/` (Python package; every module has `from __future__ import annotations`).**
   ```python
   # adb.py — thin wrappers; adb executable = os.environ.get("ADB") or "adb"
   class AdbError(RuntimeError): ...
   def run(args: list[str], serial: str | None = None, timeout: float = 60, check: bool = True, text: bool = True) -> subprocess.CompletedProcess: ...
   def devices() -> list[tuple[str, str]]: ...            # parse `adb devices` -> [(serial, state)]
   def single_device() -> str | None: ...                 # the only serial in state "device"; None if 0; AdbError if >1 (message lists states)
   def shell(serial: str, cmd: str, timeout: float = 60) -> str: ...
   def getprop(serial: str) -> dict[str, str]: ...
   def install_if_changed(serial: str, apk: Path, package: str, force: bool = False, timeout: float = 180) -> str: ...
       # returns "installed" or "unchanged"; compares local sha256 with `sha256sum $(pm path <pkg> | first base.apk path)`; else `adb install -r <apk>`
   def launch(serial: str, component: str) -> None: ...  # am start -W -n <component>
   def force_stop(serial: str, package: str) -> None: ...
   def resumed_activity(serial: str) -> str | None: ...   # parse `dumpsys activity activities` (topResumedActivity / mResumedActivity)
   def screencap(serial: str, dest: Path) -> None: ...    # `adb exec-out screencap -p` bytes -> dest
   def swipe(serial: str, x1: int, y1: int, x2: int, y2: int, duration_ms: int) -> None: ...
   def keyevent(serial: str, key: str) -> None: ...
   def logcat_clear(serial: str) -> None: ...
   def logcat_dump(serial: str, filterspecs: list[str]) -> str: ...   # adb logcat -d -s <specs>
   def run_as_cat(serial: str, package: str, rel_path: str) -> bytes: ...   # adb exec-out run-as <pkg> cat <rel_path>
   def screen_size(serial: str) -> tuple[int, int]: ...   # from `wm size` (Override size wins if present)

   # parse.py — pure functions, unit-tested with fixtures
   def parse_devices(text: str) -> list[tuple[str, str]]: ...
   def parse_getprop(text: str) -> dict[str, str]: ...    # lines "[key]: [value]"
   def parse_wm_size(text: str) -> tuple[int, int]: ...
   def parse_wm_density(text: str) -> int: ...
   def parse_meminfo_total_bytes(text: str) -> int: ...   # "MemTotal: N kB" * 1024
   def parse_refresh_rates(dumpsys_display: str) -> list[float]: ...   # unique sorted values of r"fps=([0-9.]+)"
   def parse_resumed_activity(text: str) -> str | None: ...
   def parse_hello_line(logcat: str) -> dict | None: ...  # JSON after the last "VEIL_HELLO "
   def marketing_ram_gb(total_bytes: int) -> int: ...     # smallest of [4,6,8,12,16,18,20,24,32] with s*2**30 >= total_bytes
   def chip_family_match(soc_model: str, board_platform: str) -> bool: ...   # soc_model.upper().startswith("SM8850") or board_platform == "canoe"
   def detect_os_skin(props: dict[str, str]) -> tuple[str, str]: ...
       # name: "OriginOS" if any value contains "originos" (case-insensitive), elif "funtouch" -> "Funtouch OS", else "unknown";
       # version: props["ro.vivo.os.version"] if present, else first r"\d+(\.\d+)*" in the value that matched the name, else "unknown"
   ALLOWED_PROPS: tuple[str, ...] = ("ro.soc.model","ro.soc.manufacturer","ro.board.platform","ro.hardware","ro.product.board",
       "ro.product.manufacturer","ro.product.brand","ro.product.model","ro.product.device","ro.product.name",
       "ro.build.version.release","ro.build.version.sdk","ro.build.version.security_patch","ro.build.display.id",
       "ro.build.id","ro.build.version.incremental","ro.build.fingerprint")
   SKIN_KEY_RE = re.compile(r"^ro\.(vivo|iqoo)\.[a-z0-9_.]*(os|rom|version|name)[a-z0-9_.]*$", re.I)
   def filter_props(props: dict[str, str]) -> dict[str, str]: ...   # ALLOWED_PROPS + SKIN_KEY_RE keys + any key whose value contains originos/funtouch; never serials

   # device_profile.py
   @dataclass(frozen=True)
   class DeviceProfile:
       capturedAt: str; socModel: str; socManufacturer: str; boardPlatform: str; hardware: str; chipFamilyMatch: bool
       manufacturer: str; brand: str; model: str; device: str
       androidRelease: str; sdkInt: int; buildDisplay: str; securityPatch: str; fingerprint: str
       osSkinName: str; osSkinVersion: str
       ramTotalBytes: int; ramMarketingGb: int
       screenWidthPx: int; screenHeightPx: int; densityDpi: int; refreshRatesHz: list[float]
   RAW_FILES = {"getprop": "getprop-filtered.txt", "meminfo": "meminfo.txt", "wm_size": "wm-size.txt",
                "wm_density": "wm-density.txt", "display": "dumpsys-display-modes.txt"}
   def collect(serial: str) -> tuple[DeviceProfile, dict[str, str]]: ...  # raw texts keyed like RAW_FILES (getprop already filtered;
                                                                         # display keeps only lines matching r"fps=|refreshRate")
   def from_dir(path: Path) -> tuple[DeviceProfile, dict[str, str]]: ...
   def render_markdown(p: DeviceProfile) -> str: ...
   def load_profile_json(md_path: Path) -> dict | None: ...   # JSON between the markers; None when "null"
   def update_decisions(decisions_md: Path, p: DeviceProfile, today: str) -> None: ...
   def main(argv: list[str] | None = None) -> int: ...
       # python -m workshop.bench.device_profile [--write] [--docs-dir docs] [--evidence-dir DIR] [--serial S] [--from-dir DIR]
       # no --write: print markdown; --write: write <docs-dir>/device-profile.md and update <docs-dir>/decisions.md;
       # --evidence-dir: save RAW_FILES there. Exit 0 ok; 3 no device; 4 several devices and no --serial; 1 other error.

   # aihub.py
   FAMILY_RE = re.compile(r"8[\s_-]*elite[\s_-]*gen[\s_-]*5|sm8850", re.I)
   def is_configured() -> bool: ...   # Path(os.environ.get("QAIHUB_CLIENT_INI", "~/.qai_hub/client.ini")).expanduser().exists()
   def family_devices() -> list[str]: ...   # sorted names of hub.get_devices() whose name or any attribute matches FAMILY_RE
   def make_tiny_onnx(path: Path) -> None: ...   # x float32 [1,3,32,32] -> Conv(8 filters 3x3, pads 1, weights rng(0)) -> Relu -> y; opset 17, ir_version 10
   def tiny_profile(device_name: str, workdir: Path, timeout_s: int = 1800) -> dict: ...
       # cjob = hub.submit_compile_job(model=str(onnx), device=hub.Device(device_name), name="veil-1.1-bench-tiny",
       #                               options="--target_runtime tflite"); cjob.wait(); if not cjob.get_status().success: retry once with
       #                               "--target_runtime qnn_dlc"; target = cjob.get_target_model()
       # pjob = hub.submit_inference_job(model=target, device=hub.Device(device_name), profile=True, name="veil-1.1-bench-tiny")
       # pjob.wait(timeout=timeout_s); profile = pjob.download_profile()
       # return {"device": ..., "compileJobId": cjob.job_id, "profileJobId": pjob.job_id, "targetRuntime": ...,
       #         "estimatedInferenceTimeUs": profile["execution_summary"]["estimated_inference_time"], "url": pjob.url}

   # hf.py
   PROBE_REPO = "google/siglip2-base-patch16-224"; PROBE_FILE = "config.json"
   def token_configured() -> bool: ...   # huggingface_hub.get_token() is not None (never print the token)
   def anonymous_probe() -> str: ...     # hf_hub_download(PROBE_REPO, PROBE_FILE, token=False) -> local path (inside HF_HOME)

   # testfeed.py
   @dataclass
   class FeedSummary: frames: int; max_scroll_y: int; first_visible_start: str | None; first_visible_end: str | None; taps: int; has_session: bool
   def parse_feed_log(text: str) -> FeedSummary: ...
   def scroll_check(s: FeedSummary, screen_height_px: int) -> tuple[bool, str]: ...
       # pass iff has_session and frames >= 10 and max_scroll_y >= 0.8*screen_height_px and first_visible_end != first_visible_start

   # drive.py — first driver script (PLAN Test fixtures #2)
   def scroll(serial: str, times: int = 3, fraction: float = 0.45, duration_ms: int = 250, pause_ms: int = 600) -> None: ...
       # swipe from (w/2, 0.75h) to (w/2, (0.75-fraction)h)
   def main(argv: list[str] | None = None) -> int: ...   # python -m workshop.bench.drive scroll|fling|tap|home [...]

   # a11y_probe.py — optional, used only in the Human sitting
   PROBE = "com.veil.guard/com.veil.guard.probe.ProbeAccessibilityService"
   def main(argv: list[str] | None = None) -> int: ...
       # status: print `settings get secure enabled_accessibility_services` and whether PROBE is bound (`dumpsys accessibility`)
       # enable: append PROBE to the colon-separated list (keep every existing entry), then `settings put secure accessibility_enabled 1`
       # disable: remove PROBE only; if the list becomes empty, restore the exact value read before enable (saved in data/evidence/1.1/a11y-before.txt)

   # bench_check.py
   LINE_IDS = ("toolchain","python-tests","contracts","build-guard","build-console","adb","scrcpy",
               "guard-app","console-app","testfeed","aihub-devices","aihub-profile","huggingface")
   @dataclass
   class LineResult: id: str; status: Literal["PASS","FAIL","SKIP"]; detail: str; seconds: float
   def main(argv: list[str] | None = None) -> int: ...
   ```
3. **`bench_check` behaviour.** Options:
   - `--out DIR`, default `data/evidence/1.1/bench-<YYYYmmdd-HHMMSS>/`;
   - `--build {if-missing,always,never}`, default `if-missing`;
   - `--skip-phone`, `--skip-cloud`;
   - `--only ID[,ID…]`;
   - `--serial S`;
   - `--reinstall`.

   It runs the lines in `LINE_IDS` order, **sequentially**, flushes each result line as it finishes, and writes `bench-check.txt` and `bench-check.json` into `--out`.
   - It calls helpers as module attributes (`adb.single_device()`, `aihub.is_configured()`, …) so tests can monkeypatch them.
   - When `--only` leaves out a build line and an APK is missing, the app line FAILs with `APK missing: <path> (run without --only, or build first)`.
   - **Line format, ASCII only:** `[PASS] guard-app      installed (unchanged); live soc=SM8850 android=16/API 36 ram=15.6 GiB match docs/device-profile.md`.
   - **Last line:** `RESULT: <n> PASS, <n> FAIL, <n> SKIP`.
   - **Exit code:** 0 if all PASS; 1 if any FAIL; 2 if no FAIL and at least one SKIP.

   | Line | What it does | PASS when | SKIP when (reason text) |
   | --- | --- | --- | --- |
   | toolchain | `powershell -NoProfile -ExecutionPolicy Bypass -File tools/bootstrap.ps1 -CheckOnly` | exit 0 | never |
   | python-tests | `[sys.executable, "-m", "pytest", "-q", "workshop"]` | exit 0 | never |
   | contracts | `[sys.executable, "-m", "pytest", "-q", "contracts"]` | exit 0 | never |
   | build-guard | When needed: `guard\gradlew.bat --no-daemon :app:assembleDebug :testfeed:assembleDebug` (cwd `guard`) | both APKs exist: `guard/app/build/outputs/apk/debug/app-debug.apk`, `guard/testfeed/build/outputs/apk/debug/testfeed-debug.apk` | never |
   | build-console | When needed: `shutil.which("flutter")` (resolves `flutter.bat`), then `[flutter, "build", "apk", "--debug"]` (cwd `console`), after build-guard finishes | `console/build/app/outputs/flutter-apk/app-debug.apk` exists | never |
   | adb | `single_device()` | exactly one device in state `device` (detail shows the first 8 hex of the serial's sha256, not the serial) | `--skip-phone`, or 0 devices: `no adb device (connect the phone: HC-002)`. Unauthorized device → FAIL `accept the USB debugging prompt` |
   | scrcpy | `scrcpy --serial <s> --no-window --no-audio --record=<out>/scrcpy.mp4 --time-limit=5`, then `ffprobe -v error -show_entries format=duration -of default=nw=1:nk=1` | exit 0 and duration ≥ 3.0 s | adb not PASS |
   | guard-app | Wake: `keyevent KEYCODE_WAKEUP`, then `keyevent 82`. `install_if_changed`; `force_stop com.veil.guard`; `logcat_clear`; `launch com.veil.guard/.MainActivity`; wait up to 10 s for `VEIL_HELLO` in `logcat_dump(["VeilHello:I"])`; `screencap guard.png`; compare with `load_profile_json(docs/device-profile.md)` | Hello JSON parsed, and socModel, androidRelease and sdkInt are equal, and `abs(ram - profileRam) / profileRam <= 0.01`. FAIL `docs/device-profile.md is PENDING: run device_profile --write` if the profile is null | adb not PASS |
   | console-app | `install_if_changed`; `force_stop com.veil.console`; `launch com.veil.console/.MainActivity`; poll `resumed_activity` up to 15 s; `screencap console.png` | the resumed activity contains `com.veil.console` | adb not PASS |
   | testfeed | In this order: `install_if_changed`; `force_stop com.veil.testfeed` (so `onCreate` truncates the log); `launch com.veil.testfeed/.FeedActivity`; sleep 2 s; `drive.scroll(times=3)`; `screencap testfeed.png`; `keyevent KEYCODE_HOME` (onPause flushes the log); sleep 1 s; `run_as_cat(..., "files/feedlog.jsonl")`, saved as `feedlog.jsonl`; then `scroll_check` | `scroll_check` passes | adb not PASS |
   | aihub-devices | `aihub.family_devices()`; write the names to `aihub-devices.txt` | ≥ 1 device | `--skip-cloud`, or not `is_configured()`: `AI Hub not configured (HC-003)` |
   | aihub-profile | `tiny_profile(family_devices()[0], out)`; write `aihub-profile.json` | `estimatedInferenceTimeUs > 0` | as above, or when aihub-devices did not PASS |
   | huggingface | `anonymous_probe()`; the detail adds `token: configured` or `token: not configured (optional)` | the file was downloaded | `--skip-cloud` |

   Every subprocess has a timeout:
   - builds: 45 min each;
   - pytest: 10 min;
   - AI Hub: 30 min;
   - all others: 3 min.

   A timeout counts as FAIL, with `timed out after <n> s`.
4. **`tools/bench_check.ps1`**: `$env:VEIL_ENV_QUIET='1'; . "$PSScriptRoot\env.ps1"; Set-Location (Split-Path -Parent $PSScriptRoot); & uv run --locked python -m workshop.bench.bench_check @args; exit $LASTEXITCODE`. **`tools/bench_check.sh`** is the same for Git Bash.
5. **`docs/device-profile.md`**, the committed initial (PENDING) content:
   ````
   # Device profile
   Status: PENDING - the phone has not been connected yet (HC-002).
   Generate this file with: `uv run python -m workshop.bench.device_profile --write --evidence-dir <phase evidence folder>`

   <!-- DEVICE-PROFILE-JSON:BEGIN -->
   ```json
   null
   ```
   <!-- DEVICE-PROFILE-JSON:END -->
   ````
   **`render_markdown` output, once measured:**
   - the heading `# Device profile`;
   - `Status: MEASURED (captured <capturedAt> by workshop.bench.device_profile)`;
   - a table with rows Phone, Chip (with `8 Elite Gen 5 family: YES/NO`), Android (release, API level, build display, security patch), OS skin, RAM (marketing GB and exact bytes), Screen (w × h px, dpi) and Refresh rates (Hz);
   - the line `Raw values (allowlisted properties only; no serial numbers) are saved in the phase evidence folder.`;
   - the JSON block between the same markers, holding `dataclasses.asdict(profile)`.
   
   **`update_decisions` upserts** between `<!-- veil:target-chip:begin -->` and `<!-- veil:target-chip:end -->`. On first insert it uses the next free `D-NNN` number, which is D-004 if D-001..D-003 exist, under the heading `## D-NNN · Target chip check`, with `Date: <today> · Source: docs/device-profile.md`, and then either:
   - `Result: CONFIRMED - <soc> (platform <platform>) is the Snapdragon 8 Elite Gen 5 family. Published speeds in PLAN.md apply.`, or
   - `Result: FLAGGED - the phone reports <soc> / <platform>, not the Snapdragon 8 Elite Gen 5 family (SM8850). Published speeds in PLAN.md may not apply; Chapter 3 must rely on measured numbers.`
   
   Also add the line `Phone runs Android API <sdk>; apps target API 36.` and, if sdk > 36, the line `Note: moving to targetSdk <sdk> needs platforms;android-<sdk> and AGP >= 9.1.1.`
6. **`docs/bench-check.md`**:
   - what each of the 13 lines proves and how it maps to PT-1.1's "It should check" bullets;
   - the flags and exit codes;
   - where the output goes;
   - troubleshooting: an install prompt on vivo/iQOO, a locked screen, an `unauthorized` device, AI Hub not configured, the device profile PENDING;
   - the optional `a11y_probe` and `drive` commands.
7. **Tests (`workshop/bench/tests/`):**
   - **Fixtures** in `workshop/bench/tests/fixtures/sm8850/`. All synthetic; a `README.md` says so. Model name `SYNTHETIC-IQOO15`.
     - `getprop.txt` with the allowlisted keys plus `ro.vivo.os.name=OriginOS` and `ro.vivo.os.version=6.0`;
     - `meminfo.txt` with `MemTotal: 15728640 kB`;
     - `wm-size.txt` with `Physical size: 1440x3168`;
     - `wm-density.txt` with `Physical density: 510`;
     - `dumpsys-display-modes.txt` with modes at fps 60.0, 90.0, 120.0 and 144.0;
     - `devices-*.txt` variants (none, one, unauthorized, two);
     - `activities.txt`;
     - `logcat-hello.txt`;
     - `feedlog-ok.jsonl` and `feedlog-noscroll.jsonl`.
   - **`test_parse.py`:** every parse function, `marketing_ram_gb(15728640*1024) == 16`, `chip_family_match("SM8850", "")` true and `("SM8750", "sun")` false, and `detect_os_skin`.
   - **`test_device_profile.py`:**
     - `from_dir` builds the expected profile;
     - `render_markdown` round-trips through `load_profile_json`;
     - `update_decisions` on a tmp copy (D-001..D-003 present) inserts D-004 CONFIRMED, a second call replaces it rather than duplicating it, and a non-SM8850 profile writes FLAGGED;
     - `main(["--from-dir", fixtures, "--docs-dir", tmp, "--write"]) == 0`.
   - **`test_testfeed.py`:** `scroll_check` passes on `feedlog-ok` and fails on `feedlog-noscroll`.
   - **`test_bench_check.py`:** with `adb.devices` monkeypatched to return nothing and `aihub.is_configured` returning False, `main(["--only", "adb,scrcpy,guard-app,console-app,testfeed,aihub-devices,aihub-profile", "--out", tmp])` returns 2, and every line is SKIP with the reason texts above.
   - **`test_aihub.py`:** `make_tiny_onnx` gives a model that passes `onnx.checker` and runs in onnxruntime with output shape `[1,8,32,32]`. No network.
8. Run the Verification table. Fill in the Builder sections of `1.1.3-device-check-and-accounts.md`.

### Must not

- Must not edit `docs/decisions.md` by hand, or `guard/app/**`, `guard/settings.gradle.kts`, `pyproject.toml` or `uv.lock`. If a dependency is missing, report SPEC_ISSUE.
- Must not store or print any token or the adb serial.
- Must not call `a11y_probe enable/disable` or change any phone setting during the build.
- Must not install packages other than `com.veil.guard`, `com.veil.console` and `com.veil.testfeed`.
- Must not run Gradle at the same time as another heavy job.

### Verification (the orchestrator runs these)

| # | Command (run from veil/) | Expected result | Covers |
| --- | --- | --- | --- |
| 1 | `WE --cd guard .\gradlew.bat --no-daemon :testfeed:assembleDebug :testfeed:testDebugUnitTest :app:assembleDebug` | `BUILD SUCCESSFUL`. `guard\testfeed\build\outputs\apk\debug\testfeed-debug.apk` exists | Test Feed v1 |
| 2 | `WE uv run --locked pytest workshop/bench -q` | 0 failed | bench logic |
| 3 | `WE java -jar D:\veil-toolchain\ktlint\ktlint.jar "guard/testfeed/**/*.kt" "guard/testfeed/**/*.kts"` | Exit 0 | Do 5 (Kotlin formatting) |
| 4 | `WE uv run --locked ruff check workshop/bench` and `WE uv run --locked ruff format --check workshop/bench` | Exit 0 | formatting |
| 5 | `WE uv run --locked python -m workshop.bench.device_profile` (no phone) | Exit 3. The output contains `no adb device` | 1.1.3 Do 1-3 (ready-to-run) |
| 6 | `WE uv run --locked python -m workshop.bench.device_profile --from-dir workshop/bench/tests/fixtures/sm8850` | Exit 0. The printed markdown contains `8 Elite Gen 5 family: YES` and `OriginOS 6.0` | Do 2-3 |
| 7 | `powershell -NoProfile -ExecutionPolicy Bypass -File tools\bench_check.ps1 --build never --out data\evidence\1.1\bench-nophone` (run after wave 2, with no phone and no token) | Exit 2. The output contains these lines: `[PASS] toolchain`, `[PASS] python-tests`, `[PASS] contracts`, `[PASS] build-guard`, `[PASS] build-console`, `[SKIP] adb … HC-002`, SKIP for `scrcpy`, `guard-app`, `console-app` and `testfeed`, `[SKIP] aihub-devices … HC-003`, `[SKIP] aihub-profile`, `[PASS] huggingface … token: not configured (optional)`, and `RESULT: 6 PASS, 0 FAIL, 7 SKIP` | PT-1.1 machine readiness |
| 8 | `Select-String -Path docs\device-profile.md -Pattern 'Status: PENDING','DEVICE-PROFILE-JSON:BEGIN'` | Both found | deliverable (template) |
| P1 | PHONE, after HC-002: `WE uv run --locked python -m workshop.bench.device_profile --write --evidence-dir "D:\iqoo finale\progress\ch1-see\phase-1.1-foundations\evidence"` | Exit 0. `docs\device-profile.md` says `Status: MEASURED`. `docs\decisions.md` has a `Target chip check` entry (CONFIRMED or FLAGGED). The evidence dir has `getprop-filtered.txt` and the other raw files. These two doc changes are expected script output; the orchestrator commits them as `[1.1.3] device profile` | AC-1.1-06; 1.1.3 "Done when" (profile) |
| P2 | PHONE + cloud, after HC-002 and HC-003: `powershell -NoProfile -ExecutionPolicy Bypass -File tools\bench_check.ps1` | Exit 0 and `RESULT: 13 PASS, 0 FAIL, 0 SKIP` | PT-1.1; AC-1.1-02; AC-1.1-07 |

"Done when" (PLAN): "`qai-hub list-devices` works from the laptop, and the device profile is filled in." Both need HC-002 and HC-003, so the sub-phase is VERIFIED for machine work (rows 1-8) and WAITING_HUMAN for P1-P2.

- **Needs a human:** HC-002 (phone), HC-003 (AI Hub token), and the accessibility probe test (Human sitting step 7).
  - Until then, the Builder's code reports SKIP-with-reason.
  - The Builder reports DONE for machine work, with P1-P2 noted as pending those HCs.
- **Size:** M.

---

## 5. Acceptance plan

| AC | Type | Procedure or command | Threshold (verbatim from PLAN) | Evidence file |
| --- | --- | --- | --- | --- |
| AC-1.1-01 | CLEAN | Run by a fresh Checker (prompt C), allowed input `veil/README.md` only, **alone** (heavy). The Checker: (1) runs `git clone "D:/iqoo finale/veil" "D:/veil-cleanroom-1.1/veil"` (on D:; this space-free parent also gives a fresh toolchain at `D:\veil-cleanroom-1.1\toolchain` by the DV-1 rule, so nothing from `D:\veil-toolchain` is reused); (2) follows README sections 3-9 literally: bootstrap, env, `uv sync --locked`, `uv run python -m workshop.hello`, `uv run pytest`, guard `assembleDebug` and `:testfeed:assembleDebug`, `flutter test`, `flutter build apk --debug`; (3) runs `.\tools\bench_check.ps1 --skip-phone --skip-cloud` and expects exit 2 with no FAIL; (4) records every command, its exit code and the end of its output, plus every unclear or missing README step. The orchestrator then deletes `D:\veil-cleanroom-1.1` to free about 10 GB. The phone part is covered by AC-1.1-02 / PT-1.1 | Someone who did not write the README sets up all three parts on a machine that has never built the project | `evidence/1.1-AC01-cleanroom.md` (the record notes it ran on the same laptop; see W-1) |
| AC-1.1-02 | AUTO + PHONE | AUTO: `WE uv run --locked pytest -q` (all tests) → 0 failed. PHONE (after HC-002, the Human sitting's first install done): `tools\bench_check.ps1 --only adb,guard-app,console-app --out data\evidence\1.1\ac02` → 3 PASS; copy `guard.png` and `console.png` | Python tests run; Android and Flutter hello apps launch on the iQOO | `evidence/1.1-AC02.txt`, `evidence/1.1-AC02-guard.png`, `evidence/1.1-AC02-console.png` |
| AC-1.1-03 | AUTO | `WE uv run --locked pytest contracts -q` (0 failed), plus `-k counts -rA` output showing the per-type counts | All 16 types have a schema with ≥ 2 valid and ≥ 1 invalid example | `evidence/1.1-AC03.txt` |
| AC-1.1-04 | AUTO + review | `WE uv run --locked pytest contracts/tests/test_schemas.py -v`. The orchestrator then ticks the 5 lines of "Review checklist (AC-1.1-04)" in `contracts/README.md` against the test names and one opened schema of each kind | Every schema carries `contractVersion`; every fingerprint-bearing type requires `spaceId`; units and coordinate rules are stated in each schema | `evidence/1.1-AC04.txt` |
| AC-1.1-05 | HUMAN | Human sitting step 8: the user reads `contracts/README.md` and approves v1.0 (§14: "All four owners approve" = the user). Requested changes go to a Builder fix round on 1.1.2 before approval | All four owners approve contract v1.0 | the HC answer, copied to `docs/acceptance/1.1.md` (names) |
| AC-1.1-06 | PHONE | 1.1.3 row P1. Then show `getprop-filtered.txt` (`ro.soc.model`, `ro.board.platform`, `ro.build.version.*`, skin keys), `docs/device-profile.md` (chip, Android build, OS skin, RAM, screen), and the decisions entry (CONFIRMED or FLAGGED). The user confirms the OS skin row against About phone (Human sitting step 3) | Chip model string, Android build, OS skin, RAM and screen recorded; a chip other than 8 Elite Gen 5 is flagged in `docs/decisions.md` | `evidence/getprop-filtered.txt` and the other raw files, `evidence/1.1-AC06.txt` |
| AC-1.1-07 | AUTO (after HC-003) | `WE uv run --locked qai-hub list-devices > evidence\1.1-AC07-list-devices.txt`. PASS if at least one line matches `(?i)8[\s_-]*elite[\s_-]*gen[\s_-]*5|sm8850`, e.g. "Samsung Galaxy S26 (Family)" | `qai-hub list-devices` lists at least one device of the same chip family | `evidence/1.1-AC07-list-devices.txt` |
| AC-1.1-08 | AUTO | `git check-ignore data/x.png` and `git check-ignore -v data/x.png` | `data/` is ignored by git | `evidence/1.1-AC08.txt` (expects `data/x.png`, then `.gitignore:2:/data/*	data/x.png`, exit 0) |

Deliverables check (orchestrator):
- `veil/` has `contracts/`, `workshop/`, `guard/`, `console/`, `data/`, `docs/` and `README.md`;
- 16 `contracts/*.schema.json`, `contracts/examples/`, and `workshop/contracts/models.py`;
- `docs/device-profile.md` (MEASURED after P1) and `docs/decisions.md`;
- working AI Hub (AC-1.1-07, aihub-profile line) and Hugging Face (huggingface line).

---

## 6. Proof test plan · PT-1.1 "Fresh-laptop bring-up"

- **Fixtures needed and who builds them:**
  - hello Guard and hello Console: 1.1.1;
  - Test Feed app v1, `bench_check`, `device_profile`, the AI Hub and HF probes, and the `drive` scroll helper: 1.1.3;
  - contracts and their test suite: 1.1.2.
- **Machine part:**
  - (a) The CLEAN run of AC-1.1-01: a fresh clone and fresh toolchain, following the README only.
  - (b) With the phone connected, unlocked and set to stay awake, and the AI Hub token configured, the orchestrator runs `powershell -NoProfile -ExecutionPolicy Bypass -File tools\bench_check.ps1 --out data\evidence\1.1\pt`. Expected: `RESULT: 13 PASS, 0 FAIL, 0 SKIP` and exit 0.
  - Copy `bench-check.txt`, `bench-check.json`, `testfeed.png` and `guard.png` to `progress/.../evidence/PT-1.1/`.
  - Mapping to PLAN's "It should check":
    - adb + scrcpy → lines `adb`, `scrcpy`;
    - hello Guard shows chip, Android version and RAM matching `docs/device-profile.md` → `guard-app`;
    - hello Console installs and launches → `console-app`;
    - tiny AI Hub profiling job → `aihub-profile`;
    - contract validation green → `contracts`;
    - Test Feed installs and scrolls → `testfeed`.
- **Human part (about 15 min, inside the Human sitting):**
  - connect the phone (HC-002);
  - configure AI Hub (HC-003);
  - run `.\tools\bench_check.ps1` once, watching the phone and tapping "Install" on any vivo USB-install prompt, which is a README step.
  - The orchestrator's later re-run is the verifier's run: unchanged APKs are not reinstalled, so no prompts appear.
  - Optional: a teammate on another laptop does the whole README (see W-1).
- **Pass rule (verbatim):** "Every bench-check line is green, with no fixes made outside what the README says."
- **Evidence (verbatim):** "Bench-check output and a phone screenshot."

---

## 7. Human sitting

One sitting of about **50-60 min**, plus about 10 min of optional steps. Do the steps in order. Every command runs in Windows PowerShell after:

```powershell
cd "D:\iqoo finale\veil"
. .\tools\env.ps1        # if blocked: Set-ExecutionPolicy -Scope Process Bypass, then repeat
```

0. **FYI, about 2 min (new HC).**
   - Agents set up a portable toolchain in `D:\veil-toolchain`. Nothing was installed system-wide, and no PATH or registry changes were made.
   - The bootstrap **accepted the Android SDK licences** on your behalf (`sdkmanager --licenses`). The list is in `D:\veil-toolchain\bootstrap.log` and `D:\veil-toolchain\android-sdk\licenses\`.
   - Answer "OK" or object.
1. **Toolchain check, about 1 min (closes HC-001, now superseded).** Run `.\tools\bootstrap.ps1 -CheckOnly` and expect `BOOTSTRAP OK`. Mark HC-001 [DONE] and paste the last 15 lines.
2. **Connect the phone, about 10 min (HC-002).**
   1. Phone: Settings → About phone → Version / Software version. Tap "Software version" 7 times.
   2. Settings → System / Additional settings → Developer options: turn on **USB debugging**, **Install via USB**, **USB debugging (Security settings)** if shown, and **Stay awake**.
   3. Plug in the data cable. On the phone choose "File transfer" if asked, then accept "Allow USB debugging?" with **Always allow from this computer**.
   4. Run `adb devices` and expect `<serial>	device`.
   5. Keep the phone unlocked and plugged in for the rest of the sitting.
3. **Device profile, about 3 min.**
   1. Run `uv run python -m workshop.bench.device_profile --write --evidence-dir "D:\iqoo finale\progress\ch1-see\phase-1.1-foundations\evidence"`.
   2. Open `docs\device-profile.md`. Compare the **OS skin** row with Settings → About phone (e.g. "OriginOS 6.x"). If it is wrong or "unknown", write the correct value in your answer.
4. **Qualcomm AI Hub, about 10-15 min (HC-003).**
   1. Sign up or sign in at https://aihub.qualcomm.com, then go to Account → Settings → API Token and copy it.
   2. Run `uv run qai-hub configure --api_token <PASTE_TOKEN_HERE>`. Type it in this terminal only; never paste it into chat or a file.
   3. Run `uv run qai-hub list-devices` and check that a "Samsung Galaxy S26 (Family)" row (chipset …8-elite-gen5) is listed. The old "Snapdragon 8 Elite Gen 5 QRD" was retired on 2026-09-28.
   4. Paste the device names (no token) in your answer.
5. **Hugging Face, about 5 min (optional, HC-003 part 2).** Anonymous downloads already work. A read token only helps against rate limits.
   - If you want one: https://huggingface.co → Settings → Access Tokens → new **read** token → `uv run hf auth login`. Otherwise write "skipped".
6. **Run the bench check once, about 10-20 min (the proof test with you watching).**
   1. Run `.\tools\bench_check.ps1`.
   2. Watch the phone and tap **Install** or **Allow** on any USB-install prompt.
   3. Expect `RESULT: 13 PASS, 0 FAIL, 0 SKIP`. The aihub-profile line may wait several minutes in AI Hub's queue.
   4. Paste the RESULT line and any non-PASS lines.
7. **Accessibility on a sideloaded app, about 10 min (new HC; PLAN 1.1.3 Do 6, and it feeds 4.2).**
   1. On the phone, open Settings → Accessibility (on OriginOS it may be Settings → Shortcuts & accessibility → Accessibility) → Installed / Downloaded apps → **"Veil probe (does nothing)"**, and try to switch it on.
   2. If a "Restricted setting" dialog appears: Settings → Apps → **Veil Guard** → ⋮ (top right) → **Allow restricted settings** → confirm. Then go back and switch it on.
   3. Take a phone screenshot at each step (Power + Volume down).
   4. Switch the probe **off** again.
   5. In your answer, write the exact menu path you used, and whether the restricted dialog appeared.
   6. Optional, about 5 min: run `uv run python -m workshop.bench.a11y_probe status`, then `enable`, then `status`, then `disable`, to see whether enabling through adb works on this phone. Paste the output.
8. **Approve contracts v1.0, about 15-20 min (new HC; AC-1.1-05).**
   1. Open `contracts\README.md`. Read the 16-type table, the conventions, "Why ScreenLabel is the 16th type", and the review checklist.
   2. Skim one example per type in `contracts\examples\`.
   3. Answer **"approve v1.0"**, or list the changes you want. Changes are made before approval; after approval, v1.0 is frozen.
9. **Power settings, about 2 min (HC-005).** Set the laptop to never sleep while plugged in. Start Claude Code with a permission mode that lets agents work unattended.
10. **Decide waiver W-1, about 1 min (new HC).** See section 8. Answer [WAIVED] with your reason, or name a teammate and laptop for a real fresh-laptop run (optional HC, about 60-90 min of their time, mostly downloads).

After the sitting, paste the start prompt. The orchestrator then runs the AC-1.1-02, -06 and -07 checks and the proof-test re-run itself.

---

## 8. Proposed waivers

- **W-1 · AC-1.1-01 and PT-1.1's "on a machine that has never built the project" / "A Windows laptop that has never built Veil".**
  - **Why it can't be met as written:** there is only one laptop. ORCHESTRATOR §8 rule 6 allows a CLEAN Checker on a fresh clone to count for the machine part, but the literal threshold says a different machine.
  - **Risk:** user-level state on this laptop could hide a missing README step. Examples are the git identity, `%USERPROFILE%\.android` keys and debug keystore, tiny Flutter/Dart config files in `%APPDATA%`, Windows Defender history and Git for Windows itself.
  - **Mitigation already in the plan:** the CLEAN run uses a different path, a **fresh toolchain** (all downloads repeated, about 4.5 GB) and only the README.
  - **Alternative:** a teammate runs the README on their own Windows laptop. Raise it as an optional HC if a teammate is available. If they do, this waiver is not needed.
  - **Plan to close:** the first time a second Windows machine is available (at the latest before 6.3's demo prep), run AC-1.1-01 on it and attach the log to `docs/acceptance/1.1.md`.
- No other criterion needs a waiver. AC-1.1-02, -06 and -07 are pending human setup (HC-002/003), not unmeetable. AC-1.1-05 maps to the user per ORCHESTRATOR §14.

---

## Amendments

<appended by repairs; earlier text is never rewritten>
