#!/usr/bin/env bash
# Checkpoint: make sure nothing local can be lost.
#  1. sync.sh mirrors the orchestration workspace (STATE, progress, agents, memory) into orchestration/,
#     and that mirror is committed to main (docs only, never product code).
#  2. Every other uncommitted file (builders' work in progress) is snapshotted onto the remote
#     branch `checkpoint` via a temporary index: main and the working tree are untouched, no hooks run.
#  3. Both are pushed (fast-forward only; gh credential, which has the workflow scope).
# usage: bash tools/orchestrator/checkpoint.sh ["note"]
set -u
ROOT="/d/iqoo finale"; cd "$ROOT/veil" || exit 9
NOTE="${1:-periodic}"; NOW=$(date '+%Y-%m-%d %H:%M')
PUSH=(git -c credential.helper= -c "credential.helper=!gh auth git-credential" push -q origin)
LOCK=.git/veil-commit.lock
if ! mkdir "$LOCK" 2>/dev/null; then echo "checkpoint: another commit is running, skipped"; exit 0; fi
trap 'rmdir "$LOCK" 2>/dev/null' EXIT

bash tools/orchestrator/sync.sh >/dev/null
git add -A orchestration
if ! git diff --cached --quiet -- orchestration; then
  git commit -q --no-verify -m "[checkpoint] Orchestration state $NOW ($NOTE)

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>" -- orchestration
fi

# Snapshot of everything else that is uncommitted, onto refs/heads/checkpoint.
WIP=$(git status --porcelain --untracked-files=all | grep -v ' orchestration/' | wc -l)
if [ "$WIP" -gt 0 ]; then
  export GIT_INDEX_FILE=.git/checkpoint-index
  git read-tree HEAD && git add -A . 2>/dev/null
  TREE=$(git write-tree); unset GIT_INDEX_FILE; rm -f .git/checkpoint-index
  PARENTS=(-p HEAD)
  git fetch -q origin checkpoint 2>/dev/null && PARENTS+=(-p FETCH_HEAD)
  MSG=.git/checkpoint-msg.txt
  { printf '[checkpoint] WIP snapshot %s (%s): %s uncommitted files on top of main %s

'       "$NOW" "$NOTE" "$WIP" "$(git rev-parse --short HEAD)"
    git status --porcelain --untracked-files=all | grep -v ' orchestration/' | head -40; } > "$MSG"
  C=$(git commit-tree "$TREE" "${PARENTS[@]}" -F "$MSG"); rm -f "$MSG"
  "${PUSH[@]}" "$C:refs/heads/checkpoint" && echo "checkpoint: WIP snapshot $(git rev-parse --short "$C") ($WIP files) -> origin/checkpoint"
fi
"${PUSH[@]}" main && echo "checkpoint: main $(git rev-parse --short HEAD) pushed ($NOW)"
echo "- $NOW checkpoint ($NOTE): main $(git rev-parse --short HEAD) pushed; WIP files: $WIP" >> "$ROOT/progress/LOG.md"
