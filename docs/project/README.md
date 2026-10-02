# Project planning snapshot

A copy of the planning and orchestration documents, taken when the repository was first published (2026-10-02). The live copies sit next to the repository, in `D:\iqoo finale\` (`PLAN.md`, `ORCHESTRATOR.md`, `progress/`), and change as work goes on. This snapshot is not updated automatically.

- `problem.md`: the original problem statement.
- `PLAN.md`: 6 chapters × 3 phases × 3 sub-phases, with proof tests and acceptance contracts.
- `ORCHESTRATOR.md`: the agent runbook (Opus refines, Sonnet builds, the orchestrator verifies) and the progress tracker.
- `progress/`, for each phase:
  - `SPEC.md`: the exact build spec;
  - one record per sub-phase: what was built and how it was verified;
  - `PHASE.md`: acceptance results;
  - `HUMAN_CHECKS.md`: what is waiting on a human;
  - `DEFERRED.md`: heavy checks deferred to a batch;
  - `LOG.md`: the event log.
