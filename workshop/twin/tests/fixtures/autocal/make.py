"""Parity fixture for the auto rule: bank.bin, vocab.bin, vocab.json, expected.json (seed 71).

Run:  python -m workshop.twin.tests.fixtures.autocal.make [OUT_DIR]
"""

from __future__ import annotations

import json
import sys
import zlib
from pathlib import Path

import numpy as np

from workshop.twin import autocal, judge
from workshop.twin.bank import bankio

HERE = Path(__file__).resolve().parent
DIM = 32
N_BANK = 600
N_NOUN = 30


class StubEncoder:
    space_id = "stub-space"
    text_model_id = "stub-text"

    def embed_texts(self, texts: list[str]) -> np.ndarray:
        out = [np.random.default_rng(zlib.crc32(t.encode())).normal(size=DIM) for t in texts]
        out = np.array(out)
        return (out / np.linalg.norm(out, axis=1, keepdims=True)).astype(np.float32)


def _unit(rng, n):
    v = rng.normal(size=(n, DIM))
    return v / np.linalg.norm(v, axis=1, keepdims=True)


def _entries() -> list[dict]:
    ents = []
    for i in range(N_NOUN):
        name = f"noun{i:02d}"
        excl = [i] if i % 5 else [i, (i + 1) % N_NOUN]
        rel = sorted(set(excl) | {(i + 2) % N_NOUN})
        ents.append(
            {"name": name, "kind": "noun", "forms": [name, name + "s"], "excl": excl, "rel": rel}
        )
    for k, phrase in enumerate(autocal.IGNORE):
        ents.append(
            {"name": phrase, "kind": "ignore", "forms": [phrase], "excl": [], "rel": [], "nPos": 0}
            | {"k": k}
        )
    for e in ents:
        e.setdefault("nPos", 0)
        e.pop("k", None)
    return ents


def make_fixture(out: Path = HERE) -> None:
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(71)
    labels = [sorted(set(int(x) for x in rng.integers(0, N_NOUN, rng.integers(0, 3))))
              for _ in range(N_BANK)]
    bankio.write_bank(out / "bank.bin", _unit(rng, N_BANK), labels)
    bank = bankio.read_bank(out / "bank.bin")
    ents = _entries()
    vrows = bankio.dequant(*bankio.quantise(_unit(rng, len(ents))))
    thr = np.zeros((len(ents), 3), dtype=np.float32)
    for i, e in enumerate(ents):
        t, n = autocal.null_thresholds(bank, vrows[i], set(e["excl"]))
        thr[i] = [t[m] for m in autocal.MODES]
        e["nPos"] = n if e["kind"] == "noun" else 0
    meta = {
        "version": 1,
        "bankId": bank.bank_id,
        "dim": DIM,
        "templates": autocal.TEMPLATES,
        "ignore": autocal.IGNORE,
        "quantilesPerMille": autocal.Q_PER_MILLE,
        "k": autocal.K_COMPETITORS,
        "chips": autocal.N_CHIPS,
        "margin": autocal.AUTO_MARGIN,
        "entries": ents,
    }
    bankio.write_vocab(out, vrows, thr, meta)
    vocab = bankio.read_vocab(out)
    enc = StubEncoder()
    plans = [("noun03", []), ("zorp", []), ("noun07", None)]
    queries, judges = [], []
    for qi, (word, also) in enumerate(plans):
        if also is None:
            also = autocal.chips_for(vocab, enc, word)[:2]
        cc = autocal.compile_auto(word, enc, bank, vocab, also_hide=also)
        idx = autocal.lookup(vocab, word)
        q = vocab.rows[idx] if idx is not None else autocal.ensemble(enc, word)
        auto = cc["auto"]
        queries.append(
            {
                "word": word,
                "alsoHide": list(also),
                "vector": [float(x) for x in q],
                "thresholds": auto["positives"][0]["thresholds"],
                "excluded": auto["excluded"],
                "competitors": [c["term"] for c in auto["competitors"]],
                "chips": auto["chips"],
                "auto": auto,
            }
        )
        judges.extend(_judge_cases(qi, cc, q, rng))
    expected = {
        "queries": queries,
        "vocabThr": [[float(x) for x in row] for row in thr],
        "judge": judges,
    }
    (out / "expected.json").write_text(json.dumps(expected, indent=1), encoding="utf-8")


def _judge_cases(qi: int, cc: dict, q: np.ndarray, rng) -> list[dict]:
    auto = cc["auto"]
    c0 = judge._matrix([auto["competitors"][0]["embedding"]])[0]
    r = rng.normal(size=DIM)
    r -= (r @ q) * q
    r /= np.linalg.norm(r)
    s = auto["positives"][0]["thresholds"]["balanced"] - 0.01
    near = s * q + np.sqrt(1 - s * s) * r
    mix = (q + c0) / np.linalg.norm(q + c0)
    vecs = [q, c0, mix, near, r]
    modes = ["balanced", "light", "strict", "balanced", "strict"]
    out = []
    for v, m in zip(vecs, modes, strict=True):
        verdict = judge.judge(v, cc, m)[0]
        out.append(
            {"query": qi, "mode": m, "vector": [float(x) for x in v], "verdict": verdict}
        )
    return out


if __name__ == "__main__":
    make_fixture(Path(sys.argv[1]) if len(sys.argv) > 1 else HERE)
