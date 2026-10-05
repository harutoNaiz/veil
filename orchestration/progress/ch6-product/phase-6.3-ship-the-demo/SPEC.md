# SPEC · Phase 6.3 Ship the demo
MODEL: claude-opus-5-5
Status: READY (tooling and documents now; every phone and person result is PENDING-HUMAN)
Based on: PLAN.md lines 1826-1833 (Chapter 6 intro) and 2038-2141 (6.3.1-6.3.3, proof test, acceptance contract), Appendix C (2172-2180) · ORCHESTRATOR.md section 0 (F1-F12) and 12 · repo read: console/lib/guard (GuardClient, FakeGuard), console/lib/status, workshop/eval, workshop/packs, docs/reports, tools/verify/6.1.3.ps1, 6.2.2.ps1

## 1. Deviations and risks
- D1 **Entry conditions are not met.** 5.2 and 5.3 are not accepted, and 6.1 is WAITING_HUMAN. This phase delivers tooling and documents only. The hardened on-phone build, the rehearsals, the free-use session and the phone numbers are all PENDING-HUMAN or Deferred.
- D2 **No Gradle.** Recovery, revocation and kill-switch are proved against `FakeGuard` with `flutter test`. That is a test run, not a build. Kotlin crash and restart tests (START_STICKY, the Resume notification) are Deferred as D-6.3-guard and need 5.2.
- D3 The blind-app hint ("can't see protected video") is a Guard overlay, so it is Deferred (D-6.3-blind; Kotlin, needs 5.2). The Console only shows the hint string when `BlindSpotDetector` reports one, which is also a later change. The known-issues list records it.
- D4 The 20-minute heat run and the 30-minute free use are Deferred or Human (F6). 6.3.1 ships only the analyser for their logs.
- D5 `docs/reports/final.md` is generated from result files that already exist. Any number without a measured source is printed as `PENDING-HUMAN`, never estimated. Phone metrics come from `data/final/phone-metrics.json`, which a person fills in after the phone runs. The generator re-runs on the final build.
- D6 The pitch deck is a Markdown outline: `docs/demo/pitch-outline.md`, one section per slide. Turning it into slides is Human.
- D7 Never use explicit material. The demo uses only cats, the fox and spiders.

## 2. Shared interfaces (fixed now; the sub-phases never import each other)
- **Claim id:** `F-NN`, two digits. In `final.md` every number row is one Markdown table row: `| F-NN | <claim> | <value> | measured or PENDING-HUMAN | <conditions> | <source path> |`. The column header must be exactly `| id | claim | value | status | conditions | source |`.
- **Pitch citation:** any line in `docs/demo/*.md` that holds a digit followed by `%`, `ms`, `s`, `GB`, `MB`, `fps` or `/s` must also hold `[F-NN]`. Exempt lines: lines starting with `<!-- nocite -->`, and step numbering.
- **Phone metrics input** `data/final/phone-metrics.json` (git-ignored data; 6.3.2 ships a template with all values null):
  `{"build": str|null, "device": str|null, "date": str|null, "conditions": str|null, "timeToCoverMsP95": num|null, "looksPerSecond": num|null, "aiMsPerLookP95": num|null, "memoryMbPeak": num|null, "batteryPctPerHour": {"light": num|null, "balanced": num|null, "strict": num|null}}`
- **Session log input** for 6.3.1: a logcat text dump (`adb logcat -d -b crash,main -v threadtime`). It may also be given an optional cover-event JSONL with one line per event, `{"tMs": int, "id": str, "op": "show"|"hide"|"appSwitch"|"screenOff"}`.

## 3. Sub-phases (one wave: 6.3.1 ∥ 6.3.2 ∥ 6.3.3; no phone; no Gradle)

### 6.3.1 Hardening (FakeGuard + session analyser + checklists)
Goal: prove crash, lock and kill recovery and permission revocation on the host 5 out of 5 times, give the free-use and heat sessions an automatic log check, and write the edge-case checklist and the known-issues list.
Owned: `console/lib/guard/fake_guard.dart`, `console/lib/status/status_screen.dart`, `console/test/hardening/`, `workshop/harden/` (`__init__.py`, `session_check.py`, `tests/`), `docs/release/known-issues.md`, `docs/release/edge-cases.md`, `tools/verify/6.3.1.ps1`.
Steps:
1. Add test hooks to `FakeGuard`, keeping its existing behaviour unchanged:
   - `void simulateCrash()` sets connection to `unavailable` and the capture state to `stopped`, and emits. The next `connect()` restores `connected`, and if the engine was running before the crash it restores `running`.
   - `void simulateLock()` sets the capture state to `awaitingPermission` and revokes `Perm.screenCapture`. `requestPermission(Perm.screenCapture)` followed by `start()` restores `running`.
   - The kill switch is the existing `stop()`, after which the state is `stopped` and `recentCovers` shows no active cover.
