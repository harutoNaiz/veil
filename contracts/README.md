# Veil contracts v1.0

Status: **DRAFT v1.0, awaiting owner approval (AC-1.1-05)**

This folder holds the shapes of the data that every Veil unit exchanges: 16 JSON Schemas (draft 2020-12), examples, the validator and the generated Python types. The JSON Schemas are the authority; everything else is derived from them or checks them. Reading this page and skimming the schemas should take about 15 minutes.

In the commands below, `WE` stands for `powershell -NoProfile -ExecutionPolicy Bypass -File tools\with-env.ps1` and every command runs from the repository root (`veil/`).

## The 16 types

| Type | File | Purpose | Produced by | Consumed by | Fingerprint-bearing |
| --- | --- | --- | --- | --- | --- |
| `Rect` | `rect.schema.json` | An axis-aligned rectangle on the screen | every unit | every unit | no |
| `Frame` | `frame.schema.json` | Metadata of one captured frame (never pixels) | Guard capture, Workshop replay | Gatekeeper, Spotter, Twin | no |
| `UiEvent` | `ui-event.schema.json` | One accessibility signal: scrolled, window changed, content changed, nodes snapshot, screen off, screen on | Guard accessibility service | Gatekeeper, Spotter, Follower | no |
| `Region` | `region.schema.json` | A piece of the screen proposed for describing and judging | Spotter | Describer, Judge, Follower | no |
| `Embedding` | `embedding.schema.json` | A fingerprint of an image piece or a text prompt | Describer, Teacher | Judge, Teacher | **yes** |
| `Concept` | `concept.schema.json` | The user-facing definition of one dislike (the concept card) | Console, topic packs | Teacher, Console | no |
| `ConceptPack` | `concept-pack.schema.json` | A named, versioned set of concepts | Workshop | Console, Teacher | no |
| `CompiledConcept` | `compiled-concept.schema.json` | A concept compiled into fingerprints for one model family | Teacher (Workshop or phone) | Judge | **yes** |
| `Finding` | `finding.schema.json` | The Judge's verdict on one piece, or a Layer 1 detector hit | Judge, Layer 1 detectors | Follower, offline scorer | no |
| `Track` | `track.schema.json` | The Follower's state for one cover across frames and scrolls | Follower | Follower, Painter planning, tests | no |
| `Mask` | `mask.schema.json` | One cover to draw | Follower | Painter | no |
| `MaskPlan` | `mask-plan.schema.json` | The complete set of covers to draw now (at most 24) | Follower | Painter | no |
| `Feedback` | `feedback.schema.json` | A user correction on a Layer 2 cover | Console, cover overlay | Teacher | **yes** |
| `ModelManifest` | `model-manifest.schema.json` | Everything the phone needs to load and use one model file | Workshop export | Guard model loader, Describer, Spotter | describes fingerprint models (carries the space rule, but `spaceId` is optional) |
| `EngineStats` | `engine-stats.schema.json` | Periodic statistics published by the Guard | Guard | Console | no |
| `ScreenLabel` | `screen-label.schema.json` | Ground-truth labels for one screenshot (the Phase 1.2 label format) | Workshop labelling tools | Offline scorer, evaluation | no |

The three fingerprint-bearing types (`Embedding`, `CompiledConcept`, `Feedback`) list `spaceId` in `required`.

## Conventions

Written into every schema's top-level `description`, verbatim:

> Veil contract v1.0. Units: positions and sizes are integer screen pixels with the origin at the top-left of the display in its current orientation (x grows right, y grows down); times are integer milliseconds on one monotonic clock (Android SystemClock.uptimeMillis; replays use a virtual clock in the same unit); fingerprints are L2-normalised vectors stored as float16.

The space rule is appended to `Embedding`, `CompiledConcept`, `Feedback` and `ModelManifest`, verbatim:

> A fingerprint may only be compared with a concept from the same model family: both must carry the same spaceId.

More rules that apply to every schema:

- **`contractVersion`** is `"1.0"` (a `const`) and is required everywhere except `Rect`, where it is optional because a Rect always sits inside a message that carries the version. In `UiEvent` every variant carries it.
- **No `null`.** An optional field is left out; it is never `null`.
- **`additionalProperties: false`** on every object. A typo in a field name is an error, not silently ignored.
- **No inline objects.** Every nested object lives in the file's `$defs` with the title `<FileTitle><Key>` (for example `UiEventNode`).
- **Integers** for all counts, pixels and times. Enum strings are lowerCamelCase (a few names fixed by the plan, such as `RGB`, `NCHW` and `onnxruntime-qnn`, are kept as they are).
- **`Rect` is an object** `{x, y, w, h}`, not an array. It can carry `contractVersion` and gives typed models. `x` and `y` may be negative (an item scrolled partly off-screen); `w` and `h` are at least 1.
- **Scroll direction.** In `UiEvent.Scrolled`, `dx` and `dy` say how far the content moved on screen: `+dy` means it moved down, `-dy` means it moved up (the user scrolled towards later content). This is the opposite sign to Android's scroll delta.
- **Fingerprints** (`Embedding.vectorF16`): standard base64, with padding, of `dim` little-endian IEEE-754 binary16 values, L2-normalised. The byte length `2 x dim` and the unit norm (within 0.01) are checked by `workshop/contracts/rules.py`, because JSON Schema cannot express them.
- **Layer rules** that the schemas enforce: Layer 1 concepts and masks are always `solid`, Layer 1 masks are never `peekable`, `Feedback.layer` is always 2 (Layer 1 cannot be corrected), `userOffset` is capped at plus or minus 0.15, `MaskPlan` holds at most 24 masks and `CompiledConcept.exceptions` at most 64.

