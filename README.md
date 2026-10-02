# Veil

Veil is an on-phone guard that watches what appears on screen and covers what the user has asked not to see. This repository holds every part of it. This README gets a new teammate from `git clone` to the three "hello world" targets (laptop, Guard app, Console app) and onward to the phone.

All commands are Windows PowerShell commands, run from the repository root unless a step says otherwise.

## What is in this repository

| Folder | What it holds |
| --- | --- |
| `contracts/` | JSON Schemas shared by every part: the "language" the units speak (added in Phase 1.1.2) |
| `workshop/` | Python: twin, evaluation, model export, bench tools, Flask API |
| `guard/` | Android app in Kotlin: capture, accessibility, overlay, brain, AI runtime. Also the Test Feed app (`guard/testfeed/`) |
| `console/` | Flutter app (the Console) |
| `data/` | Screenshots, recordings, labels, evidence. Private and git-ignored |
| `docs/` | Decisions, device profile, reports, acceptance records |
| `tools/` | Toolchain bootstrap, environment scripts, pre-commit hook scripts, bench check |

Other top-level files: `pyproject.toml` and `uv.lock` (the pinned Python environment), `.pre-commit-config.yaml` (formatting hooks), `.python-version`.

## Before you start

- Windows 10 or 11, 64-bit, with Git for Windows and an internet connection.
- About 15 GB free on a drive where the toolchain folder can be placed on a path **without spaces** (Flutter does not support spaces in its path).
- No admin rights needed. Nothing is installed system-wide: no PATH, registry or environment-variable changes.

## One-command setup

```powershell
powershell -ExecutionPolicy Bypass -File tools\bootstrap.ps1
```

- **Where it installs.** The toolchain goes to the first of these that has no spaces: `-ToolchainDir <path>`, then `$env:VEIL_TOOLCHAIN`, then `<parent of this repo>\toolchain`, then `<drive of this repo>\veil-toolchain` (for example `D:\veil-toolchain`). Example: `powershell -ExecutionPolicy Bypass -File tools\bootstrap.ps1 -ToolchainDir E:\veil-tools`.
- **What it downloads (about 4.5 GB, 30 to 60 minutes the first time).** Python 3.11 via uv, Temurin JDK 17, Gradle 9.3.1, the Android command-line tools with platform-tools, API 36, build-tools 36.0.0 and NDK 28.2.13676358, Flutter 3.47.6 (the largest, 1.9 GB), scrcpy 4.1, ffmpeg 9.0.2 and ktlint 1.8.0. Every archive is checked against a pinned checksum (`tools\toolchain.json`). It then installs the Python environment (`uv sync --locked`) and the git pre-commit hook.
- **Android SDK licences.** The script accepts Google's Android SDK licences on your behalf and logs this in `<toolchain>\bootstrap.log`. Read them first if you need to.
- **Re-running is safe.** Finished components are skipped, and an interrupted download resumes.
- **Just check.** `powershell -ExecutionPolicy Bypass -File tools\bootstrap.ps1 -CheckOnly` installs nothing and prints a table of every tool and version. It ends with `BOOTSTRAP OK` (exit code 0) or `BOOTSTRAP FAILED: ...` (exit code 1).

## Every new terminal

The tools are only on the path of the shell that loads them. In each new PowerShell window:

```powershell
. .\tools\env.ps1
```

In Git Bash:

```bash
source tools/env.sh
```

If PowerShell refuses to run scripts, allow it for this window only: `Set-ExecutionPolicy -Scope Process Bypass`.