2. In `StatusScreen`, when the connection is `unavailable` or the capture state is `awaitingPermission`, show one `FilledButton` with the key `resume-veil` and the label "Resume Veil". It calls `connect()`, then `requestPermission(screenCapture)` if that permission is missing, then `start()`. Revoking any `Perm` must still show its one-tap fix, which already exists.
3. `console/test/hardening/recovery_test.dart` (widget tests) covers:
   - crash then Resume, 5 times in a loop: running each time;
   - lock then Resume, 5 times: running each time;
   - kill, `stop()`, 5 times: stopped each time, and `start()` resumes;
   - revoking each of the 5 Perms shows its fix button.
   The tests print `RECOVERY crash=5/5 lock=5/5 kill=5/5`.
4. `session_check.py --logcat F [--covers J] [--package com.veil] [--out R.json]` reports:
   - crashes: the count of `FATAL EXCEPTION` blocks whose `Process:` matches the package prefix;
   - ANRs: the count of `ANR in <pkg>`;
   - stuck covers: shows not followed by a hide within 2 s after an `appSwitch` or `screenOff` event, or still open at the end of the log.
   It writes `{crashes, anrs, stuckCovers, verdict: "PASS"|"FAIL"}` and exits 1 on FAIL. Its tests use small hand-written fixtures: one clean log, one log with a Veil crash, one log with a crash in another app (ignored), and one with a cover left open after an app switch.
5. `edge-cases.md`: a phone checklist with one row each for rotation, split screen, keyboard open, picture-in-picture, notification shade, app switch mid-scroll, a blind app (Netflix), and the 20-minute heat run (thermal status before and after, through `adb shell dumpsys thermalservice`). Each row has steps, the expected result, and empty Pass/Fail and date columns.
6. `known-issues.md`: start it with D2, D3, the 6.1 APK compile deferral (D-6.1-apk), and "protected video is not seen".
Verify `6.3.1.ps1` (copy the `Check`/`Run` pattern from 6.2.2.ps1):
- `with-env.ps1 --cd console flutter analyze lib/guard lib/status test/hardening`;
- `with-env.ps1 --cd console flutter test test/hardening test/onboarding`, and the output must contain `RECOVERY crash=5/5 lock=5/5 kill=5/5`;
- ruff check and format check on `workshop/harden`;
- `pytest workshop/harden/tests -q`;
- `edge-cases.md` must contain all 8 row names.
It prints `VERIFY 6.3.1: PASS`.
Human needs: none to build. The phone rows go to section 6.

### 6.3.2 Final evaluation (report generator + linter)
Goal: one honest page, `docs/reports/final.md`, generated from the measured results, where every number is labelled and its conditions are stated.
Owned: `workshop/final/` (`__init__.py`, `report.py`, `lint_report.py`, `sources.py`, `tests/`), `data/final/phone-metrics.template.json`, `docs/reports/final.md`, `tools/final_report.ps1`, `tools/verify/6.3.2.ps1`.
Steps:
1. `sources.py` holds one loader per source. Each returns rows `(id, claim, value, status, conditions, source)`. A missing file or a missing key gives `status="PENDING-HUMAN"` and `value="—"`. Sources:
   - Chapter 1: `data/ch1/results-public.json` (cat recall and clean false covers; the conditions say "public sample, not the frozen set"). It also uses `results-synthetic.json` only if labelled as pipeline-check.
   - Chapter 2: `data/ch2/motion-eval/scores.json` (time to cover p95, flicker, wrong covers per minute, % frames analysed, for each mode).
   - Chapter 3: `docs/reports/ch3-profile.md` table values, or their JSON source if the builder finds one.
   - Packs: `workshop/packs/reports/*.json` (recall and false covers for each pack, plus status).
   - Phone: `data/final/phone-metrics.json` (time to cover, looks per second, AI ms per look, memory, battery per mode). A missing file means every row is PENDING-HUMAN.
   Fixed ids: F-01..F-09 for chapters 1-2, F-10..F-19 for chapter 3, F-20..F-29 for packs (sorted by packId), F-30..F-39 for phone.
