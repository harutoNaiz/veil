#!/usr/bin/env bash
# Phase 1.1 proof test in one command (Git Bash). Same as tools/bench_check.ps1; see docs/bench-check.md.
here="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck source=env.sh
source "$here/env.sh"
cd "$here/.." || exit 1
uv run --locked python -m workshop.bench.bench_check "$@"
exit $?
