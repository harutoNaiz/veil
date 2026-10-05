---
name: subagent-model-rule
description: Sub-agents must print their model as the first line; kill and restart any on the wrong model
metadata:
  node_type: memory
  type: feedback
  originSessionId: d02cdfe4-2925-41dc-8f31-a2557f5c2be2
  modified: 2026-10-01T20:54:36.093Z
---

Every sub-agent must print `MODEL: <id>` as the first line of its reply; if it is not the intended model (Sonnet 5.5 for builders, Opus 5.5 for the plan refiner), stop it and restart it with the model set explicitly.

**Why:** a hard rule the user set when first allowing sub-agents; they want to control which model does which work and its cost.
**How to apply:** always pass `model` explicitly on Agent calls and check the first line on return. Related: [[veil-orchestration]].
