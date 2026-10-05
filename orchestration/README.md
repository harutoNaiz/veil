# Orchestration workspace (mirror)

The orchestrator runs from the folder ABOVE this repo, `D:\iqoo finale\`. That folder holds the runbook, the plan and the progress records. This directory is a mirror of them, so that a fresh clone has everything another agent needs to resume.

It is refreshed by `bash tools/orchestrator/sync.sh` before every push.

| Here | Lives at (live copy) | What it is |
| --- | --- | --- |
| `ORCHESTRATOR.md` | `D:\iqoo finale\ORCHESTRATOR.md` | The runbook. **Section 1 (STATE block) says exactly where work stopped and what to do next.** |
| `PLAN.md` | `D:\iqoo finale\PLAN.md` | The product plan: 6 chapters × 3 phases, with acceptance contracts |
| `problem.md` | `D:\iqoo finale\problem.md` | The original problem statement |
| `progress/` | `D:\iqoo finale\progress\` | Per-phase SPEC.md, sub-phase records, PHASE.md, evidence, LOG.md, HUMAN_CHECKS.md, DEFERRED.md |
| `claude-agents/` | `D:\iqoo finale\.claude\agents\` | Claude Code agent types: veil-builder (Sonnet, medium), veil-planner-medium and veil-planner-high (Opus) |
| `memory/` | `C:\Users\<user>\.claude\projects\D--iqoo-finale\memory\` | The orchestrator's persistent notes |

## Resume on a new machine
1. Clone into the same layout: `git clone https://github.com/harutoNaiz/veil "D:\iqoo finale\veil"`. Many scripts assume `D:\iqoo finale`.
2. Restore the workspace from this mirror:
   ```bash
   cd "/d/iqoo finale"
   cp veil/orchestration/{ORCHESTRATOR.md,PLAN.md,problem.md} .
   cp -r veil/orchestration/progress .
   mkdir -p .claude && cp -r veil/orchestration/claude-agents .claude/agents
   ```
   Copy `memory/` to the Claude Code project memory folder (optional).
3. Rebuild the toolchain at `D:\veil-toolchain` by following the repo README (`tools/` bootstrap scripts).
   - `data/` is git-ignored: models, datasets and exports. Regenerate it with the Chapter 1-3 scripts, such as `workshop/forge`, `fetch.py` and the export scripts.
4. Start Claude Code in `D:\iqoo finale` and type the start prompt from ORCHESTRATOR.md ("Start here"). The orchestrator reads STATE and continues.

## Orchestrator helpers
- `tools/orchestrator/vc.sh <x.y.z> "<name>" "<chN-…/phase-…>" "<record.md>" <owned paths…>` re-runs `tools/verify/<x.y.z>.ps1` and commits only the owned paths. It also appends the verification to the record and to LOG.md.
- `tools/orchestrator/sync.sh` refreshes this mirror.
- `tools/gradle-locked.ps1 <gradle args>` is the ONLY way to run Gradle. It takes the machine-wide mutex `Global\veil-gradle`, which allows one build at a time on the 7.4 GB laptop.
