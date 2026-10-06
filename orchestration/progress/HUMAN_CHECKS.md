> Recommended order for all phone and human checks: see `veil/docs/PHONE_DAY.md`.

# Waiting on you

The orchestrator adds an item here whenever something needs human hands, eyes, accounts or judgement. For each item:

1. Do it.
2. Change its tag.
3. Write what you saw under **Your answer**.
4. Paste the start prompt from `ORCHESTRATOR.md` again.

Only you change a tag; agents never do.

Tags:

- **[OPEN]**: waiting for you.
- **[DONE]**: an action is finished.
- **[PASS]** or **[FAIL]**: the result of a check.
- **[WAIVED]**: you accept the risk; write the reason, the risk and the plan.

"Blocks" says what each item holds up, so do the ones that block the most first.

---

## Sitting 1 · Phase 1.1 (about 60 min, do in this order)

Overnight, agents built a **portable toolchain** in `D:\veil-toolchain`, so you don't need to install Android Studio, Flutter, adb, scrcpy, ffmpeg or uv yourself. Nothing was installed system-wide, and no PATH or registry changes were made.

Every command below runs in **Windows PowerShell**, after these two lines:

```powershell
cd "D:\iqoo finale\veil"
. .\tools\env.ps1        # if blocked: Set-ExecutionPolicy -Scope Process Bypass, then repeat this line
```

`env.ps1` puts the toolchain on PATH for **that terminal window only**. Run it again in every new window.

