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
