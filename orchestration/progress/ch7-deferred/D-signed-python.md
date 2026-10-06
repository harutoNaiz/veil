MODEL: claude-sonnet-5-5
Files: tools/toolchain.json (python -> archive entry, nuget 3.11.9, sha256 9283876d..., dir python-3.11.9, strip 0; top-level "python" key removed), tools/bootstrap.ps1 (step 6 now asserts UV_PYTHON exists; python installed by generic archive loop; -CheckOnly rows expect 3.11.9), tools/env.ps1, tools/env.sh (UV_PYTHON, UV_PYTHON_DOWNLOADS=never, PREFERENCE only-system), .python-version, tools/verify/D-signed-python.ps1.
Deviations: download cached as _downloads\3.11.9 (name from URL tail). uv run --locked recreated .venv (was 3.11.16 -> 3.11.9); export job using old .venv may be affected. Extracted python-3.11.9 into D:\veil-toolchain.
Verify: PASS.

## Independent verification (orchestrator)
- 23:41: `tools/verify/D-signed-python.ps1` re-run → VERIFY D-signed-python: PASS (evidence/D-signed-python-verify.txt). Commit 5543ea9.
Fix rounds: Round 1: added python-3.11.9\tools to PATH in env.ps1/env.sh; repo-venv CheckOnly row now runs .venv\Scripts\python.exe --version (uv --no-sync rejected UV_PYTHON path). verify PASS, CheckOnly BOOTSTRAP OK.

## Independent verification (orchestrator)
- 23:46: `tools/verify/D-signed-python.ps1` re-run → VERIFY D-signed-python: PASS (evidence/D-signed-python-verify.txt). Commit 28110ab.
