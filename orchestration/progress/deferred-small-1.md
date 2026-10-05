MODEL: claude-sonnet-5-5
Files: veil/tools/verify/pt-4.2.ps1 (new), veil/tools/verify/D-small-1.ps1 (new), veil/workshop/perf/tune.py (MAIN assets check in in_sync/apply), veil/workshop/perf/tests/test_report_tune.py (+test_tune_main_assets_sync).
Result: VERIFY D-small-1: PASS. Note: first adb call starts a daemon that holds the pipe open; the verify hangs once if no adb daemon is running (already running now).

## Independent verification (orchestrator)
- 23:16: `tools/verify/D-small-1.ps1` re-run → VERIFY D-small-1: PASS (evidence/D-small-1-verify.txt). Commit 7266ef6.
