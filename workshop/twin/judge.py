"""Judge v0: compares piece fingerprints with a CompiledConcept and decides hide / nearMiss / leave.

Per piece:  sL, sN, sI = best cosine against looksLike / butNot / ignore phrases (empty group: -1)
            p_raw = softmax(T * [sL, sN, sI])[0] with T = 100
            p = clip(p_raw + calibrationOffset + userOffset, 0, 1); margin = sL - sN; score = sL
            hide if (p >= thr[mode] and margin >= cc.margin) or (sE >= exampleThreshold)
            nearMiss if not hide and p >= thr[mode] - 0.1, else leave
"""

from __future__ import annotations

import functools

import numpy as np

from workshop.contracts.rules import decode_f16

T = 100.0
NEAR_MISS_BAND = 0.1
MODES = ("light", "balanced", "strict")


@functools.lru_cache(maxsize=8192)
def _decode(b64: str, dim: int) -> np.ndarray:
    vec = decode_f16(b64, dim).astype(np.float32)
    vec.setflags(write=False)
    return vec


def _matrix(embeddings: list[dict]) -> np.ndarray | None:
    if not embeddings:
        return None
    mat = np.stack([_decode(e["vectorF16"], e["dim"]) for e in embeddings]).astype(np.float64)
    return mat / np.maximum(np.linalg.norm(mat, axis=1, keepdims=True), 1e-12)


def _best(vecs: np.ndarray, embeddings: list[dict]) -> np.ndarray:
    mat = _matrix(embeddings)
    if mat is None:
        return np.full(len(vecs), -1.0)
    return (vecs @ mat.T).max(axis=1)


def judge(vecs: np.ndarray, cc: dict, mode: str = "balanced") -> list[dict]:
    """One verdict per row of `vecs` (L2-normalised piece fingerprints, same space as `cc`)."""
    if mode not in MODES:
        raise ValueError(f"mode must be one of {MODES}, got {mode!r}")
    vecs = np.atleast_2d(np.asarray(vecs, dtype=np.float64))
    if vecs.size == 0:
        return []
    s_look = _best(vecs, cc["looksLike"])
    s_not = _best(vecs, cc.get("butNot", []))
    s_ign = _best(vecs, cc.get("ignore", []))
    logits = T * np.stack([s_look, s_not, s_ign], axis=1)
    logits -= logits.max(axis=1, keepdims=True)
    expo = np.exp(logits)
    p_raw = expo[:, 0] / expo.sum(axis=1)
    shift = cc.get("calibrationOffset", 0.0) + cc.get("userOffset", 0.0)
    prob = np.clip(p_raw + shift, 0.0, 1.0)
    margin = s_look - s_not
    thr = cc["thresholds"][mode]
    s_ex = None
    if cc.get("exampleCentroid") is not None:
        centroid = _matrix([cc["exampleCentroid"]])[0]
        s_ex = vecs @ centroid
    ex_thr = cc.get("exampleThreshold")
    verdicts = []
    for i in range(len(vecs)):
        hide = bool(prob[i] >= thr and margin[i] >= cc.get("margin", 0.0))
        if s_ex is not None and ex_thr is not None and s_ex[i] >= ex_thr:
            hide = True
        if hide:
            decision = "hide"
        elif prob[i] >= thr - NEAR_MISS_BAND:
            decision = "nearMiss"
        else:
            decision = "leave"
        verdicts.append(
            {
                "p_raw": float(p_raw[i]),
                "probability": float(prob[i]),
                "score": float(s_look[i]),
                "margin": float(margin[i]),
                "decision": decision,
            }
        )
        if s_ex is not None:
            verdicts[-1]["exampleScore"] = float(s_ex[i])
    return verdicts


def to_findings(
    image: str, regions: list[dict], verdicts: list[dict], concept_id: str, lane: str
) -> list[dict]:
    """Finding v1.0 for the hide and nearMiss verdicts only."""
    findings = []
    for i, (region, v) in enumerate(zip(regions, verdicts, strict=True)):
        if v["decision"] == "leave":
            continue
        findings.append(
            {
                "contractVersion": "1.0",
                "findingId": f"f{i}-{region['regionId']}"[:64],
                "lookId": int(region.get("lookId", 0)),
                "tMs": int(region.get("tMs", 0)),
                "image": image,
                "regionId": region["regionId"],
                "rect": dict(region["rect"]),
                "conceptId": concept_id,
                "layer": 2,
                "lane": lane,
                "decision": v["decision"],
                "probability": float(np.clip(v["probability"], 0.0, 1.0)),
                "score": float(np.clip(v["score"], -1.0, 1.0)),
                "margin": float(np.clip(v["margin"], -2.0, 2.0)),
                "scope": "object",
            }
        )
    return findings
