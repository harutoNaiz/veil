# Phone day: run sheet

Follow this top to bottom. Every other file is optional reading. After each step, write the result in the HC item's "Your answer" box in `progress/HUMAN_CHECKS.md` (tag [PASS], [FAIL] or [DONE]), then paste the start prompt from ORCHESTRATOR.md.

All commands run in **Windows PowerShell** with the toolchain loaded (do this in every new window):

```powershell
cd "D:\iqoo finale\veil"
. .\tools\env.ps1        # if blocked: Set-ExecutionPolicy -Scope Process Bypass, then repeat
```

## Summary

| HC | Sitting | Minutes | Needs |
|---|---|---|---|
| HC-001 | 1 | 1 | laptop |
| HC-005 | 1 | 2 | laptop |
| HC-006 | 1 | 2 | laptop |
| HC-010 | 1 | 15 | laptop, read contracts |
| HC-011 | 1 | 1 | decision |
| HC-016 | 1 | 5 | decision |
| HC-002 | 2 | 10 | phone, USB cable |
| HC-007 | 2 | 3 | HC-002 |
| HC-003 | 2 | 12 | AI Hub account |
| HC-004 | 2 | 30 | phone, test accounts |
| HC-008 | 2 | 15 (+ queue wait) | HC-002, HC-003 |
| HC-009 | 2 | 10 | HC-008 |
| HC-026 | 3 | 45 | phone, models pushed, HC-004 |
| HC-018 | 3 | 15 | phone |
| HC-020 | 4 | 40 | phone, HC-026 |
| HC-023 | 4 | 25 | phone, HC-004 |
| HC-024 | 5 | 15 | phone, HC-023 |
| HC-027 | 5 | 40 | phone, laptop reference run |
| HC-025 | 5 | 30 + curation | phone, wired Guard |
| HC-017 | 6 | 5 hands, 60-120 unattended | HC-003 |
| HC-021 | 6 | 20 hands, 240 unattended | phone, HC-004, HC-026 |
| HC-015 | 6 (part 1), 8 (part 2) | 5, 45 | laptop, then HC-014 |
| HC-012 | 7 (collect), 8 (label, split) | 150, 300+ | phone, HC-004, a second person |
| HC-014 | 7 | 150 | phone, HC-004 |
| HC-013 | 9 | 65 | HC-012 |
| HC-019 | 10 | 60-120 | 3 outsiders, wired Guard |
| HC-022 | 11 | about 240 | everything above accepted |

Totals: sittings 1-6 are about 5.5 h of your hands, plus about 4 h unattended (HC-021 battery batch, HC-017 cloud run). Sittings 7-11 are long data and demo work (about 20 h). Each sitting is at most 90 minutes of your hands; stop between sittings freely.

## Step 0: the kit (laptop, unattended)