### HC-006 · Phase 1.1 · FYI: Android SDK licences were accepted for you  [OPEN]
- **Why a human:** the bootstrap accepted Google's Android SDK licences on your behalf so builds could run overnight. You should know, and you can object.
- **Blocks:** nothing.
- **Time:** about 2 min.
- **Do:** optionally look at `D:\veil-toolchain\android-sdk\licenses\` and `D:\veil-toolchain\bootstrap.log`.
- **How to answer:** [DONE] with "OK", or write your objection.
- **Your answer:**

### HC-001 · Setup · Toolchain check (replaces "install the test bench")  [OPEN]
- **Why a human:** a quick confirmation that the toolchain works in your own terminal.
- **Blocks:** nothing. Agents already verified it, but this is your first touch.
- **Time:** about 1 min.
- **Do:** run `.\tools\bootstrap.ps1 -CheckOnly` and expect `BOOTSTRAP OK` as the last line.
- **How to answer:** [DONE], then paste the last 15 lines.
- **Your answer:**

### HC-002 · Setup · Connect the iQOO to this laptop  [OPEN]
- **Why a human:** physical access and on-phone confirmation.
- **Blocks:** all PHONE checks, starting with AC-1.1-02 and AC-1.1-06 and the proof test PT-1.1. Phase 1.1 can't be accepted without it.
- **Time:** about 10 min.
- **Do:**
  1. Phone: Settings → About phone → Version / Software version. Tap **Software version** 7 times.
  2. Settings → System / Additional settings → Developer options. Turn on:
     - **USB debugging**;
     - **Install via USB**;
     - **USB debugging (Security settings)**, if shown;
     - **Stay awake**.
  3. Plug in a data cable. Choose "File transfer" if the phone asks, then accept "Allow USB debugging?" and tick **Always allow from this computer**.
  4. In the env-loaded PowerShell, run `adb devices`. Expect `<serial>	device`.
  5. Keep the phone unlocked and plugged in for the rest of the sitting.
- **How to answer:** [DONE]. Paste the `adb devices` output with the serial replaced by `xxx`.
- **Your answer:**

### HC-007 · Phase 1.1 · Device profile  [OPEN]
- **Why a human:** reading the OS skin version on the phone.
- **Blocks:** acceptance of 1.1 (AC-1.1-06).
- **Time:** about 3 min (after HC-002).
- **Do:**
  1. Run `uv run python -m workshop.bench.device_profile --write --evidence-dir "D:\iqoo finale\progress\ch1-see\phase-1.1-foundations\evidence"`.
  2. Open `docs\device-profile.md` and compare the **OS skin** row with Settings → About phone (for example "OriginOS 6.x").
- **How to answer:** [PASS] if the row is right. If it is wrong or "unknown", answer [FAIL] and write the correct value.
- **Your answer:**

### HC-003 · Setup · Qualcomm AI Hub token (Hugging Face optional)  [OPEN]
- **Why a human:** accounts and tokens are yours. Agents must never see or store them.
- **Blocks:** acceptance of 1.1 (AC-1.1-07, the aihub-profile bench line), then all of Chapter 3.
- **Time:** about 10-15 min.
- **Do:**
  1. Sign up or sign in at https://aihub.qualcomm.com, then go to Account → Settings → API Token and copy it.
  2. Run `uv run qai-hub configure --api_token <PASTE_TOKEN_HERE>`. Type it in this terminal only; never paste it into chat or a file.
  3. Run `uv run qai-hub list-devices` and check that a **"Samsung Galaxy S26 (Family)"** row is listed. That is the same chip family; the old "8 Elite Gen 5 QRD" was retired on 2026-09-28.
  4. Optional, Hugging Face: anonymous downloads already work. If you want a read token: https://huggingface.co → Settings → Access Tokens → new **read** token → `uv run hf auth login`.
- **How to answer:** [DONE]. Paste the device names from step 3 (no token), and "HF: skipped" or "HF: done".
- **Your answer:**

### HC-008 · Phase 1.1 · Run the bench check once, watching the phone  [OPEN]
- **Why a human:** vivo/OriginOS may ask for an on-phone tap on every USB install. This is the proof test PT-1.1 with you watching.
- **Blocks:** acceptance of 1.1 (PT-1.1, AC-1.1-02).
- **Time:** about 10-20 min (after HC-002 and HC-003).
- **Do:**
  1. Run `.\tools\bench_check.ps1`.
  2. Watch the phone and tap **Install** or **Allow** on any USB-install prompt.
  3. Expect `RESULT: 13 PASS, 0 FAIL, 0 SKIP`. The aihub-profile line may wait several minutes in AI Hub's queue.
- **How to answer:** [PASS] or [FAIL]. Paste the RESULT line and any non-PASS lines.
- **Your answer:**

### HC-009 · Phase 1.1 · Accessibility service on a sideloaded app  [OPEN]
- **Why a human:** Android's "restricted settings" flow can only be done by hand. It feeds Phase 4.2.
- **Blocks:** acceptance of 1.1 (PLAN 1.1.3 Do 6).
- **Time:** about 10 min (after HC-008 has installed the apps).
- **Do:**
  1. On the phone, open Settings → Accessibility (on OriginOS it may be Settings → Shortcuts & accessibility → Accessibility) → Installed / Downloaded apps → **"Veil probe (does nothing)"**, and try to switch it on.
  2. If a "Restricted setting" dialog appears: Settings → Apps → **Veil Guard** → ⋮ (top right) → **Allow restricted settings** → confirm. Then go back and switch it on.
  3. Take a phone screenshot at each step (Power + Volume down).
  4. Switch the probe **off** again.
  5. Optional, about 5 min: run `uv run python -m workshop.bench.a11y_probe status`, then `enable`, then `status`, then `disable`, and paste the output. This tells us whether enabling through adb works on this phone.
- **How to answer:** [DONE]. Write the exact menu path you used and whether the restricted dialog appeared. Screenshots can stay on the phone; the next session pulls them.
- **Your answer:**

### HC-010 · Phase 1.1 · Approve contracts v1.0  [OPEN]
- **Why a human:** PLAN says "all four owners approve contract v1.0", and here that is you (ORCHESTRATOR section 14).
- **Blocks:** acceptance of 1.1 (AC-1.1-05). After approval, v1.0 is frozen.
- **Time:** about 15-20 min.
- **Do:**
  1. Open `D:\iqoo finale\veil\contracts\README.md`. Read:
     - the 16-type table;
     - the conventions;
     - "Why ScreenLabel is the 16th type";
     - the review checklist.
  2. Skim one example per type in `contracts\examples\`.
- **How to answer:** [PASS] with "approve v1.0", or [FAIL] with the changes you want. Changes are made before approval.
- **Your answer:**

### HC-011 · Phase 1.1 · Waiver W-1: "fresh laptop" test on the same laptop  [OPEN]
- **Why a human:** only you can grant a waiver.
- **Blocks:** acceptance of 1.1 (AC-1.1-01 and PT-1.1).
- **Time:** about 1 min to decide.
- **The issue:** PLAN wants the setup tested by someone else on a laptop that has never built Veil. There is one laptop. Instead, a fresh agent follows only the README, in a fresh clone with a fresh toolchain download, on this same laptop.
  - Risk: user-level state on this laptop could hide a missing README step, for example the git identity, adb keys, or small Flutter config files.
  - Details: SPEC section 8.
- **How to answer:** either
  - [WAIVED] with your reason, plus a plan such as "re-run on a teammate's laptop before demo prep"; or
  - name a teammate and laptop for a real fresh-laptop run (about 60-90 min of their time, mostly downloads).
- **Your answer:**

### HC-005 · Setup · Let agents work while you're away  [OPEN]
- **Why a human:** only you can choose Claude Code's permission settings and your laptop's power settings.
- **Blocks:** nothing directly. Last night the session was also cut off by the usage limit at about 05:35 and resumed at 07:00.
- **Time:** about 2 min.
- **Do:**
  1. In Windows power settings, set the laptop to **never sleep when plugged in** while a session runs.
  2. Keep Claude Code in a permission mode that lets agents work unattended.
- **How to answer:** [DONE].
- **Your answer:**

### HC-012 · Phase 1.2 · Real test data: collect, label, review, freeze  [OPEN]
- **Why a human:** the phone, test accounts and labelling judgement. Agents built and proved all the tools (`progress/ch1-see/phase-1.2-test-data/PHASE.md`).
- **Blocks:** acceptance of 1.2. Real Chapter 1 gate numbers in 1.3 (1.3 is built on public sample images meanwhile).
- **Time:** about 8-10 h in total, can be split. Needs HC-002 (phone) and HC-004 (test accounts) first.
- **Do:** (from SPEC section 6; run in an env-loaded PowerShell in `D:\iqoo finale\veil`)
```
HC-1.2 Phase 1.2 real test data (blocked on HC-004 test accounts; est. 8-10 h total, can be split)
[ ] 1. Collect (~2.5 h): phone connected, test accounts logged in. Add each account id to data\screens\sources.txt.
       Per surface: uv run python -m workshop.screens.capture --app instagram --surface explore --mode dark --source test-acct-A --count 10
       Cover Instagram feed/reels/explore/profile/DMs, YouTube home/playing, Chrome news/image search, WhatsApp chat, X or Reddit.
       Targets: >=100 cats, >=50 spiders, >=150 clean, >=30 lookalikes (dog, fox, lion, stuffed toy, cat logo, word "cat"), >=20% dark, a few landscape.
       Then: uv run python -m workshop.screens.meta_check --screens data\screens  -> exit 0
