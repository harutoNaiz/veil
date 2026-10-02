"""Cross-field rules JSON Schema cannot express: spaces, vectors and the concept hash."""

from __future__ import annotations

import base64
import copy
import json
from pathlib import Path

import numpy as np
import pytest

from workshop.contracts.rules import (
    SpaceMismatchError,
    VectorError,
    check_rules,
    concept_sha256,
    decode_f16,
    encode_f16,
)
from workshop.contracts.validate import SCHEMA_DIR, type_for_path

EXAMPLES = SCHEMA_DIR / "examples"
VALID = sorted(EXAMPLES.glob("*/valid-*.json"))


def rel(path: Path) -> str:
    return path.relative_to(EXAMPLES).as_posix()


def load(name: str) -> dict:
    return json.loads((EXAMPLES / name).read_text(encoding="utf-8"))


@pytest.mark.parametrize("path", VALID, ids=rel)
def test_rules_pass_on_valid_examples(path):
    check_rules(type_for_path(path), json.loads(path.read_text(encoding="utf-8")))


def test_space_mismatch_raises():
    cc = copy.deepcopy(load("compiled-concept/valid-01-cats-siglip2.json"))
    cc["looksLike"][0]["spaceId"] = "yoloe-v1-text-prompt"
    with pytest.raises(SpaceMismatchError):
        check_rules("CompiledConcept", cc)


def test_feedback_space_mismatch_raises():
    fb = copy.deepcopy(load("feedback/valid-01-not-this-fox.json"))
    fb["embedding"]["spaceId"] = "yoloe-v1-text-prompt"
    with pytest.raises(SpaceMismatchError):
        check_rules("Feedback", fb)


def test_bad_vector_length_raises():
    e = copy.deepcopy(load("embedding/valid-01-text-prompt-dim8.json"))
    e["dim"] = 7
    with pytest.raises(VectorError):
        check_rules("Embedding", e)
    with pytest.raises(VectorError):
        decode_f16(e["vectorF16"], 9)


def test_unnormalised_vector_raises():
    e = copy.deepcopy(load("embedding/valid-01-text-prompt-dim8.json"))
    raw = np.frombuffer(base64.b64decode(e["vectorF16"]), dtype="<f2") * 3
    e["vectorF16"] = base64.b64encode(raw.astype("<f2").tobytes()).decode("ascii")
    with pytest.raises(VectorError):
        check_rules("Embedding", e)


@pytest.mark.parametrize("dim", [8, 768])
def test_encode_decode_roundtrip(dim):
    vec = np.random.default_rng(5).standard_normal(dim)
    back = decode_f16(encode_f16(vec), dim).astype(np.float64)
    cosine = float(vec @ back / (np.linalg.norm(vec) * np.linalg.norm(back)))
    assert cosine >= 0.999
    assert abs(float(np.linalg.norm(back)) - 1.0) <= 0.01


def test_concept_sha256_is_key_order_independent():
    concept = load("concept/valid-01-cats-layer2.json")
    shuffled = dict(reversed(list(concept.items())))
    assert list(shuffled) != list(concept)
    assert concept_sha256(shuffled) == concept_sha256(concept)
    changed = {**concept, "displayName": "Kittens"}
    assert concept_sha256(changed) != concept_sha256(concept)


def test_compiled_concept_examples_carry_the_concept_hash():
    concept = load("concept/valid-01-cats-layer2.json")
    for name in ("valid-01-cats-siglip2", "valid-02-cats-yoloe-text"):
        cc = load(f"compiled-concept/{name}.json")
        assert cc["conceptSha256"] == concept_sha256(concept)