`kit.ps1` builds every APK; `kit.ps1 -Push` installs the APKs and pushes the models (needs HC-002 done). Start the build now and leave it.

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File tools\phone\kit.ps1
```

Run the `-Push` form in Sitting 2, after the phone is connected. If kit.ps1 is missing, tell Claude.

## Sitting 1 (laptop only, about 26 min)

**HC-001 Toolchain check (1 min).** `.\tools\bootstrap.ps1 -CheckOnly`. PASS: last line is `BOOTSTRAP OK`. Paste the last 15 lines.

**HC-005 Keep the laptop awake (2 min).** Windows power settings: never sleep when plugged in. Keep Claude Code in a permission mode that lets agents work unattended. PASS: you did both.

**HC-006 Licence FYI (2 min).** Optionally look at `D:\veil-toolchain\android-sdk\licenses\`. Answer "OK" or write your objection.

**HC-010 Approve contracts v1.0 (15 min).** Read `contracts\README.md`: the 16-type table, conventions, "Why ScreenLabel is the 16th type", the review checklist. Skim one example per type in `contracts\examples\`. PASS: write "approve v1.0". Changes go before approval.

**HC-011 Waiver W-1 (1 min).** Decide: [WAIVED] with a reason and a plan, or name a teammate laptop for a real fresh run.

**HC-016 Chapter 2 gate decision (5 min).** Choose W1 (recommended: keep PLAN, let the real-recording gate decide after HC-014), W2 or W3. Details are under HC-016 in HUMAN_CHECKS.md. Write the letter.

## Sitting 2 (phone setup, about 80 min)

Order: HC-002, HC-007, HC-003, HC-004, kit push, HC-008, HC-009.

**HC-002 Connect the phone (10 min).**
1. Settings, About phone, tap **Software version** 7 times.
2. Developer options: turn on USB debugging, Install via USB, USB debugging (Security settings) if shown, and Stay awake.
3. Plug in the cable, choose File transfer, accept "Allow USB debugging?" and tick Always allow.
4. Run `adb devices`.

PASS: a line `<serial>` then `device`. Paste it with the serial replaced by `xxx`. Keep the phone unlocked and plugged in.

**HC-007 Device profile (3 min).**

```powershell
uv run python -m workshop.bench.device_profile --write --evidence-dir "D:\iqoo finale\progress\ch1-see\phase-1.1-foundations\evidence"
```

Open `docs\device-profile.md` and compare the OS skin row with Settings, About phone. PASS: it matches. If wrong or "unknown", write the right value.

**HC-003 AI Hub token (12 min).** Sign in at https://aihub.qualcomm.com, Account, Settings, API Token, copy it.

```powershell
uv run qai-hub configure --api_token <PASTE_TOKEN_HERE>
uv run qai-hub list-devices
```

Type the token in this terminal only, never into chat or a file. PASS: a "Samsung Galaxy S26 (Family)" row appears. Optional Hugging Face: `uv run hf auth login`. Paste the device names, not the token.

**HC-004 Test accounts (30 min).** Create test accounts, never personal ones, for Instagram and YouTube, and sign in on the phone. In the test Instagram, follow a mix of cat, dog, fox, spider and general accounts. Install Chrome and WhatsApp (skip WhatsApp without a spare number). Netflix is optional ("skipped" is fine). PASS: list which apps are signed in.

**Kit push (about 10 min, mostly unattended).**

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File tools\phone\kit.ps1 -Push
```

PASS: it ends without an error. Every later sitting needs it.

**HC-008 Bench check (15 min of watching).**

```powershell
.\tools\bench_check.ps1
```

Watch the phone and tap Install or Allow on every USB-install prompt. The aihub-profile line may wait several minutes in AI Hub's queue; that wait is unattended. PASS: `RESULT: 13 PASS, 0 FAIL, 0 SKIP`. Evidence: `docs\bench-check.md`. Paste the RESULT line and any non-PASS lines.

**HC-009 Accessibility on a sideloaded app (10 min).**
1. Settings, Accessibility (OriginOS: Shortcuts & accessibility, Accessibility), Installed apps, **Veil probe (does nothing)**, try to switch it on.
2. If a "Restricted setting" dialog appears: Settings, Apps, **Veil Guard**, top-right menu, **Allow restricted settings**, confirm, go back and switch it on.
3. Screenshot each step (Power + Volume down). Switch the probe off.
4. Optional: `uv run python -m workshop.bench.a11y_probe status`, then `enable`, `status`, `disable`. Paste the output.

PASS: write the exact menu path and whether the restricted dialog appeared.

## Sitting 3 (the live Guard, about 60 min)

Everything after this depends on HC-026 working.

**HC-026 Live Guard and "The cat feed" (45 min).** The kit push already put the models in `/sdcard/Android/media/com.veil.guard/models/`. If any is missing, push by hand:

```powershell
adb push data\forge\nudenet\nudenet-320n.onnx /sdcard/Android/media/com.veil.guard/models/
adb push data\forge\nudenet\nudenet-640m.onnx /sdcard/Android/media/com.veil.guard/models/
foreach ($b in 1,4,16) { adb push "data\forge\siglip2\siglip2-image-b$b.onnx" /sdcard/Android/media/com.veil.guard/models/ }
```

Then follow HC-026 steps 2-8 in HUMAN_CHECKS.md in order: enable ONLY "GuardAccessibilityService", send `--es cmd start`, accept the consent. `files/debug.jsonl` must hold `look` lines, `plan` lines, all six `stage` kinds, and no `warn lane-off`. `--es cmd mode --es value strict|light|off` must change `status.json`. A Test Feed cat post is covered, follows scroll, and clears on app switch and screen off. Then pull `debug.jsonl` and `feedlog.jsonl` into the repo folder and run:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File tools\verify\pt-5.2.ps1 -Debug debug.jsonl -Feed feedlog.jsonl
```

Keep the scrcpy recording. Layer 1: you provide a curated evaluation set yourself; confirm the covers are solid and non-peekable. Instagram test account: watch a cat get covered, scroll, switch apps, check small cats in Explore. Run ReplayActivity on one recorded session: PARITY at least 95%. PASS: each step as written. Evidence: `files/debug.jsonl`, the scrcpy video.

**HC-018 Brain and Teacher on the phone (15 min).**

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File tools\with-env.ps1 --cd guard .\gradlew.bat --no-daemon :app:connectedDebugAndroidTest
```

