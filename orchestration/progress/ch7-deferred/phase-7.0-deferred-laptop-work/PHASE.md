# Phase 7.0 Deferred laptop work · BUILT (phone checks pending)
Commits: 45ccc2d (7.0.1), d9d5bd9 (7.0.2), dae06c1 (7.0.3) · Spec: SPEC.md (84 lines)

## Summary
- **7.0.1 Toxicity on the phone (D-5.2W-tox):**
  - tokpack.py writes compact tokenizer packs. The Kotlin GemmaBpe matches the Python token ids exactly on 25 harmless strings each, for both the toxicity tokenizer and SigLIP2's.
  - ToxPrep and OrtToxicity score toxicity as sigmoid(logits[0]).
  - The SigLIP2 tokenizer also unblocks the Teacher on the phone.
- **7.0.2 Guard crash recovery (D-6.3-guard):**
  - Fixes the Android 14+ SecurityException: the service now uses the SPECIAL_USE foreground type when there is no live projection.
  - Adds RecoveryPolicy, a "Resume Veil" notification, and stopSelf on stale sticky restarts.
  - The running flag persists in prefs `veil.capture`.
  - `RECOVERY-GUARD crash=5/5 lock=5/5 kill=5/5` on the JVM.
- **7.0.3 Concept hot-swap (D-5.2W-teacher):** GuardRuntime.swapLanes swaps lanes without rebuilding the pipeline. Model sessions stay cached. ConceptWatcher reloads the concepts folder in about 150 ms. TeacherDebugActivity writes cards there. Toxicity is wired into the live lanes.

## Deviations
- The "concepts" log field `lanes` carries buildCount.

## Still TODO
- D-5.2W-finder: YOLOE's concept list is empty while its text encoder is blocked.
- D-6.3-blind.
- D-6.1-apk.
- D-7.0-auc.

## Human
On the phone, these behaviours fold into HC-026 (live Guard) and HC-018 (toxicity).
