"""Correction book: per-concept threshold nudge and a bounded exception list (Layer 2 only).

notThis -> nudge += STEP (cap +CAP), vec kept as an exception (oldest dropped past MAX_EXCEPTIONS)
missed  -> nudge -= STEP (floor -CAP)
adjust() applies userOffset = -nudge; filter() turns a verdict into `leave` when the piece is
within EXCEPTION_SIM (cosine) of a stored exception. Layer 1 concepts are never touched.
"""

from __future__ import annotations

import numpy as np

from workshop.contracts.rules import decode_f16, encode_f16

MAX_EXCEPTIONS = 64
STEP = 0.02
CAP = 0.15
EXCEPTION_SIM = 0.92
LAYER1_IDS = frozenset({"nsfw", "nudity"})


def _unit(vec) -> np.ndarray:
    v = np.asarray(vec, dtype=np.float64).ravel()
    return v / max(float(np.linalg.norm(v)), 1e-12)


def _protected(concept_id: str, layer: int) -> bool:
    return layer == 1 or concept_id in LAYER1_IDS


class CorrectionBook:
    def __init__(self) -> None:
        self.nudge: dict[str, float] = {}
        self.exceptions: dict[str, list[np.ndarray]] = {}

    def record(self, fb: dict, vec) -> None:
        if fb.get("layer") != 2:
            raise ValueError("Layer 1 cannot be corrected")
        cid = fb["conceptId"]
        if cid in LAYER1_IDS:
            raise ValueError("Layer 1 cannot be corrected")
        kind = fb["kind"]
        cur = self.nudge.get(cid, 0.0)
        if kind == "notThis":
            self.nudge[cid] = min(cur + STEP, CAP)
            if vec is not None:
                # round-trip through f16 so the stored vector matches the persisted one
                stored = _unit(decode_f16(encode_f16(_unit(vec)), len(vec)))
                lst = self.exceptions.setdefault(cid, [])
                lst.append(stored)
                del lst[:-MAX_EXCEPTIONS]
        elif kind == "missed":
            self.nudge[cid] = max(cur - STEP, -CAP)

    def adjust(self, cc: dict, layer: int = 2) -> dict:
        cid = cc["conceptId"]
        if _protected(cid, int(cc.get("layer", layer))):
            return cc
        return {**cc, "userOffset": -self.nudge.get(cid, 0.0)}

    def filter(self, concept_id: str, vec, verdict: dict, layer: int = 2) -> dict:
        if _protected(concept_id, layer):
            return verdict
        ex = self.exceptions.get(concept_id)
        if not ex:
            return verdict
        sim = float((np.stack(ex) @ _unit(vec)).max())
        if sim >= EXCEPTION_SIM:
            return {**verdict, "decision": "leave"}
        return verdict

    def to_json(self) -> dict:
        ids = sorted(set(self.nudge) | set(self.exceptions))
        return {
            "concepts": {
                i: {
                    "nudge": self.nudge.get(i, 0.0),
                    "exceptions": [encode_f16(e) for e in self.exceptions.get(i, [])],
                }
                for i in ids
            }
        }

    @classmethod
    def from_json(cls, doc: dict, dim: int) -> CorrectionBook:
        book = cls()
        for i, c in doc.get("concepts", {}).items():
            book.nudge[i] = float(c["nudge"])
            book.exceptions[i] = [_unit(decode_f16(b, dim)) for b in c["exceptions"]]
        return book
