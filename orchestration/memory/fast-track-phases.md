---
name: fast-track-phases
description: "Hard rule — each Veil phase must take 20-30 min end to end; lean specs, parallel builders, defer heavy checks"
metadata:
  node_type: memory
  type: feedback
  originSessionId: d02cdfe4-2925-41dc-8f31-a2557f5c2be2
  modified: 2026-10-02T12:50:59.831Z
---

Each phase (Opus refine → Sonnet build → verify) must finish in 20-30 minutes wall clock. Specs ≤ 250 lines, builders build the minimum with one verify script each, one fix round max, heavy/slow checks (clean-room installs, soak, battery) go to progress/DEFERRED.md, human/phone checks never block. Pipeline: refine phase N+1 while N builds.

Model/effort rule (user, 2026-10-02 evening): planning only on Opus at medium or high effort (by difficulty), all coding on Sonnet 5.5 at medium effort — project agent types veil-planner-medium / veil-planner-high / veil-builder in D:\iqoo finale\.claude\agents\.

**Why:** Phase 1.1 took ~4 h (1687-line spec, 430 tests, 2 h clean-room run); the user said they can't afford that many tokens and time per phase and a chapter should already be done.
**How to apply:** follow ORCHESTRATOR.md section 0 (FAST TRACK F1-F10); cut scope rather than polish. Related: [[veil-orchestration]].
