#!/usr/bin/env bash
# Mirror the orchestration workspace (files that live OUTSIDE this repo) into veil/orchestration/,
# so a fresh clone holds everything needed to resume. Run before every push.
# Restore on a new machine: see orchestration/README.md.
set -eu
ROOT="/d/iqoo finale"; DEST="$ROOT/veil/orchestration"
MEM="${VEIL_MEMORY_DIR:-/c/Users/Tushar/.claude/projects/D--iqoo-finale/memory}"
mkdir -p "$DEST"
cp "$ROOT/ORCHESTRATOR.md" "$ROOT/PLAN.md" "$ROOT/problem.md" "$DEST/"
rm -rf "$DEST/progress" "$DEST/claude-agents" "$DEST/memory"
cp -r "$ROOT/progress" "$DEST/progress"
cp -r "$ROOT/.claude/agents" "$DEST/claude-agents"
[ -d "$MEM" ] && cp -r "$MEM" "$DEST/memory"
echo "synced orchestration -> $DEST ($(du -sh "$DEST" | cut -f1))"
