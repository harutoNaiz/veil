MODEL: claude-sonnet-5-5
Task D-text-dml: DONE
Files: workshop/twin/bank/engine.py (text session now PROVIDERS[self.provider]), tools/verify/D-text-dml.ps1.
No git history (not a repo) and no comment explaining CPU-only text; parity check shows DML safe, so default changed.
Deviation: `uv run --no-sync --with onnxruntime-directml` fails here (uv looks for missing D:\veil-toolchain\_trial-py interpreter).
Workaround: installed onnxruntime-directml 1.24.4 via `uv pip install --target D:\veil-toolchain\cache\ort-dml --no-deps` (not .venv); verify runs .venv python with PYTHONPATH=repo;ort-dml.
Result: cosine min=1.000000 max=1.000000 (n=32); cpu 2.27 texts/s, dml 171.15 texts/s (~75x).
VERIFY D-text-dml: PASS
Note: real bank builds with `uv run --locked --with onnxruntime-directml` (no --no-sync) still work as before.

## Independent verification (orchestrator)
- 01:18: `tools/verify/D-text-dml.ps1` re-run → VERIFY D-text-dml: PASS (evidence/D-text-dml-verify.txt). Commit 16ca97e.
