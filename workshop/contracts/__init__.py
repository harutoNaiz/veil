"""Veil shared contracts v1.0: the 16 JSON Schema types, validation helpers and cross-field rules.

The JSON Schemas in ``contracts/*.schema.json`` are the authority. ``models.py`` is generated
from them by ``contracts/scripts/gen_python.py`` and must never be edited by hand.
"""

from __future__ import annotations

import importlib

CONTRACT_VERSION: str = "1.0"

# The 16 shared types, in the order of the contracts README, with their schema files.
TYPE_FILES: dict[str, str] = {
    "Rect": "rect.schema.json",
    "Frame": "frame.schema.json",
    "UiEvent": "ui-event.schema.json",
    "Region": "region.schema.json",
    "Embedding": "embedding.schema.json",
    "Concept": "concept.schema.json",
    "ConceptPack": "concept-pack.schema.json",
    "CompiledConcept": "compiled-concept.schema.json",
    "Finding": "finding.schema.json",
    "Track": "track.schema.json",
    "Mask": "mask.schema.json",
    "MaskPlan": "mask-plan.schema.json",
    "Feedback": "feedback.schema.json",
    "ModelManifest": "model-manifest.schema.json",
    "EngineStats": "engine-stats.schema.json",
    "ScreenLabel": "screen-label.schema.json",
}

TYPES: tuple[str, ...] = tuple(TYPE_FILES)

FINGERPRINT_TYPES: tuple[str, ...] = ("Embedding", "CompiledConcept", "Feedback")

CONVENTIONS: str = (
    "Veil contract v1.0. Units: positions and sizes are integer screen pixels with the origin "
    "at the top-left of the display in its current orientation (x grows right, y grows down); "
    "times are integer milliseconds on one monotonic clock (Android SystemClock.uptimeMillis; "
    "replays use a virtual clock in the same unit); fingerprints are L2-normalised vectors "
    "stored as float16."
)

SPACE_RULE: str = (
    "A fingerprint may only be compared with a concept from the same model family: "
    "both must carry the same spaceId."
)


def example_dir(type_name: str) -> str:
    """Folder name under ``contracts/examples/`` for a type, e.g. ``"ui-event"``."""
    return TYPE_FILES[type_name].removesuffix(".schema.json")


def model_class(type_name: str) -> type:
    """The generated pydantic class for a type (imported lazily)."""
    if type_name not in TYPE_FILES:
        raise KeyError(type_name)
    models = importlib.import_module("workshop.contracts.models")
    return getattr(models, type_name)
