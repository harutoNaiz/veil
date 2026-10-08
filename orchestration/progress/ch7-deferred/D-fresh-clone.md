MODEL: claude-sonnet-5-5

# D-fresh-clone

Wrong:
1. workshop/hello.py split dependencies on "==" only, so "nltk>=3.10.3" became the name "nltk>=3.10.3" and importlib.metadata.version raised PackageNotFoundError.
2. gen_python.py --check compared raw bytes; with core.autocrlf=true models.py is checked out as CRLF while the generator emits LF, so test_models_up_to_date reported STALE.

Changed:
- workshop/hello.py: added `import re`; names now come from a regex match of the leading distribution name (handles ==, >=, <=, ~=, !=, <, >, extras, markers).
- contracts/scripts/gen_python.py: --check compares with "\r\n" -> "\n" normalised on both sides. models.py not touched.
- tools/verify/D-fresh-clone.ps1 (new): ruff check + format --check on both files, workshop.hello (exit 0 + "Veil workshop OK"), gen_python.py --check, pytest contracts -q.

Verify: `VERIFY D-fresh-clone: PASS` (430 contract tests passed).

## Independent verification (orchestrator)
- 15:54: `tools/verify/D-fresh-clone.ps1` re-run → VERIFY D-fresh-clone: PASS (evidence/D-fresh-clone-verify.txt). Commit 75f2e2c.