2. `report.py [--out docs/reports/final.md]` writes:
   - a header with the build (`git rev-parse --short HEAD`) and the date;
   - a "How to read" note: measured means it came from a file, and PENDING-HUMAN means it is not measured yet;
   - one table per area in the section 2 format;
   - a "Limits" section: protected video, the delay before a cover appears, and laptop numbers that are not phone numbers.
   It does not invent or carry forward any number.
3. `lint_report.py F` exits 1 in any of these cases:
   - a row has a numeric value but its status is not `measured`;
   - a `measured` row has empty conditions or a source path that does not exist;
   - an id is duplicated;
   - a number appears outside a table row (the header date and build are exempt).
4. `tools/final_report.ps1` runs the generator and then the linter in one command. This is the rerun for the final build.
5. Tests: fixture source files give a known table; a missing source gives PENDING-HUMAN; the linter catches each of its 4 failure cases; the generated report passes the linter.
Verify `6.3.2.ps1`:
- ruff and pytest on `workshop/final/tests`;
- run `tools/final_report.ps1`;
- `lint_report.py docs/reports/final.md` must exit 0;
- `final.md` must contain `| F-01 |` and the Limits section.
It prints `VERIFY 6.3.2: PASS`.
Human needs: fill in `phone-metrics.json` after the phone runs and rerun `final_report.ps1` (section 6).

### 6.3.3 Demo and pitch (documents + trace checker)
Goal: the demo script, the phone prep list, the pitch outline, the Q&A sheet, the rehearsal log template, and an automatic check that every pitch number points to the report and every licence question is answered.
Owned: `docs/demo/` (`demo-script.md`, `phone-prep.md`, `pitch-outline.md`, `qa-sheet.md`, `rehearsal-log.md`), `workshop/demo/` (`__init__.py`, `trace_claims.py`, `tests/` with a fixture `final.md`), `tools/verify/6.3.3.ps1`.
Steps:
1. `demo-script.md` holds the 7 PLAN steps in order: the feed, "cats" added in the Console, cats vanish while scrolling, Strict mode, the "not a cat" fox correction, the spider pack, and airplane mode. Each step has what to say, what to tap, the expected result, the time in seconds, and a fallback ("cut to the backup video at mm:ss"). It ends with the cut-scope variant: cats plus one pack.
2. `phone-prep.md` is the PLAN 6.3.3 step 2 list:
   - the sideloaded build;
   - the permissions granted;
   - the capture-permission shortcut, if it works on this phone;
   - test accounts only, with known content;
   - fixed brightness and do-not-disturb on;
   - scrcpy recording commands for the rehearsals.
   It never asks for a factory reset, account changes or anything else outside ground rule 8.
3. `pitch-outline.md` has slides for the problem, how it works (the six helpers), the privacy story, the measured numbers, the limits (protected video, a short delay before covering), and what's next. Every number cites `[F-NN]`.
4. `qa-sheet.md` covers battery, privacy, false covers, the Play Store path (the accessibility policy link from Appendix D), and licences. The licences part has one answer each for SigLIP2, YOLOE (Ultralytics), MobileCLIP / MobileCLIP2 weights, NudeNet, and the Toxicity model, with each part's name written exactly as in Appendix C.
5. `rehearsal-log.md`: a table for runs 1-3 with columns for date, verifier, recording path, each step's pass or retry, the airplane step, and clean yes or no. Below it, sections for the free-use notes and for the backup-video-offline check.
6. `trace_claims.py --docs docs/demo --report docs/reports/final.md --appendix-c` checks three things:
   - every line in the docs that has a number carries an `[F-NN]` from section 2, and that id exists in the report;
   - `qa-sheet.md` names all 5 Appendix C parts;
   - `demo-script.md` has 7 numbered steps and mentions airplane mode.
   It exits 1 and lists the offending lines. The tests use a fixture report, a good doc, a doc with an uncited number, a doc citing an unknown id, and a Q&A sheet missing a part.
Verify `6.3.3.ps1`:
- ruff and pytest on `workshop/demo/tests`;
- run `trace_claims.py` against `docs/reports/final.md` if it exists, or else against the fixture, and print which one it used.
It prints `VERIFY 6.3.3: PASS`. The orchestrator runs it again after 6.3.2 lands.
Human needs: turn the outline into slides, record the backup video, and rehearse (section 6).

