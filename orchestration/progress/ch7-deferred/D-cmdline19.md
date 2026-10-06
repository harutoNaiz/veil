MODEL: claude-sonnet-5-5
Files: veil/tools/toolchain.json (pin 19.0), veil/tools/bootstrap.ps1 (steps 4-5), veil/tools/verify/D-cmdline19.ps1 (new).
bootstrap: --licenses run via cmd /c with < NUL; if licenses\android-sdk-license missing, writes "\n24333f8a..." and logs it; --install via cmd /c with < NUL. Old cmd-pipe fallback and 23.0 comment removed.
Version detect: existing .veil-pin marker (version+sha1) already forces reinstall of 23.0 -> 19.0 (Install-Archive wipes dir). Unchanged. --list_installed regex already accepts ; and /.
Deviation: verify passes --sdk_root=D:\veil-toolchain\_trial-cmdline19 since trial dir is not under a "latest" path.
Verify: VERIFY D-cmdline19: PASS. bootstrap.ps1 not run. Not committed.

## Independent verification (orchestrator)
- 23:36: `tools/verify/D-cmdline19.ps1` re-run → VERIFY D-cmdline19: PASS (evidence/D-cmdline19-verify.txt). Commit 1928230.
