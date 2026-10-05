MODEL: claude-sonnet-5-5
Files: veil/tools/phone/kit.ps1, veil/tools/verify/phone-kit-1.ps1
Built via gradle-locked: guard app debug+androidTest, testfeed, smoketest debug+androidTest. All copied to data/phone-kit/apks/ + MANIFEST.txt (sha256, model sizes, concept).
Sizes: guard 130MB, guard-AT 1.0MB, smoketest 92.7MB, smoketest-AT 0.8MB, testfeed 2.7MB.
Models listed: nudenet 320n/640m, siglip2 b1/b4/b16 + siglip2-tok.bin, toxicity seq128 + toxicity-tok.bin, yoloe embed. Concept: contracts/examples/compiled-concept/valid-01-cats-siglip2.json -> concepts/.
Verify: VERIFY phone-kit-1: PASS (parse, dry-run, 6 APKs in manifest, -Push no device -> exit 2).
D-6.1-apk: FAILED. flutter build apk --debug: ':app:compileDebugKotlin' failed (Kotlin BuildToolsApi compilation work), 1m30s, under Global\veil-gradle mutex. Not fixed. console-debug.apk in kit is STALE (Oct 2 prior build copied); kit prints WARN and "flutter ok: False".
Note: do not pipe verify to tail; adb server inherits the pipe and hangs it.

## Independent verification (orchestrator)
- 00:53: `tools/verify/phone-kit-1.ps1` re-run → VERIFY phone-kit-1: PASS (evidence/phone-kit-1-verify.txt). Commit 04351c2.