[ ] 2. Label (~5 h): powershell -File tools\label-studio.ps1 (first run downloads Label Studio). In the browser: create project,
       paste workshop\labels\ls_config.xml as labelling config, add local storage path <veil>\data\screens, import tasks from
       uv run python -m workshop.labels.ls_convert to-ls --screens data\screens --url-prefix "/data/local-files/?d=screens/" --out data\labels\ls-tasks.json
       Label every image per docs\labelling-rules.md (tick "clean" on clean ones). Export JSON -> data\labels\ls-export.json, then
       uv run python -m workshop.labels.ls_convert from-ls --export data\labels\ls-export.json --screens data\screens --labeller labeller-a --out data\labels\screens.json
       uv run python -m workshop.labels.check --labels data\labels\screens.json --screens data\screens   -> LABELS OK
       uv run python -m workshop.eval.counts --labels data\labels\screens.json --require                  -> all OK (AC-1.2-01)
[ ] 3. Second person (~1.5 h): agree sample --fraction 0.2 -> blind-label those in a fresh project -> from-ls -> data\labels\blind.json
       agree compare --official data\labels\screens.json --blind data\labels\blind.json -> pass (AC-1.2-03). Fix disagreements, update rules "Changes".
       Second person also spot-checks the counts (PLAN 1.2.1 "Done when").
[ ] 4. Split and freeze (~5 min): uv run python -m workshop.eval.split --labels data\labels\screens.json --screens data\screens --seed 12 --out data\labels\splits.json
       uv run python -m workshop.eval.freeze write --screens data\screens --labels data\labels\screens.json --splits data\labels\splits.json --doc docs\datasets.md
       Commit docs\datasets.md only (never data\). After this the test set never changes.
