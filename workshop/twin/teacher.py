"""Teacher v0: turns one word into a Concept card, and a Concept into a CompiledConcept.

The word becomes five "looks like" phrases, a few lookalike phrases ("but not") and a shared ignore
list. No model learns anything: switching the list is only a re-compile of text fingerprints.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import numpy as np

from workshop.contracts.rules import concept_sha256, encode_f16
from workshop.twin.describer import TextEncoder

LOOKS_LIKE = [
    "a photo of a {c}",
    "a cartoon {c}",
    "a drawing of a {c}",
    "a {c} emoji",
    "a close-up of a {c}",
]
IGNORE = ["a screenshot of an app", "text on a screen", "a user interface"]
LOOKALIKES = {
    "cat": ["a dog", "a fox", "a lion", "a stuffed toy"],
    "spider": ["an ant", "a crab", "a scorpion", "a beetle"],
}  # unknown words get no lookalikes
CALIB_PATH = Path(__file__).resolve().parent / "calibration.json"
THRESH_PATH = Path(__file__).resolve().parent / "thresholds.json"
DEFAULT_MODES = {"light": 0.7, "balanced": 0.5, "strict": 0.3}
DEFAULT_MARGIN = 0.01


def _singular(word: str) -> str:
    """Strip one trailing "s" ("cats" -> "cat"); "grass" and one-letter words stay as they are."""
    return word[:-1] if len(word) > 2 and word.endswith("s") and not word.endswith("ss") else word


def concept_card(word: str) -> dict:
    """Concept v1.0 for a user word. "cats" -> conceptId "cats", {c} = "cat"."""
    text = " ".join(word.split()).strip()
    slug = re.sub(r"[^a-z0-9._-]+", "-", text.lower()).strip("-.")[:64]
    if not slug:
        raise ValueError(f"cannot make a concept from {word!r}")
    singular = _singular(text.lower())
    return {
        "contractVersion": "1.0",
        "conceptId": slug,
        "displayName": text[:1].upper() + text[1:] if text else text,
        "layer": 2,
        "enabled": True,
        "looksLike": [t.format(c=singular) for t in LOOKS_LIKE],
        "butNot": list(LOOKALIKES.get(singular, [])),
        "scope": "object",
        "coverStyle": "solid",
        "showLabel": False,
    }


def _load(source: Path | dict | None) -> dict:
    if source is None:
        return {}
    if isinstance(source, dict):
        return source
    path = Path(source)
    return json.loads(path.read_text(encoding="utf-8")) if path.is_file() else {}


def _embeddings(enc: TextEncoder, phrases: list[str]) -> list[dict]:
    if not phrases:
        return []
    vecs = enc.embed_texts(phrases)
    return [
        {
            "contractVersion": "1.0",
            "spaceId": enc.space_id,
            "modelId": enc.text_model_id,
            "dim": int(vec.shape[0]),
            "vectorF16": encode_f16(vec),
            "kind": "text",
            "text": phrase[:500],
        }
        for phrase, vec in zip(phrases, vecs, strict=True)
    ]


def compile_concept(
    concept: dict,
    enc: TextEncoder,
    calibration: Path | dict | None = CALIB_PATH,
    thresholds: Path | dict | None = THRESH_PATH,
    example_centroid: np.ndarray | None = None,
) -> dict:
    """CompiledConcept v1.0 in the encoder's space; merges calibration and threshold files."""
    cid = concept["conceptId"]
    calib = (_load(calibration).get("concepts") or {}).get(cid) or {}
    thr = _load(thresholds)
    modes = {**DEFAULT_MODES, **(thr.get("modes") or {})}
    butnot = list(concept.get("butNot", [])) + [
        p for p in calib.get("butNotExtra", []) if p not in concept.get("butNot", [])
    ]
    ignore = list(concept.get("ignore") or IGNORE)
    looks = list(concept["looksLike"])
    vecs = _embeddings(enc, looks + butnot + ignore)
    cc = {
        "contractVersion": "1.0",
        "conceptId": cid,
        "spaceId": enc.space_id,
        "textModelId": enc.text_model_id,
        "conceptSha256": concept_sha256(concept),
        "looksLike": vecs[: len(looks)],
        "butNot": vecs[len(looks) : len(looks) + len(butnot)],
        "ignore": vecs[len(looks) + len(butnot) :],
        "exampleCount": 0,
        "exceptions": [],
        "calibrationOffset": float(np.clip(calib.get("calibrationOffset") or 0.0, -1.0, 1.0)),
        "userOffset": 0.0,
        "thresholds": {m: float(modes[m]) for m in ("light", "balanced", "strict")},
        "margin": float(thr.get("margin", DEFAULT_MARGIN)),
    }
    if example_centroid is not None:
        centroid = np.asarray(example_centroid, dtype=np.float32).ravel()
        cc["exampleCentroid"] = {
            "contractVersion": "1.0",
            "spaceId": enc.space_id,
            "modelId": enc.image_model_id if hasattr(enc, "image_model_id") else enc.text_model_id,
            "dim": int(centroid.shape[0]),
            "vectorF16": encode_f16(centroid),
            "kind": "centroid",
        }
        cc["exampleCount"] = len(concept.get("examplePhotos", [])) or 1
        if calib.get("exampleThreshold") is not None:
            cc["exampleThreshold"] = float(np.clip(calib["exampleThreshold"], 0.0, 1.0))
    return cc