Then open the Teacher debug screen, type 5 words, note the time per card (target 1 s or less). Restart the phone and check the settings survived. PASS: tests green and cards at or under 1 s.

## Sitting 4 (about 65 min)

**HC-020 Watch the watcher (40 min).**

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File tools\verify\pt-4.1.ps1 -Phone
```

Follow the prompts: accept consent ("Entire screen"), tap "Resume Veil". Fill the lock-behaviour table and the app compatibility table (at least 8 apps) in `docs\reports\ch4-plumbing.md`. Try `adb shell appops set com.veil.guard PROJECT_MEDIA allow` and note whether it skips the dialog. PASS: the script ends `PT 4.1: PASS`. Evidence: `progress\ch4-plumbing\phase-4.1-screen-capture\evidence\`.

**HC-023 Screen signals (25 min).** Phone unlocked and awake. First do "Allow restricted settings", enable "Veil Guard signals", and screenshot each screen for `docs\restricted-settings.md`.

```powershell
adb install -r guard\app\build\outputs\apk\debug\app-debug.apk
powershell -NoProfile -ExecutionPolicy Bypass -File tools\verify\4.2.1.ps1 -Phone
powershell -NoProfile -ExecutionPolicy Bypass -File tools\verify\pt-4.2.ps1
```

Do 20 app switches and check the logged foreground app matches each. Have Instagram, YouTube and Chrome signed in for pt-4.2. Compare Instagram smoothness with the service on and off. PASS: 4.2.1 passes and pt-4.2 shows no FAIL. Evidence: `data\signals\pt-4.2\report.md`.

## Sitting 5 (about 85 min)

**HC-024 Covers and Chapter 4 gate (15 min).** Needs HC-023 done.

```powershell
powershell -NoProfile -File tools\phone\4.3.1-phone.ps1
powershell -NoProfile -File tools\phone\4.3.2-phone.ps1
powershell -NoProfile -File tools\phone\4.3.3-phone.ps1
powershell -NoProfile -ExecutionPolicy Bypass -File tools\verify\pt-4.3.ps1 -Phone
```

Look at covers over Instagram, YouTube, Chrome, the keyboard and the status bar; scroll with a peekable cover under your finger. Read the drift table and self-capture frames, then sign the Chapter 4 gate line in `docs\reports\ch4-plumbing.md`. Evidence: `data\ch4\`. These scripts use the debug overlay service (see Known gaps).

**HC-027 AI in your hand and Chapter 3 gate (40 min).**

```powershell
uv run python -m workshop.forge.phone.laptop_ref
powershell -NoProfile -ExecutionPolicy Bypass -File tools\phone\3.3\pt.ps1 -Record
```

PASS: 50 on-phone screenshots with cosine at least 0.98, a 10-minute soak at 3 looks/s, a reopen with VEIL_READY at or under 5000 ms. Evidence: `data\ch3\phone\<stamp>\`. If QNN load fails, approve the AI Hub context-binary downloads (needs HC-003). Optional NPU run once you have the LiteRT .tflite and dispatch library: `powershell -NoProfile -File tools\phone\3.3\bench.ps1 -Runtime litert-npu`. Hold the phone for the 10 minutes and note comfort and heat. Approve the D-3.3 runtime decision in `docs\decisions.md` and sign the Chapter 3 gate in `docs\reports\ch3-speed.md`.

**HC-025 "Not a cat", network silence, packs (30 min plus curation).**
1. Test Feed with a fox post and a repost below it: long-press the fox, "That's not a cat", scroll away and back. PASS: the repost stays uncovered and a real cat is still covered. Record with scrcpy.
2. Run PCAPdroid during step 1. PASS: 0 requests from Veil.
3. Start the laptop Workshop server (`workshop/api`). From the app, download the Spiders pack and a model update; a tampered pack must be refused and the old pack kept.
4. Needles, gore and spoilers: you curate your own controlled, consented image set (Claude never fetches one). Score image recall and false covers. Packs that fail stay out of the catalogue; today those three plus alcohol are text-only and PENDING-HUMAN.

## Sitting 6 (long runs: about 25 min of hands, about 4 h unattended)

Start these, then leave the phone and laptop alone, plugged in and awake.

**HC-017 Live cloud profiling (5 min hands, 1-2 h unattended).** Needs HC-003.

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File tools\cloud_live.ps1
```

