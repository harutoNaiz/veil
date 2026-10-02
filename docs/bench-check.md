# Bench check

`tools\bench_check.ps1` is the Phase 1.1 proof test in one command. It checks that the laptop, the phone and
the cloud accounts are ready for the rest of the project, and prints one line per check.

```powershell
cd "D:\iqoo finale\veil"
.\tools\bench_check.ps1                      # everything; needs the phone and the AI Hub token
.\tools\bench_check.ps1 --build never        # do not build; use the APKs that already exist
.\tools\bench_check.ps1 --skip-phone --skip-cloud   # laptop only
```

From Git Bash: `tools/bench_check.sh [options]`. Both scripts load the toolchain (`tools/env.ps1` or
`tools/env.sh`) and then run `python -m workshop.bench.bench_check` in the locked Python environment.

## What the 13 lines prove

The lines run one after the other, in this order. The last column says which of PT-1.1's "It should check"
bullets the line covers.

| Line | What it does | Passes when | Skipped when | PT-1.1 bullet |
| --- | --- | --- | --- | --- |
| `toolchain` | runs `tools\bootstrap.ps1 -CheckOnly` | it prints `BOOTSTRAP OK` (exit 0) | never | (setup) |
| `python-tests` | `pytest -q workshop` | exit 0 | never | (setup) |
| `contracts` | `pytest -q contracts` | exit 0 | never | contract validation is green |
| `build-guard` | builds the Guard and the Test Feed with Gradle, if the APKs are missing | both debug APKs exist | never | (setup) |
| `build-console` | `flutter build apk --debug`, if the APK is missing | the Console debug APK exists | never | (setup) |
| `adb` | looks for exactly one phone in state `device` | one phone is ready (shown as the first 8 hex digits of its serial's hash) | `--skip-phone`, or no phone | adb works |
| `scrcpy` | records 5 s of the phone screen with scrcpy, then measures it with ffprobe | the video is at least 3.0 s long | the `adb` line did not pass | scrcpy works |
| `guard-app` | installs the Guard (only if it changed), starts it, reads the `VEIL_HELLO` log line, takes `guard.png`, compares with `docs/device-profile.md` | chip, Android release and API level match, RAM within 1 % | the `adb` line did not pass | hello Guard shows chip, Android version and RAM matching the device profile |
| `console-app` | installs the Console (only if it changed), starts it, waits for it to be the top activity, takes `console.png` | `com.veil.console` is in the foreground | the `adb` line did not pass | hello Console installs and launches |
| `testfeed` | installs the Test Feed, starts it, scrolls it 3 times, takes `testfeed.png`, reads the app's own log (`feedlog.jsonl`) | at least 10 frames logged, scrolled at least 80 % of the screen height, and the top item changed | the `adb` line did not pass | Test Feed installs and scrolls |
| `aihub-devices` | lists AI Hub devices of the 8 Elite Gen 5 family | at least one is listed | `--skip-cloud`, or AI Hub not configured | AI Hub account works |
| `aihub-profile` | compiles a tiny synthetic model and profiles it on a real device in the cloud | an estimated inference time above 0 | as `aihub-devices`, or it did not pass | tiny AI Hub profiling job |
| `huggingface` | downloads one small file of a public model without a token | the file arrives. The line also says whether a token is configured (optional) | `--skip-cloud` | Hugging Face works |

A line is `PASS`, `FAIL` or `SKIP`. A `SKIP` always says why. An exception inside a line becomes a `FAIL` with
the error text; the check never stops half way.

## Options

| Option | Meaning |
| --- | --- |
| `--out DIR` | where logs, screenshots and the result files go (default `data\evidence\1.1\bench-<date>-<time>\`) |
| `--build if-missing` (default) | build only when an APK is missing |
| `--build always` | rebuild everything (Gradle up to 45 min, Flutter up to 45 min) |
| `--build never` | do not build; a missing APK is a `FAIL` |
| `--skip-phone` | skip the lines that need the phone |
| `--skip-cloud` | skip AI Hub and Hugging Face |
| `--only ID[,ID...]` | run only the listed lines, in the usual order (for example `--only adb,guard-app,console-app`) |
| `--serial S` | choose a phone when more than one is attached |
| `--reinstall` | install the apps even when the same file is already on the phone |

## Output and exit code

- Each line looks like `[PASS] guard-app      installed (unchanged); live soc=SM8850 android=16/API 36 ram=15.6 GiB match docs/device-profile.md`,
  in plain ASCII. The last line is `RESULT: <n> PASS, <n> FAIL, <n> SKIP`.
- Exit code: **0** every line passed, **1** at least one `FAIL`, **2** no `FAIL` but at least one `SKIP`.
  Tonight's expected result without a phone or token is `RESULT: 6 PASS, 0 FAIL, 7 SKIP`, exit 2.
- Files in the output folder: `bench-check.txt` (the lines), `bench-check.json` (the same, with timings),
  `toolchain.txt`, `python-tests.log`, `contracts.log`, `build-guard.log`, `build-console.log`, and, with a
  phone, `scrcpy.mp4`, `guard.png`, `console.png`, `testfeed.png`, `feedlog.jsonl`; with AI Hub,
  `aihub-devices.txt` and `aihub-profile.json`. The default folder is under `data\`, which git ignores.
- The adb serial and the AI Hub or Hugging Face tokens are never printed or saved. Every command has a
  time limit (builds 45 min, tests 10 min, AI Hub 30 min, everything else 3 min); a line that runs out of
  time is a `FAIL` that says `timed out after <n> s`.

## Troubleshooting

- **The phone asks to confirm an install (vivo / iQOO).** Tap **Install** (or **Allow**) on the phone while
  the `guard-app`, `console-app` or `testfeed` line runs. The apps are installed only if they changed, so
  this happens once per new build. Turn on "Install via USB" in Developer options to avoid most prompts.
- **The screen is locked.** The check presses Wake and the menu key, which does not unlock a phone that has a
  PIN. Unlock it and set "Stay awake" in Developer options. A black `guard.png` or a missing `VEIL_HELLO`
  line usually means the screen was off.
- **`adb` says "device unauthorized".** Look at the phone and accept "Allow USB debugging?" (choose "Always
  allow from this computer"). If the prompt does not appear, unplug the cable, run `adb kill-server`, plug it
  in again.
- **`adb` says "choose one with --serial".** Two phones or emulators are attached. Unplug one, or run
  `adb devices` and pass `--serial <serial>`.
- **AI Hub not configured (HC-003).** Run `uv run qai-hub configure --api_token <token>` once in your own
  terminal (get the token at https://aihub.qualcomm.com, Account, Settings, API Token). Never paste the token
  into a chat or a file. Then `uv run qai-hub list-devices` should show a "Samsung Galaxy S26 (Family)" row.
- **`aihub-profile` is slow.** The job waits in AI Hub's queue; allow several minutes (limit 30 min).
- **`guard-app` says `docs/device-profile.md is PENDING`.** Run
  `uv run python -m workshop.bench.device_profile --write --evidence-dir <evidence folder>` with the phone
  connected. It fills in `docs/device-profile.md` and adds the "Target chip check" entry to
  `docs/decisions.md`.
- **`huggingface` fails.** It needs internet. A token is not needed for the models Veil uses.

## Other commands

```powershell
# Show or save the phone's facts (the device profile). Without --write it only prints.
uv run python -m workshop.bench.device_profile
uv run python -m workshop.bench.device_profile --write --evidence-dir <folder>
uv run python -m workshop.bench.device_profile --from-dir <folder with the raw files>   # no phone needed

# Drive the phone from the laptop (add --serial S when several devices are attached)
uv run python -m workshop.bench.drive scroll --times 3
uv run python -m workshop.bench.drive fling
uv run python -m workshop.bench.drive tap 720 1500
uv run python -m workshop.bench.drive home

# Optional, Human sitting only: try the do-nothing accessibility probe over adb.
# This changes a phone setting, so it is never run by the bench check or by a build.
uv run python -m workshop.bench.a11y_probe status
uv run python -m workshop.bench.a11y_probe enable
uv run python -m workshop.bench.a11y_probe disable
```

`device_profile` exits with 0 on success, 3 when no phone is connected, 4 when several are connected and no
`--serial` was given, and 1 on any other error. `a11y_probe enable` remembers the two settings it changes in
`data\evidence\1.1\a11y-before.txt`, and `disable` puts them back exactly.
