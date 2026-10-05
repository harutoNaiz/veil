#!/usr/bin/env bash
# Orchestrator: verify one sub-phase and commit only its owned paths.
# usage: vc.sh <x.y.z> "<name>" "<phase-dir under progress/>" "<record file>" <owned path>...
set -u
ID="$1"; NAME="$2"; PDIR="$3"; REC="$4"; shift 4
ROOT="/d/iqoo finale"; EV="$ROOT/progress/$PDIR/evidence/$ID-verify.txt"
SP_U="${VC_TMP:-$ROOT/veil/.git/vc-tmp}"; mkdir -p "$SP_U"; SP=$(cygpath -w "$SP_U")
cd "$ROOT/veil" || exit 9
mkdir -p "$(dirname "$EV")"
echo "=== $ID verify · $(date '+%Y-%m-%d %H:%M:%S')" > "$EV"
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "tools\\verify\\$ID.ps1" >> "$EV" 2>&1
CODE=$?
echo "exit $CODE" >> "$EV"
tail -4 "$EV"
# boundary: every changed path must be in an owned path of SOME running sub-phase; we report the ones outside this sub-phase's set
echo "--- changed paths NOT owned by $ID (other builders' paths expected):"
git status --short --untracked-files=all | awk '{print $2}' | while read -r f; do
  ok=0; for p in "$@"; do case "$f" in "$p"*) ok=1;; esac; done; [ $ok = 0 ] && echo "  $f"; done | head -20
if [ $CODE -ne 0 ] || ! grep -q "VERIFY $ID: PASS" "$EV"; then echo "RESULT: VERIFY FAILED ($ID)"; exit 1; fi
source tools/env.sh >/dev/null 2>&1
printf '[%s] %s\n\nVerified by orchestrator (tools/verify/%s.ps1 PASS): progress/%s/%s\n\nCo-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>\n' "$ID" "$NAME" "$ID" "$PDIR" "$REC" > "$(cygpath -u "$SP")/msg-$ID.txt"
PATHS=(); for p in "$@"; do case "$p" in data/*) ;; *) [ -e "$p" ] && PATHS+=("$p");; esac; done
LOCK=.git/veil-commit.lock; for i in $(seq 1 60); do mkdir "$LOCK" 2>/dev/null && break; sleep 2; done
trap 'rmdir "$LOCK" 2>/dev/null' EXIT
BEFORE=$(git rev-parse HEAD)
for attempt in 1 2; do
  git add -- "${PATHS[@]}" "tools/verify/$ID.ps1" 2>&1 | grep -v "LF will be replaced"
  git commit -q -F "$SP\msg-$ID.txt" > "$(cygpath -u "$SP")/commit-$ID.log" 2>&1
  [ "$(git rev-parse HEAD)" != "$BEFORE" ] && break
  echo "commit attempt $attempt failed (hook output below); re-staging hook-formatted files"; grep -v "LF will be replaced" "$(cygpath -u "$SP")/commit-$ID.log" | grep -v "Passed\|Skipped" | head -8
done
if [ "$(git rev-parse HEAD)" = "$BEFORE" ]; then echo "RESULT: VERIFY PASS but COMMIT FAILED ($ID)"; exit 2; fi
H=$(git log --format=%h -1)
echo "RESULT: PASS · COMMIT $H"
printf '\n## Independent verification (orchestrator)\n- %s: `tools/verify/%s.ps1` re-run → VERIFY %s: PASS (evidence/%s-verify.txt). Commit %s.\n' "$(date '+%H:%M')" "$ID" "$ID" "$ID" "$H" >> "$ROOT/progress/$PDIR/$REC"
echo "$(date '+%Y-%m-%d %H:%M') | $ID | VERIFY PASS + COMMIT $H | [$ID] $NAME" >> "$ROOT/progress/LOG.md"
rmdir "$LOCK" 2>/dev/null
git -c credential.helper= -c "credential.helper=!gh auth git-credential" push -q origin main && echo "pushed main $H"