[ ] 5. Proof test human part: SPEC.md section 5 steps 1-5 (~2 h, verifier is not the main labeller).
```
- **How to answer:** tick the steps as you go; [DONE] when all 5 are done, with the `counts`, `agree compare` and `freeze` outputs pasted.
- **Your answer:**

### HC-013 · Phase 1.3 · Chapter 1 gate and review  [OPEN]
- **Why a human:** the real gate needs your labelled screenshots (HC-012), and the gallery needs a person's eye.
- **Blocks:** acceptance of 1.3 and the Chapter 1 gate. Nothing else: Chapters 2-3 proceed on the chosen models.
- **Time:** about 65 min in total, after HC-012.
- **Do:** (env-loaded PowerShell in `D:\iqoo finale\veil`)
  - [ ] a. **Real gate run** (about 10 min, uses 1 of the 3 allowed test runs): `powershell -NoProfile -ExecutionPolicy Bypass -File tools\ch1_see.ps1 -Set real -Test`. Paste the Balanced cats/spiders recall and clean false-cover lines.
  - [ ] b. **Proof test "Fresh screenshots"** (about 45 min, needs the phone): take 30 new screenshots (10 cats, 5 spiders, 15 neither), pull them to a folder, run `tools\ch1_see.ps1 -Fresh <folder>`. Someone who didn't build it opens the gallery and fills the tally. Repeat with an unseen word (e.g. "bicycles") and no code change.
  - [ ] c. **Gallery review** (about 10 min): open `data\ch1\gallery\public-dev-balanced\index.html` and note repeated wrong covers.
  - [ ] d. **FYI licences:** YOLOE is AGPL-3.0, and its MobileCLIP2-B text encoder is research-only. Fine for the demo; review before any commercial use.
- **How to answer:** tick the boxes; [PASS] or [FAIL] with the numbers and tally pasted.
- **Your answer:**

### HC-014 · Phase 2.1 · Real recordings and labels  [OPEN]
- **Why a human:** the phone, test accounts and labelling judgement. Agents built and proved all the tools on generated sessions (`progress/ch2-motion/phase-2.1-recordings-and-replay/PHASE.md`).
- **Blocks:** acceptance of 2.1, and real-recording numbers in 2.2 and 2.3. Needs HC-002 (phone) and HC-004 (test accounts). AC-2.1-02 also needs the 4.2.1 event logger.
- **Time:** about 2.5 h.
- **Do:** (env-loaded PowerShell in `D:\iqoo finale\veil`)
```
HC-2.1 Recordings and replay (phone + test accounts only, ~2.5 h total)
[ ] Record >= 6 sessions, >= 10 min total: python -m workshop.recordings.record --name <n> --seconds <s> --situations ...
    Cover twice each: slow scroll, fling, Reels swipe, Explore grid, YouTube cat video with a scene cut,
    app switch, lock/unlock; plus pauses and a news site. Test accounts only, nothing explicit.
[ ] python -m workshop.recordings.index data/recordings  -> AC-2.1-01 PASS (AC-2.1-02 waits for the 4.2.1 logger)
[ ] python -m workshop.recordings.sync_check on every session -> SYNC PASS (AC-2.1-03)
[ ] Label every session in Label Studio (tools\label-studio.ps1, config workshop/labels/ls_video_config.xml),
    keyframes every 0.5 s, mark scene cuts, app switches, clean stretches; convert with recordings.py from-ls
[ ] A second person labels one full session; recordings.py agree A B -> <= 5% (AC-2.1-04)
[ ] recordings.py split-freeze, then check-frozen -> OK
[ ] PT-2.1 human part (SPEC section 5, ~20 min)
[ ] Watch one covered.mp4 from the synthetic PT run: covers sit on the shapes, markers on scroll frames
```
- **How to answer:** tick as you go; [DONE] with the index and sync_check outputs pasted.
- **Your answer:**

### HC-015 · Phase 2.2 · Gatekeeper review and real-data look budget  [OPEN]
- **Why a human:** reviewing the look timeline (does it look when it should and rest when it should?), plus real-recording numbers
- **Blocks:** acceptance of 2.2 (real-data AC-2.2-02/05/06 and the PT-2.2 review). Nothing else
- **Time:** about 5 min now; about 45 min after HC-014
- **Do:** (env-loaded PowerShell in `D:\iqoo finale\veil`)
```
HC-2.2 Gatekeeper (laptop now ~5 min; phone later ~45 min)
[ ] Open data/evidence/pt-2.2/timeline.png and timeline-slow.png: no missed swipe / scene cut / app switch,
    no looks in the first 30 s except check-ups, nothing piles up in the slow run. Write 3-5 lines of notes.
[ ] Glance at docs/reports/ch2-motion.md "Look budget": chosen params per mode look sane; note any waiver on AC-2.2-05.
[ ] Phone: on a real screenshot, check the status bar fits in the top 2 and the nav bar in the bottom 2
    of 64 thumbnail rows (about 50 screen px each on 720x1600); else set ignore_*_rows in params.json.
[ ] After HC-2.1 recordings + labels exist: python -m workshop.twin.budget eval --sessions data/recordings
    --labels data/labels/recordings --split dev --out data/ch2/look-budget  -> AC-2.2-02/05/06 on real data
    (then budget tune on the same set if they fail).