It uploads only model files and harmless test crops. Afterwards review `docs\reports\ch3-profile.md` (off-chip layers, chosen precisions, Balanced total at or under 45 ms), then tell Claude to commit `workshop\forge\manifests\`. The live client is untested, so paste any error.

**HC-021 Real-world performance (20 min hands, 3.5-4 h unattended).**
1. Guard and Test Feed installed, Instagram test account signed in, brightness fixed, phone charged, same Wi-Fi throughout.
2. Latency: `uv run python -m workshop.perf.latency.capture --minutes 5`, then `uv run python -m workshop.perf.latency.parse --debug <dir>\debug.jsonl --feed <dir>\feedlog.jsonl --out <evidence>\latency.json`. PASS: p95 at or under 0.3 s.
3. Smoothness: 30 minutes of Instagram with the Guard on while `uv run python -m workshop.perf.smooth.sample --minutes 30` runs; then `uv run python -m workshop.perf.smooth.section --dir <dir> --out <evidence>\smooth.json`.
4. Heat: warm the phone (Strict mode plus camera); `throttled` appears in the stats, then clears.
5. Kills: `uv run python -m workshop.perf.smooth.kill --times 5`. PASS: 5 of 5 restarts within 5 s.
6. Battery batch, unattended about 3.5 h:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File tools\verify\pt-5.3.ps1
```

Optional `-Brightness 128` (the default). It ends `PT 5.3: PASS`, `FAIL` or `PENDING`. If over budget: `uv run python -m workshop.perf.tune --set balanced.sched.rate=<n> --check`, re-run, then record the Chapter 5 gate in `docs\reports\ch5-guard.md`. Evidence: `progress\ch5-guard\phase-5.3-real-world-performance\evidence\` and `data\ch5\perf\pt.log`.

**HC-015 part 1 (laptop, 5 min).** Open `data\evidence\pt-2.2\timeline.png` and `timeline-slow.png`; check no missed swipe, scene cut or app switch, no looks in the first 30 s except check-ups, nothing piling up in the slow run. Write 3-5 lines. Glance at `docs\reports\ch2-motion.md` "Look budget". Machine rerun if wanted: `powershell -NoProfile -ExecutionPolicy Bypass -File tools\verify\pt-2.2.ps1`. On the phone, check the status bar fits in the top 2 and the nav bar in the bottom 2 of 64 thumbnail rows, else set `ignore_*_rows` in params.json.

## Sittings 7-11 (long data and demo work; split into blocks of 90 min or less)

Do these last.

**Sitting 7a. HC-012 step 1, collect (150 min, two blocks).** Add each account id to `data\screens\sources.txt`. Per surface:

```powershell
uv run python -m workshop.screens.capture --app instagram --surface explore --mode dark --source test-acct-A --count 10
uv run python -m workshop.screens.meta_check --screens data\screens
```

Targets: 100+ cats, 50+ spiders, 150+ clean, 30+ lookalikes (dog, fox, lion, stuffed toy, cat logo, the word "cat"), 20%+ dark, a few landscape. Layer 1 sets are curated only by you. PASS: `meta_check` exits 0.

**Sitting 7b. HC-014 recordings (150 min, two blocks).** Record at least 6 sessions, 10 min total, covering slow scroll, fling, Reels swipe, Explore grid, YouTube cat video with a scene cut, app switch, lock/unlock, pauses, a news site (test accounts only):

```powershell
uv run python -m workshop.recordings.record --name <n> --seconds <s> --situations ...
uv run python -m workshop.recordings.index data\recordings
uv run python -m workshop.recordings.sync_check data\recordings\<session>.session.json
```

PASS: index shows AC-2.1-01 PASS, sync_check says SYNC PASS on every session.

**Sitting 8. Label and freeze (HC-012 steps 2-5, HC-014 labels, HC-015 part 2).** Follow HC-012 and HC-014 in HUMAN_CHECKS.md exactly: `powershell -File tools\label-studio.ps1`, convert exports, `workshop.labels.check` (LABELS OK), `workshop.eval.counts --require`, a second person blind-labels 20% and `agree compare` passes. Then:

```powershell
uv run python -m workshop.eval.split --labels data\labels\screens.json --screens data\screens --seed 12 --out data\labels\splits.json
uv run python -m workshop.eval.freeze write --screens data\screens --labels data\labels\screens.json --splits data\labels\splits.json --doc docs\datasets.md
```

Then HC-014 labelling, `recordings.py agree A B` at 5% or less, `split-freeze`, `check-frozen`. HC-015 part 2 (45 min): `uv run python -m workshop.twin.budget eval --sessions data\recordings --labels data\labels\recordings --split dev --out data\ch2\look-budget`, plus a fresh 3-minute phone recording for PT-2.2. Do the long labelling in several blocks.

**Sitting 9. HC-013 Chapter 1 gate (65 min, needs HC-012).**

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File tools\ch1_see.ps1 -Set real -Test
powershell -NoProfile -ExecutionPolicy Bypass -File tools\ch1_see.ps1 -Fresh <folder>
```