### String formats

| Format | Pattern | Used for |
| --- | --- | --- |
| Id | `^[A-Za-z0-9][A-Za-z0-9._:-]{0,63}$` | string ids: `sessionId`, `regionId`, `parentRegionId`, `lastFindingId`, `findingId`, `feedbackId`, `modelId`, `textModelId` |
| Slug | `^[a-z0-9][a-z0-9._-]{0,63}$` | `conceptId`, `packId`, `spaceId` (Layer 1 ids look like `l1.nudity`) |
| Package name | `^[A-Za-z][A-Za-z0-9_]*(\.[A-Za-z0-9_]+)+$` | `packageName`, `foregroundPackage` |
| sha256 | `^[0-9a-f]{64}$` | file and concept hashes |
| Base64 | `^[A-Za-z0-9+/]*={0,2}$`, at least 4 characters | `vectorF16` |
| Times | integer, at least 0 | `tMs` and every other `*Ms` field |

## Why `ScreenLabel` is the 16th type

The plan's step list names 15 types, while its acceptance criteria and deliverables say 16. The 16th is `ScreenLabel`, the screenshot label format, because Phase 1.2's entry condition reads "Phase 1.1 accepted (the label format schema exists)". The other candidates belong to later phases: `Tape` is a named Phase 2.1 deliverable (`contracts/tape.schema.json`) and `LookRequest` is fixed by Phase 2.2's guarantee. This choice is recorded as decision D-003 in `docs/decisions.md` and needs the owner's approval together with the rest of v1.0 (AC-1.1-05).

## The freeze rule

> Contract v1.0 is frozen. Any change needs a version bump, a note to all owners, and a re-run of every test that uses the changed type.

`Tape` (Phase 2.1) and `LookRequest` (Phase 2.2) arrive as additive v1.1 changes: new schema files, with the existing 16 untouched.

## Layout

```
contracts/
  VERSION                        the single line 1.0
  *.schema.json                  the 16 schemas (the authority)
  examples/<type>/valid-NN-*.json     at least 2 valid examples per type
  examples/<type>/invalid-NN-*.json   at least 1 invalid example per type
  examples/invalid-index.json    for each invalid example, the JSON Schema keyword(s) that must reject it
  scripts/gen_python.py          regenerates workshop/contracts/models.py
  scripts/make_vector.py         prints a reproducible random fingerprint, for examples
  tests/                         pytest tests for the schemas, examples, models and rules
workshop/contracts/
  __init__.py                    CONTRACT_VERSION, TYPE_FILES, TYPES, CONVENTIONS, SPACE_RULE
  validate.py                    validator and command line
  rules.py                       cross-field rules (vectors, spaces, concept hash)
  models.py                      GENERATED pydantic v2 models: never edit by hand
```

## How to validate, regenerate and add an example

**Validate everything** (schemas, all examples, models, rules):

```powershell
WE uv run --locked pytest contracts -q
```

**Validate your own files** (the type comes from the folder name under `contracts/examples/`, or from `--type`; `--jsonl` treats each line as one document):

```powershell
WE uv run --locked python -m workshop.contracts.validate contracts\examples\rect\valid-01-basic.json
WE uv run --locked python -m workshop.contracts.validate my-events.jsonl --type UiEvent --jsonl
```

The command prints `OK <Type> <file>` or `INVALID <Type> <file>: <reason>` and exits 0 only if every document is valid. It checks the schema only; the cross-field checks of `rules.py` (`check_rules`) are separate.

**Regenerate the Python models** after any schema change (the test `test_models_up_to_date` fails until you do):

```powershell
WE uv run --locked python contracts\scripts\gen_python.py
WE uv run --locked python contracts\scripts\gen_python.py --check   # exit 1 if models.py is stale
```

**Add an example.** Put one JSON object in `contracts/examples/<type>/`, named `valid-NN-<what>.json` or `invalid-NN-<why>.json`, pretty-printed with a 2-space indent and a trailing newline. For an invalid example, add an entry to `contracts/examples/invalid-index.json` mapping its path (relative to `contracts/examples/`) to the keyword(s) that must reject it, such as `["maximum"]`. A fingerprint for an example comes from `WE uv run --locked python contracts\scripts\make_vector.py --dim 8 --seed 1`.

## Review checklist (AC-1.1-04)

Tick each line after reading the schemas; the test named on the line enforces it, so a green `pytest contracts` already proves it.

- [ ] 1. Every schema carries `contractVersion` (const `"1.0"`; required everywhere except `Rect`). Enforced by `test_contract_version_defined` and `test_contract_version_required_except_rect` in `contracts/tests/test_schemas.py`.
- [ ] 2. Every fingerprint-bearing type (`Embedding`, `CompiledConcept`, `Feedback`) requires `spaceId`. Enforced by `test_fingerprint_types_require_space_id` in `contracts/tests/test_schemas.py`.
- [ ] 3. The spaceId rule is written in those schemas (and in `ModelManifest`). Enforced by `test_space_rule_stated` in `contracts/tests/test_schemas.py`.
- [ ] 4. Units and coordinate rules are stated in every schema. Enforced by `test_conventions_stated` in `contracts/tests/test_schemas.py`.
- [ ] 5. `pytest contracts/` passes: every valid example is accepted and every invalid example is rejected for its indexed reason. Enforced by `test_valid_example`, `test_invalid_example` and `test_invalid_index_complete` in `contracts/tests/test_examples.py`, and by the whole suite.