To run one command with the tools loaded, without changing your shell:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File tools\with-env.ps1 uv run pytest
powershell -NoProfile -ExecutionPolicy Bypass -File tools\with-env.ps1 --cd guard .\gradlew.bat --no-daemon :app:assembleDebug
```

## Workshop (Python)

```powershell
uv sync --locked
uv run python -m workshop.hello
uv run pytest
```

`workshop.hello` prints the Python version and every pinned package, then `Veil workshop OK`. The heavy machine-learning packages (torch, transformers, ultralytics) are declared but not installed. They arrive in Phase 1.3: `uv sync --locked --group ml`.

## Contracts

The shared types (v1.0) live in `contracts/` and are described in [contracts/README.md](contracts/README.md).

```powershell
uv run pytest contracts
uv run python contracts/scripts/gen_python.py           # regenerate the Python types; add --check to only verify
uv run python -m workshop.contracts.validate <file>     # validate a JSON file against its schema
```

## Guard (Android app)

```powershell
cd guard
.\gradlew.bat --no-daemon :app:assembleDebug
adb install -r app\build\outputs\apk\debug\app-debug.apk
adb shell am start -n com.veil.guard/.MainActivity
```

The hello screen shows the phone's chip, Android version, RAM and screen. The same facts are logged as one `VEIL_HELLO {...}` line (`adb logcat -s VeilHello`).

## Test Feed app

A tiny app with a feed of known blocks, used to test the Guard.

```powershell
cd guard
.\gradlew.bat --no-daemon :testfeed:assembleDebug
adb install -r testfeed\build\outputs\apk\debug\testfeed-debug.apk
adb shell am start -n com.veil.testfeed/.FeedActivity
```

More in [guard/testfeed/README.md](guard/testfeed/README.md).

## Console (Flutter app)

```powershell
cd console
flutter pub get
flutter test
flutter build apk --debug
adb install -r build\app\outputs\flutter-apk\app-debug.apk
adb shell am start -n com.veil.console/.MainActivity
```

## Connect the phone

1. On the phone open Settings, About phone, and tap "Build number" seven times to turn on Developer options.
2. In Developer options turn on **USB debugging**, **Install via USB** and, if it is shown, **USB debugging (Security settings)**. Turn on **Stay awake** (the screen stays on while charging).
3. Connect the USB cable and accept the "Allow USB debugging?" prompt with **Always allow this computer**.
4. Check from a shell that has loaded the env:

   ```powershell
   adb devices
   ```

   The phone must be listed as `device` (not `unauthorized`).
5. vivo and iQOO phones may ask you to confirm every USB install on the phone itself. Tap **Install** when it appears.

## Device profile

```powershell
uv run python -m workshop.bench.device_profile --write
```

Reads the phone's chip, Android version, RAM and screen over adb and writes `docs/device-profile.md`. If the chip is not a Snapdragon 8 Elite Gen 5 family chip, it says so in `docs/decisions.md`.

## Bench check

```powershell
.\tools\bench_check.ps1
```

Checks every tool, the phone and the accounts in one go. Exit code 0 means everything passed, 1 means a failure, 2 means nothing failed but some lines were skipped (for example no phone connected). Details in [docs/bench-check.md](docs/bench-check.md).

## Accounts: Qualcomm AI Hub and Hugging Face

Qualcomm AI Hub is needed from Phase 3.2. Create an account, copy your API token, and type this in your own terminal. Never put the token in a file or a chat:

```powershell
uv run qai-hub configure --api_token <TOKEN>
uv run qai-hub list-devices
```

Hugging Face is optional (the planned models are public). To log in anyway: `uv run hf auth login`.

## Formatting and the pre-commit hook

Before every commit the hook formats Python (ruff), Kotlin in `guard/` (ktlint) and Dart in `console/` (dart format).

```powershell
uv run pre-commit install              # the bootstrap already does this
uv run pre-commit run --all-files
```

Commit from a shell that has loaded the env (`. .\tools\env.ps1` or `source tools/env.sh`): the hook needs the toolchain tools. If a hook changes files, stage them again and commit again.

## Low-memory laptops

The project is tuned for an 8 GB laptop. Run one build at a time (a Gradle build, a Flutter build, the bootstrap or a model job). Always pass `--no-daemon` to Gradle. Every Gradle project caps its heap at 2 GB. If you still see `OutOfMemoryError`, close other programs first.

## Private data

`data/` holds screenshots, recordings and labels from real phones. It is git-ignored and never pushed or uploaded. To check that a path is ignored:

```powershell
git check-ignore -v data/x.png
```

## Troubleshooting

- **`flutter.bat` or another tool is missing after setup.** Antivirus may have quarantined it while unpacking. Add an exclusion for the toolchain folder, delete that component's folder, and run the bootstrap again.
- **"Toolchain path must not contain spaces".** Choose a folder without spaces: `tools\bootstrap.ps1 -ToolchainDir D:\veil-toolchain`, or set `$env:VEIL_TOOLCHAIN`.
- **The phone shows an install prompt and `adb install` hangs.** Unlock the phone and tap **Install** (see "Connect the phone").
- **`OutOfMemoryError` during a build.** Close other programs, and keep to one build at a time (see "Low-memory laptops").
- **`adb devices` says `unauthorized`.** Unplug the cable, run `adb kill-server`, replug, and accept the prompt on the phone with "Always allow".
- **`uv`, `java` or `flutter` is not found.** The shell has not loaded the env: run `. .\tools\env.ps1`.