The first uses 1 of the 3 allowed test runs: paste the Balanced cats/spiders recall and clean false-cover lines. For the second, take 30 new screenshots (10 cats, 5 spiders, 15 neither), pull them to the folder, and have someone who did not build it fill the gallery tally; repeat with an unseen word such as "bicycles". Open `data\ch1\gallery\public-dev-balanced\index.html` and note repeated wrong covers. FYI: YOLOE is AGPL-3.0 and its MobileCLIP2-B text encoder is research-only; fine for the demo.

**Sitting 10. HC-019 First-time users (60-120 min).** Three people who have never seen Veil each install it and are told only "make it hide cats". Note every hesitation; do not help. Then TalkBack on and 200% text: every control labelled, nothing clipped. Run together with HC-022 step 11.

**Sitting 11. HC-022 Ship the demo (about half a day, several blocks).** Follow HC-022 in HUMAN_CHECKS.md: prepare the phone per `docs\demo\phone-prep.md`; fill `docs\release\edge-cases.md`; fill `data\final\phone-metrics.json` (template `workshop\final\phone-metrics.template.json`), then:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File tools\final_report.ps1
powershell -NoProfile -ExecutionPolicy Bypass -File tools\verify\6.3.3.ps1
```

PASS: 6.3.3 passes. Then slides from `docs\demo\pitch-outline.md` (keep every [F-NN] tag), a scrcpy backup video, 3 rehearsals logged in `docs\demo\rehearsal-log.md` (airplane-mode step, one verifier each), a 30-minute outsider session checked with `workshop\harden\session_check.py` on the logcat (0 crashes, 0 stuck covers), the backup video playing offline with Wi-Fi off, and the licence answers in `docs\demo\qa-sheet.md` checked against PLAN Appendix C.

## Known gaps

- Production Guard overlay hooks are wired only in 5.2-W; HC-024 scripts use the debug overlay service. If a step needs overlays and they are missing, say so rather than marking FAIL.
- The live cloud client (HC-017) is untested; a small first-run error is possible.
- Layer 1 image sets are curated by you; nothing here fetches them.

## When something fails

Tell Claude: "HC-0xx failed, logs in <path>". Keep, for any phone step:

| What | How to get it |
|---|---|
| Guard debug log | `adb pull /sdcard/Android/media/com.veil.guard/files/debug.jsonl .\data\fail\debug.jsonl` (if not found, `adb shell run-as com.veil.guard ls files`) |
| Test Feed log | pull `feedlog.jsonl` from the Test Feed app's files folder to `data\fail\` |
| Logcat | `adb logcat -d > data\fail\logcat.txt` (right after the failure, before reopening apps) |
| Guard status | `status.json` next to `debug.jsonl` |
| Screen | scrcpy recording or a phone screenshot of the failing screen |
| Script output | copy the whole PowerShell window text; pt-5.3 also writes `data\ch5\perf\pt.log` |
| Evidence folders | `data\ch3\phone\<stamp>\`, `data\ch4\`, `data\signals\pt-4.2\`, `data\ch5\perf\`, `progress\ch*\phase-*\evidence\` |

Do not delete these folders before telling Claude. Never paste the AI Hub token.
