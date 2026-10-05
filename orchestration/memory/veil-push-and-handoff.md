---
name: veil-push-and-handoff
description: How to push the Veil repo (gh credential, workflow scope) and the user's rule to keep everything committed+pushed for handoff
metadata:
  type: feedback
---

The user wants EVERYTHING committed and pushed (code + orchestration files + agent definitions + notes), so another agent could resume from a fresh clone if the laptop dies.

**Why:** said on 2026-10-05: "imagine this laptop will be killed, even then other agent should be able to read this repo and pick it from exactly where we left".

**How to apply:**
- Run `bash veil/tools/orchestrator/sync.sh`, which mirrors ORCHESTRATOR.md, PLAN.md, progress/, .claude/agents and memory into veil/orchestration/. Then commit.
- Push with `git -c credential.helper= -c "credential.helper=!gh auth git-credential" push origin main`. The default Windows credential manager token lacks the `workflow` scope; .github/workflows exists.
- Do this after each batch of commits and before any shutdown.
- Related: [[veil-orchestration]].
