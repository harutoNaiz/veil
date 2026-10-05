---
name: veil-orchestration
description: Veil build is run by an orchestrator session following ORCHESTRATOR.md; state lives in its YOU ARE HERE block
metadata:
  node_type: memory
  type: project
  originSessionId: d02cdfe4-2925-41dc-8f31-a2557f5c2be2
  modified: 2026-10-01T20:54:33.125Z
---

From 2026-10-02 the user drives the Veil build (PLAN.md: 6 chapters × 3 phases × 3 sub-phases) by pasting one start prompt that makes the session act as orchestrator per `D:\iqoo finale\ORCHESTRATOR.md`. Opus Refiner per phase writes SPEC.md, Sonnet Builders per sub-phase, orchestrator verifies and records in `progress/`; human items go to `progress/HUMAN_CHECKS.md`.

**Why:** the user wants to only invoke one agent until their weekly usage resets Tuesday 2026-10-06; everything else is abstracted.
**How to apply:** when asked to continue the build, read ORCHESTRATOR.md section 1 (state) first; the orchestrator never writes product code. See [[subagent-model-rule]].
