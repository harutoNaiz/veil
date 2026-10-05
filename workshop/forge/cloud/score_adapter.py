"""Score adapter (DV-4): points 0-100 per model; fixture mode reads fixtures/2/scores.json."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np

FIXTURE = Path(__file__).parent / "fixtures" / "2" / "scores.json"


def cosine_points(outputs, reference) -> float:
    """100 x mean cosine similarity between rows of outputs and reference."""
    a = np.asarray(outputs, dtype=np.float64).reshape(len(outputs), -1)
    b = np.asarray(reference, dtype=np.float64).reshape(len(reference), -1)
    num = (a * b).sum(1)
    den = np.linalg.norm(a, axis=1) * np.linalg.norm(b, axis=1)
    return float(100.0 * np.mean(num / np.maximum(den, 1e-12)))


def fixture_scores(path: Path = FIXTURE) -> dict:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def score(model_id: str, outputs, reference, fixture: dict | None = None) -> float:
    """Fixture mode (fixture dict given): recorded float score. Embedders/toxicity: cosine points.

    Detectors live use the ch1 scorer (workshop/eval/score_screens.py) on decoded
    hub outputs; that path runs only with --live.
    """
    if fixture is not None:
        return float(fixture[model_id]["float"])
    if model_id.startswith(("nudenet", "yoloe")):
        raise NotImplementedError("detector scoring runs live via workshop/eval/score_screens.py")
    return cosine_points(outputs, reference)