[ ] PT-2.2 human part on a fresh 3-minute phone recording (SPEC section 5), reviewer notes saved with the chart.
```
- **How to answer:** tick as you go; [PASS], [FAIL] or [DONE] with notes and pasted outputs.
- **Your answer:**

### HC-016 · Phase 2.3 · DECISION: Chapter 2 gate on generated sessions  [OPEN]
- **Why a human:** only you can grant a waiver or change a plan rule (PLAN acceptance rules 4 and 7).
- **Blocks:** acceptance of 2.3 and the Chapter 2 gate. Nothing else: Chapters 3-4 continue.
- **Time:** about 5 min to decide.
- **What happened:**
  - On the generated test sessions, Balanced mode failed the gate: about 75% coverage, wrong covers at 23 per minute, and some items never covered.
  - An Opus repair found three real bugs, which are fixed:
    - covers were dropped on the first scroll frame;
    - "confirm" looks were starved;
    - covers stayed up after a scene cut.
  - After the fixes, expected: median time to cover 233 ms, coverage about 83%, wrong covers about 8.7 per minute, 0 flicker.
  - **Even with a perfect detector, the gate can't fully pass on these sessions:**
    - a Layer 2 cover needs at least about 233 ms (look, detect, one frame, confirm);
    - many generated items are visible for under 200 ms;
    - the sessions have only 0.34 clean minutes, so a single wrong cover breaks "< 1 per minute".
  - Details: `progress/ch2-motion/phase-2.3-steady-covers/SPEC.md`, "Amendment A1".
- **Pick one** (thresholds are never changed silently):
  - **W1 (recommended):** keep PLAN as written, record the generated-session gate as FAIL with its known floor, and let the **real-recording gate** decide (after HC-014).
  - **W2:** in Balanced, cover on the first high-confidence sighting instead of the second. This changes PLAN 2.3.1 rule 3; it would be re-measured.
  - **W3:** change the scoring definition so a short-lived item scores its uncovered time instead of "never". Also record at least 3 clean minutes for the wrong-cover rate.
- **How to answer:** [DONE] with "W1", "W2" or "W3" (or a combination) and any notes.
- **Your answer:**

### HC-017 · Phase 3.2 · Live cloud-phone profiling  [OPEN]
- **Why a human:** needs your Qualcomm AI Hub token (HC-003).
- **Blocks:** acceptance of 3.2, and real speeds for 3.3 and Chapter 5.
- **Time:** about 5 min of your time, then 1-2 h running in the background.
- **Do:** (env-loaded PowerShell in `D:\iqoo finale\veil`)
  1. HC-003: `uv run qai-hub configure --api_token <token>`. Never write the token into a file.
  2. `powershell -File tools\cloud_live.ps1`. It uploads only the model files and harmless test crops.
  3. Review `docs/reports/ch3-profile.md`: off-chip layers, chosen precisions, Balanced total ≤ 45 ms. Then tell the orchestrator to commit `workshop/forge/manifests/`.
- **Note:** the live client is untested, so the first run may need a small fix. Paste any error here.
- **Your answer:**

### HC-018 · Phase 5.1 · Brain and Teacher on the phone  [OPEN]
- **Why a human:** needs the phone connected (HC-002).
- **Blocks:** acceptance of 5.1.
- **Time:** about 15 min.
- **Do:** (env-loaded PowerShell in `D:\iqoo finale\veil`, phone connected and unlocked)
  1. `powershell -NoProfile -ExecutionPolicy Bypass -File tools\with-env.ps1 --cd guard .\gradlew.bat --no-daemon :app:connectedDebugAndroidTest`. This runs the golden tapes and the Teacher/store tests on the phone.
  2. Open the Teacher debug screen, type 5 words, and note the time per card (target ≤ 1 s).
  3. Restart the phone, then check that the settings are still there.
- **How to answer:** [PASS] or [FAIL], with the test summary and card times.
- **Your answer:**

### HC-019 · Phase 6.1 · First-time users and accessibility  [OPEN]
- **Why a human:** real people and a screen reader.
- **Blocks:** acceptance of 6.1. Needs the real Guard (5.2) and the phone.
- **Time:** about 1-2 h.
- **Do:**
  1. Three people who have never seen Veil each install it and are told only "make it hide cats". Note every hesitation; don't help.
  2. Turn on TalkBack and set 200% text; check that every control is labelled and nothing is clipped.
- **How to answer:** [PASS] or [FAIL] with the observer notes.
- **Your answer:**

### HC-020 · Phase 4.1 · "Watch the watcher" on the phone  [OPEN]
- **Why a human:** the phone, consent taps, lock and unlock, Netflix.
- **Blocks:** acceptance of 4.1 (AC-4.1-01 to -08) and the Chapter 4 gate.
- **Time:** about 30-45 min. Needs HC-002.
- **Do:** (env-loaded PowerShell in `D:\iqoo finale\veil`, phone connected)
  1. Install the debug Guard, then run `powershell -File tools\verify\pt-4.1.ps1 -Phone` and follow its MANUAL prompts (accept consent, tap "Resume Veil").
  2. Fill in the lock-behaviour table and the app compatibility table (≥ 8 apps; Netflix optional) in `docs/reports/ch4-plumbing.md`.
  3. Try the shortcut `adb shell appops set com.veil.guard PROJECT_MEDIA allow` and note whether it skips the dialog.
- **How to answer:** [PASS] or [FAIL] with the checker output.
- **Your answer:**

### HC-021 · Phase 5.3 · Real-world performance on the phone  [OPEN]
- **Why a human:** every number here is measured on the phone. The battery batch takes about 3.5 h of phone time.
- **Blocks:** acceptance of 5.3 and the Chapter 5 gate.
- **Time:** about 4 h unattended plus 20 min hands-on. Needs HC-002, HC-004, and 5.2 built, including the 5.2-W live wiring.
- **Do:** (env-loaded PowerShell in `D:\iqoo finale\veil`)
  1. Prereq: the 5.2-W live wiring must be built. It includes the `kind=stage` debug lines and a `mode` command in CaptureCommandReceiver. Install the Guard and the Test Feed, and sign in to the Instagram test account.
  2. Latency:
     - Run `uv run python -m workshop.perf.latency.capture --minutes 5`.
     - Then run `uv run python -m workshop.perf.latency.parse --debug <dir>\debug.jsonl --feed <dir>\feedlog.jsonl --out <evidence>\latency.json`.
     - Pass: p95 ≤ 0.3 s. If not, note the slowest stage and what fixed it.
  3. Optional: film the screen in slow motion with a second phone, and compare 3 appearances against the report.
  4. Smoothness and memory:
     - Run 30 minutes of Instagram with the Guard on, with `uv run python -m workshop.perf.smooth.sample --minutes 30` running.
     - Compare gfxinfo with the Guard on and off.
     - Then run `uv run python -m workshop.perf.smooth.section --dir <dir> --out <evidence>\smooth.json`.
  5. Heat: warm the phone up (Strict mode plus the camera). Confirm that `throttled` appears in the stats, then clears.
  6. Kills: `uv run python -m workshop.perf.smooth.kill --times 5`. Pass: 5/5 restarts within 5 s.
  7. Battery batch, about 3.5 h:
     - Run `powershell -NoProfile -ExecutionPolicy Bypass -File tools\verify\pt-5.3.ps1`.
     - Keep brightness fixed, start from the same charge, and stay on the same network.
     - Verifier A repeats the A/B comparison independently.
  8. If anything is over budget:
     - Tune the rates with `uv run python -m workshop.perf.tune --set balanced.sched.rate=<n> --check`.
     - Re-run the tapes and measure again.
     - Then record the Chapter 5 gate decision in `docs/reports/ch5-guard.md`.
- **How to answer:** [PASS] or [FAIL] per step, with the evidence paths.
- **Your answer:**

### HC-022 · Phase 6.3 · Ship the demo  [OPEN]
- **Why a human:** the phone, the rehearsals, the outsider test and the slides all need a person.
- **Blocks:** acceptance of 6.3 and the Chapter 6 gate.
- **Time:** about half a day. Needs 5.2 and 5.3 accepted, and the final build on the phone.
- **Do:**
  1. Prepare the phone following `veil/docs/demo/phone-prep.md`: test accounts only, Do Not Disturb on, brightness fixed.
  2. Edge cases: fill in `veil/docs/release/edge-cases.md` (rotation, split screen, keyboard, PiP, notification shade, app switch, blind app, 20-minute heat).
  3. Phone recovery: crash, lock and kill each recover 5/5 times on the real Guard. Log the results in `edge-cases.md`.
  4. Fill in `data/final/phone-metrics.json` (the template is `workshop/final/phone-metrics.template.json`). Run `tools\final_report.ps1`; then `tools\verify\6.3.3.ps1` must PASS.
  5. Turn `docs/demo/pitch-outline.md` into slides. Every number keeps its [F-NN] tag.
  6. Record the backup demo video with scrcpy, and save it on the presentation laptop.
  7. Hold 3 rehearsals in a row, including the airplane-mode step, with one verifier each (A, B, C). Log them in `docs/demo/rehearsal-log.md`.
  8. 30 minutes of free use by an outsider. Run `workshop/harden/session_check.py` on the logcat. Pass: 0 crashes and 0 stuck covers.
  9. Check that the backup video plays offline on the presentation machine with Wi-Fi off.
  10. Check the licence answers in `docs/demo/qa-sheet.md` against PLAN Appendix C.
  11. Chapter 6 gate: a first-time user installs the app, grants the permissions, adds 2 dislikes, and sees both covered in Instagram, unaided (run together with HC-019).
- **How to answer:** [PASS] or [FAIL] per step.
- **Your answer:**

### HC-023 · Phase 4.2 · Screen signals on the phone  [OPEN]
- **Why a human:** restricted-settings consent, app switching, and the smoothness judgement all happen on the phone.
- **Blocks:** acceptance of 4.2 (AC-4.2-01 to -08).
- **Time:** about 25 min. Needs HC-002 and HC-004.
- **Do:** (env-loaded PowerShell in `D:\iqoo finale\veil`, phone connected, unlocked and awake)
  1. Install the Guard debug APK.
  2. Do "Allow restricted settings", then enable "Veil Guard signals". Screenshot each screen for `docs/restricted-settings.md` (AC-08).
  3. Run `tools\verify\4.2.1.ps1 -Phone`. The real log must validate (AC-01).
  4. Do 20 app switches. Check that the logged foreground app matches each one (AC-07).
  5. Run the "Scroll ruler" proof test, `tools\verify\pt-4.2.ps1` (AC-02 to AC-06). Have Instagram, YouTube and Chrome signed in. If the script is missing, follow SPEC §5 by hand.
  6. Compare Instagram smoothness with the service on and off (AC-06, human view).
- **How to answer:** [PASS] or [FAIL] per step.
- **Your answer:**

### HC-024 · Phase 4.3 · Covers on the phone and the Chapter 4 gate  [OPEN]
- **Why a human:** the visual judgement and the gate sign-off.
- **Blocks:** acceptance of 4.3 and the Chapter 4 gate.
- **Time:** about 15 min. Needs HC-002, and the Guard installed with the accessibility service enabled (HC-023).
- **Do:** (env-loaded PowerShell in `D:\iqoo finale\veil`)
  1. Connect the iQOO. Run `tools\phone\4.3.1-phone.ps1`, `4.3.2-phone.ps1`, `4.3.3-phone.ps1`, then `tools\verify\pt-4.3.ps1 -Phone`.
  2. Look at covers over Instagram, YouTube, Chrome, the keyboard and the status bar. Nothing should feel blocked.
  3. Scroll with a peekable cover under your finger. Is the replay delay acceptable?
  4. Read the drift table and the self-capture frames. Sign the Chapter 4 gate line in `docs/reports/ch4-plumbing.md`.
- **Note:** the production Guard does not wire the overlay hooks yet. The scripts use the debug overlay service. Live wiring comes with 5.2-W.
- **How to answer:** [PASS] or [FAIL] per step.
- **Your answer:**

### HC-025 · Phase 6.2 · "Not a cat" on the phone, network silence, packs  [OPEN]
- **Why a human:** the on-phone correction flow, PCAPdroid, and curating a consented image set.
- **Blocks:** acceptance of 6.2.
- **Time:** about 30 min, plus curation time for step 4. Needs HC-002 and 5.2 wired.
- **Do:**
  1. In the Test Feed with a fox post and a repost further down: long-press the fox, then choose "That's not a cat". Scroll away and back.
     - Pass: the repost stays uncovered and a real cat is still covered.
     - Record it with scrcpy.
  2. Run PCAPdroid during step 1. It must show 0 requests from Veil.
  3. Run the laptop Workshop server (`workshop/api`). From the app:
     - download the Spiders pack and a model update;
     - check that a tampered pack is refused and the old pack stays.
  4. For needles, gore and spoilers:
     - Use a controlled, consented image set that you curate yourself. Claude never fetches one.
     - Score image recall and false covers.
     - Packs that fail stay out of the catalogue. Today those three packs, and alcohol, are text-only and PENDING-HUMAN.
- **How to answer:** [PASS] or [FAIL] per step.
- **Your answer:**

### HC-026 · Phase 5.2 + 5.2-W · The live Guard and "The cat feed"  [OPEN]
- **Why a human:** the phone, model files on the device, a curated Layer 1 set, and the visual checks.
- **Blocks:** acceptance of 5.2, and it unblocks HC-020, HC-021, HC-024 and HC-025 on the real Guard.
- **Time:** about 45 min. Needs HC-002 and HC-004.
- **Do:** (env-loaded PowerShell in `D:\iqoo finale\veil`)
  1. Push the models with `adb push`:
     - `data/forge/nudenet/nudenet-320n.onnx`, `nudenet-640m.onnx`, and `data/forge/siglip2/siglip2-image-b{1,4,16}.onnx` go to `/sdcard/Android/media/com.veil.guard/models/`.
     - One compiled cat concept JSON goes to `.../concepts/`. Then send `--es cmd concepts`.
  2. Install the debug Guard and enable ONLY "GuardAccessibilityService" (not the debug overlay service). Send `--es cmd start` and accept the consent.
     - `files/debug.jsonl` must have `look` lines, `plan` lines, all six `stage` kinds, and no `warn lane-off`.
  3. `--es cmd mode --es value strict|light|off` must change `status.json`. `off` must clear the covers and touch windows.
  4. A Test Feed cat post must get covered, the cover must follow a scroll, and it must clear on app switch and on screen off. `perfetto` must show `veil.*` sections.
  5. Run `tools\verify\pt-5.2.ps1` with the phone connected. Keep the scrcpy recording.
  6. Layer 1: provide the controlled evaluation set yourself (agents never fetch it). Confirm the covers are solid and non-peekable.
  7. Instagram test account: watch a cat get covered, then scroll and switch apps. Also check small cats in the Explore grid.
  8. Run ReplayActivity on one recorded session. Pass: `PARITY` ≥ 95 % against the twin.
- **How to answer:** [PASS] or [FAIL] per step.
- **Your answer:**

### HC-027 · Phase 3.3 · "AI in your hand" and the Chapter 3 gate  [OPEN]
- **Why a human:** the phone, a 10-minute hand-held soak, comfort, and the runtime decision.
- **Blocks:** acceptance of 3.3 and the Chapter 3 gate.
- **Time:** about 40 min. Needs HC-002. HC-003 (AI Hub) helps if QNN load fails.
- **Do:** (env-loaded PowerShell in `D:\iqoo finale\veil`)
  1. On the laptop, run `uv run python -m workshop.forge.phone.laptop_ref` (full 50 images) once.
  2. Connect the iQOO with USB debugging and "stay awake" on. Run `tools\phone\3.3\pt.ps1`.
     - It covers: 50 on-phone screenshots, cosine ≥ 0.98 against the laptop, a 10-min soak at 3 looks/s, and a reopen with VEIL_READY ≤ 5000 ms.
     - Evidence goes to `data/ch3/phone/<stamp>/`.
  3. If QNN load fails, approve the AI Hub context-binary downloads.
  4. Supply the LiteRT .tflite and the NPU dispatch lib, then run `tools\phone\3.3\bench.ps1 -Runtime litert-npu`.
  5. Hold the phone for the 10 min and report how comfortable it was (heat).
  6. Approve or change the D-3.3 runtime decision in `docs/decisions.md`. Then sign the Chapter 3 gate in `docs/reports/ch3-speed.md`.
- **How to answer:** [PASS] or [FAIL] per step.
- **Your answer:**

### HC-028 · Phase 7.1 · Review waiver W-7.1-card, plus "buffalo" on the phone  [OPEN]
- **Why a human:** a contract-schema change to review, and a phone timing.
- **Blocks:** acceptance of 7.1 (non-blocking for the build).
- **Waiver:** compiled concept cards gain an optional `auto` field (the self-calibration data) and concept cards an optional `alsoHide` list. contractVersion stays 1.0, and old cards behave exactly as before. The orchestrator approved this on 2026-10-06 so the build could continue. Reply [OK] or say what to change.
- **Phone (after the 7.1 build + kit):** in the Console, type "buffalo". It must be active within ≤ 1 s and show "Also hide?" chips. Buffalo posts get covered; cow and horse posts stay visible unless you tick their chips.
- **Your answer:**

---

## Later (not needed for Phase 1.1)

### HC-004 · Setup · Test accounts on the phone  [OPEN]
- **Why a human:** account creation and sign-in.
- **Blocks:** the start of 1.2 (screenshots), 2.1 (recordings) and 4.1 (app compatibility).
- **Time:** about 30 min.
- **Do:**
  1. Create **test accounts, never personal ones**, for Instagram and YouTube. Sign in on the phone.
  2. In the test Instagram account, follow a mix of cat, dog, fox, spider and general accounts, so feeds contain both test content and lookalikes.
  3. Install and open Chrome and WhatsApp (a spare or test number is fine; skip WhatsApp if you have none).
  4. Netflix is optional, only for the "black screen" check in 4.1. Write "skipped" if you don't have a spare account.
- **How to answer:** [DONE], and list which apps are signed in to test accounts.
- **Your answer:**

---

## Answered

*(The orchestrator moves items here once it has applied your answer.)*