## 4. Acceptance criteria
| ID | Status now | How it is checked | Pass threshold (PLAN, word for word) |
| --- | --- | --- | --- |
| AC-6.3-01 | HUMAN | Free-use session plus `session_check.py` on the logcat; notes in rehearsal-log.md | A 30-minute session by someone outside the team ends with 0 crashes and 0 stuck covers |
| AC-6.3-02 | AUTO (FakeGuard) + PHONE | recovery_test prints 5/5 for each; phone repeat in edge-cases.md, Guard side D-6.3-guard | Crash, lock and kill recovery each pass 5 out of 5 times |
| AC-6.3-03 | PHONE | edge-cases.md rows filled in | Rotation, split screen, keyboard, picture-in-picture and the notification shade all checked |
| AC-6.3-04 | AUTO + PHONE | lint_report.py on final.md; phone rows PENDING-HUMAN until phone-metrics.json is filled in | Every number in the final report is measured, with its conditions stated |
| AC-6.3-05 | AUTO | trace_claims.py over docs/demo against final.md | Every claim in the pitch points to a line in the final report |
| AC-6.3-06 | HUMAN | rehearsal-log.md, 3 recordings | 3 consecutive clean rehearsals, including the airplane-mode step |
| AC-6.3-07 | HUMAN | Check on the day | The backup video plays offline on the presentation machine |
| AC-6.3-08 | AUTO + HUMAN review | trace_claims.py --appendix-c; a person reads the answers | The Q&A sheet answers every licence question in Appendix C |
| Ch6 gate | HUMAN | First-time user (HC-019) and 3 demo runs | A person who has never seen Veil installs it, grants permissions, adds two dislikes, and sees them covered in Instagram, without help. The full demo runs three times in a row without a failure. |

## 5. Proof test "Dress rehearsal"
**Machine part (now, about 3 min):**
- Run `tools/verify/6.3.1.ps1`, `6.3.2.ps1` and `6.3.3.ps1`, then `6.3.3.ps1` once more against the real `final.md`.
- Evidence goes in `progress/ch6-product/phase-6.3-ship-the-demo/evidence/`: the three verify outputs, `final.md`, and the session_check fixture reports.

**Human part (about 3 hours; needs 5.2/5.3, the final build and the phone):**
1. Prepare the phone with `phone-prep.md` (20 min).
2. Run `edge-cases.md` and the 20-minute heat run (45 min).
3. Fill in `data/final/phone-metrics.json` from the 5.3 runs and run `tools\final_report.ps1`, then `6.3.3.ps1`, which must pass (15 min).
4. Rehearse 3 times in a row with scrcpy recording, each watched by a verifier (A, B, C), and log each run in `rehearsal-log.md` (45 min).
5. Hand the phone over for 30 minutes of free use, then run `adb logcat -d -b crash,main -v threadtime > data/evidence/6.3/freeuse.txt` and `session_check.py --logcat` on it, which must give 0 and 0 (40 min).
6. Repeat the core demo in airplane mode and record it (10 min).
7. Play the backup video offline on the presentation laptop with Wi-Fi off (5 min).

## 6. Human items (ready to paste into HUMAN_CHECKS.md, one item HC-6.3)
```
HC-6.3 Ship the demo (needs 5.2/5.3 accepted + final build on phone)
[ ] Prep phone per veil/docs/demo/phone-prep.md (test accounts only, DND, brightness fixed)
[ ] Edge cases: fill veil/docs/release/edge-cases.md (rotation, split screen, keyboard, PiP, shade, app switch, blind app, 20-min heat)
[ ] Phone recovery: crash / lock / kill each 5/5 on the real Guard (log in edge-cases.md)
[ ] Fill data/final/phone-metrics.json; run tools\final_report.ps1; then tools\verify\6.3.3.ps1 must PASS
[ ] Turn docs/demo/pitch-outline.md into slides; every number keeps its [F-NN]
[ ] Record the backup demo video (scrcpy), save it on the presentation laptop
[ ] 3 consecutive rehearsals incl. airplane step, one verifier each (A, B, C) -> docs/demo/rehearsal-log.md
[ ] 30-min free use by an outsider; run workshop/harden/session_check.py on the logcat -> 0 crashes, 0 stuck covers
[ ] Backup video plays offline on the presentation machine (Wi-Fi off)
[ ] Read docs/demo/qa-sheet.md licence answers against PLAN Appendix C
[ ] Chapter gate: first-time user installs, grants, adds 2 dislikes, sees them covered in Instagram unaided (with HC-019)
```
Deferred (add to `progress/DEFERRED.md`):
- D-6.3-guard: Kotlin crash and restart tests and the Resume notification on the Guard.
- D-6.3-blind: the blind-app hint overlay.
- D-6.3-heat: the 20-minute thermal run.
