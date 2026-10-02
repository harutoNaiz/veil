"""Cross-field rules that JSON Schema cannot express. They operate on plain dicts.

- Vectors: ``vectorF16`` is base64 of ``dim`` little-endian float16 values, L2-normalised.
- Spaces: a fingerprint may only be compared with a concept of the same ``spaceId``.
- Concepts: ``conceptSha256`` is the hash of the canonical JSON of the source Concept.
"""

from __future__ import annotations

import base64
import binascii
import hashlib
import json
from collections.abc import Mapping

import numpy as np

NORM_TOLERANCE = 0.01


class SpaceMismatchError(ValueError):
    """Two fingerprints or a fingerprint and a concept come from different model families."""


class VectorError(ValueError):
    """A fingerprint vector is malformed (wrong length, not finite, not normalised)."""


def encode_f16(vec) -> str:
    """L2-normalise in float64, cast to little-endian float16 and return base64 text."""
    arr = np.asarray(vec, dtype=np.float64).ravel()
    norm = float(np.linalg.norm(arr))
    if not np.isfinite(norm) or norm == 0.0:
        raise VectorError("cannot normalise a zero or non-finite vector")
    return base64.b64encode((arr / norm).astype("<f2").tobytes()).decode("ascii")


def decode_f16(b64: str, dim: int) -> np.ndarray:
    """Decode base64 float16 into a float32 array of length ``dim``."""
    try:
        raw = base64.b64decode(b64, validate=True)
    except (binascii.Error, ValueError) as exc:
        raise VectorError(f"vectorF16 is not valid base64: {exc}") from exc
    if len(raw) != 2 * dim:
        raise VectorError(f"vectorF16 holds {len(raw)} bytes, expected {2 * dim} for dim {dim}")
    arr = np.frombuffer(raw, dtype="<f2").astype(np.float32)
    if not np.all(np.isfinite(arr)):
        raise VectorError("vectorF16 contains a non-finite value")
    return arr


def check_embedding(e: Mapping) -> None:
    """The vector decodes to ``dim`` finite values and has an L2 norm within 0.01 of 1."""
    arr = decode_f16(e["vectorF16"], e["dim"])
    norm = float(np.linalg.norm(arr.astype(np.float64)))
    if abs(norm - 1.0) > NORM_TOLERANCE:
        raise VectorError(f"vector is not L2-normalised: norm {norm:.4f}")


def check_same_space(a: str, b: str) -> None:
    if a != b:
        raise SpaceMismatchError(f"spaceId mismatch: {a!r} != {b!r}")


def _nested_embeddings(cc: Mapping) -> list[Mapping]:
    found: list[Mapping] = []
    for key in ("looksLike", "butNot", "ignore", "exceptions"):
        found.extend(cc.get(key, []))
    if "exampleCentroid" in cc:
        found.append(cc["exampleCentroid"])
    return found


def check_compiled_concept(cc: Mapping) -> None:
    """Every nested Embedding has the concept's spaceId, one common dim, and a valid vector."""
    dims: set[int] = set()
    for embedding in _nested_embeddings(cc):
        check_same_space(cc["spaceId"], embedding["spaceId"])
        check_embedding(embedding)
        dims.add(embedding["dim"])
    if len(dims) > 1:
        raise VectorError(f"embeddings of one compiled concept differ in dim: {sorted(dims)}")


def check_feedback(fb: Mapping) -> None:
    """If the feedback carries an embedding, it is in the feedback's space and valid."""
    if "embedding" in fb:
        check_same_space(fb["spaceId"], fb["embedding"]["spaceId"])
        check_embedding(fb["embedding"])


def concept_sha256(concept: Mapping) -> str:
    """SHA-256 of the canonical JSON (sorted keys, no spaces, UTF-8) of a Concept."""
    text = json.dumps(concept, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def check_rules(type_name: str, instance: Mapping) -> None:
    """Run the cross-field rules of a type; a no-op for types without any."""
    if type_name == "Embedding":
        check_embedding(instance)
    elif type_name == "CompiledConcept":
        check_compiled_concept(instance)
    elif type_name == "Feedback":
        check_feedback(instance)
