MODEL: claude-sonnet-5-5
D-blind-hint: DONE. VERIFY D-blind-hint: PASS (ktlint, unit tests, compileDebugKotlin).
Files: overlay/blind/{BlindHintPolicy,BlindHintHub,BlindHintChip}.kt, res/values/blind_strings.xml, test BlindHintPolicyTest, tools/verify/D-blind-hint.ps1.
Hooks (one line each): AccessibilityScreenSource after BlindSpotDetector.detect -> BlindHintHub.onFrame(isFullBlind); GuardRuntime.start registers foreground (SignalsHub.foregroundPackage) + BlindHintChip listener.
Limit: MediaProjection source has blindRects = emptyList() (no detection), so only the accessibility backup path feeds the hint until that source detects blind frames.
PENDING-HUMAN: on phone, open Netflix playback; after ~2 s chip appears; tap = dismiss for app; switch app = chip hides; other app with black frames shows it again.

## Independent verification (orchestrator)
- 11:38: `tools/verify/D-blind-hint.ps1` re-run → VERIFY D-blind-hint: PASS (evidence/D-blind-hint-verify.txt). Commit 27b5397.
