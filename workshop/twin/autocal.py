"""Auto calibration (Chapter 7.1): a word becomes a CompiledConcept whose thresholds come from a
reference bank of ordinary images (the null distribution), plus lookalike competitors.

Every constant is global; nothing is tuned per word. The Kotlin port is AutoCal in the app.
"""

from __future__ import annotations

import numpy as np

from workshop.contracts.rules import concept_sha256, encode_f16
from workshop.twin import teacher
from workshop.twin.bank.bankio import Bank, Vocab, direction, excluded_rows

TEMPLATES = [
    "a photo of a {w}",
    "a {w}",
    "a close-up of a {w}",
    "a {w} in a meme",
    "a drawing of a {w}",
]
Q_PER_MILLE = {"light": 999, "balanced": 995, "strict": 980}
K_COMPETITORS = 8
N_CHIPS = 6
AUTO_MARGIN = 0.0  # spec constant (the on-device Teacher still writes this)
PHONE_MARGIN = 0.04  # phone-kit CLI default, from phone_eval margin sweep
PHONE_K = 128  # phone-kit competitor count (spec K=8): K=8 let rooster/dog tiles fire cats
AUTO_NEAR_BAND = 0.02
IGNORE = teacher.IGNORE
RULE = "null-quantile-v2"
MODES = ("light", "balanced", "strict")


def _l2(v: np.ndarray) -> np.ndarray:
    v = np.asarray(v, dtype=np.float64)
    return v / np.maximum(np.linalg.norm(v, axis=-1, keepdims=True), 1e-12)


def _norm_word(word: str) -> str:
    return " ".join(word.lower().split())


def _singular(word: str) -> str:
    return teacher._singular(_norm_word(word))


def ensemble(enc, word: str) -> np.ndarray:
    """e_w = l2(mean_k l2(text(TEMPLATES[k] with w))), float64."""
    w = _singular(word)
    vecs = _l2(np.asarray(enc.embed_texts([t.format(w=w) for t in TEMPLATES]), dtype=np.float64))
    return _l2(vecs.mean(axis=0))


def quantile_index(n: int, qm: int) -> int:
    """Integer-only index of the per-mille quantile in an ascending array of length n."""
    return min(max((qm * n + 999) // 1000 - 1, 0), n - 1)


def null_thresholds(bank: Bank, q: np.ndarray, excl: set[int]) -> tuple[dict, int]:
    """Quantile thresholds of the scores of `q` against the bank rows that are not excluded."""
    drop = excluded_rows(bank, excl) if excl else np.zeros(len(bank.rows), dtype=bool)
    d = np.sort(bank.rows[~drop] @ _l2(q))
    thr = {m: float(d[quantile_index(len(d), Q_PER_MILLE[m])]) for m in MODES}
    return thr, int(drop.sum())


def lookup(vocab: Vocab, word: str) -> int | None:
    w = _norm_word(word)
    for cand in (w, _singular(w)):
        for i, e in enumerate(vocab.meta["entries"]):
            if e["kind"] == "noun" and cand in e["forms"]:
                return i
    return None


def _rel(vocab: Vocab, idx: int | None, word: str) -> set[int]:
    entries = vocab.meta["entries"]
    if idx is not None:
        return set(entries[idx]["rel"]) | {idx}
    s = _singular(word)
    return {i for i, e in enumerate(entries) if e["kind"] == "noun" and e["name"] == s}


def competitors(
    vocab: Vocab,
    q: np.ndarray,
    idx: int | None,
    word: str,
    positives: set[int] = frozenset(),
    k: int | None = None,
) -> list[int]:
    """Top K noun entries by cosine (not related, not positive), then the ignore entries."""
    entries = vocab.meta["entries"]
    skip = _rel(vocab, idx, word) | set(positives)
    sims = vocab.rows @ _l2(q)
    cand = [i for i, e in enumerate(entries) if e["kind"] == "noun" and i not in skip]
    cand.sort(key=lambda i: (-sims[i], i))
    ign = [i for i, e in enumerate(entries) if e["kind"] == "ignore"]
    return cand[: K_COMPETITORS if k is None else k] + ign


def chips_for(vocab: Vocab, enc, word: str) -> list[str]:
    """The N_CHIPS lookalike names offered for `word`."""
    idx = lookup(vocab, word)
    q = vocab.rows[idx] if idx is not None else ensemble(enc, word)
    return [vocab.meta["entries"][i]["name"] for i in competitors(vocab, q, idx, word)[:N_CHIPS]]


def _emb(enc, vec: np.ndarray, term: str) -> dict:
    return {
        "contractVersion": "1.0",
        "spaceId": enc.space_id,
        "modelId": enc.text_model_id,
        "dim": int(len(vec)),
        "vectorF16": encode_f16(np.asarray(vec, dtype=np.float32)),
        "kind": "text",
        "text": term[:500],
    }


def compile_auto(
    word: str,
    enc,
    bank: Bank,
    vocab: Vocab,
    also_hide=(),
    margin: float = AUTO_MARGIN,
    k: int | None = None,
) -> dict:
    """CompiledConcept v1.0 with an `auto` rule. `also_hide` = chip names turned into positives."""
    entries = vocab.meta["entries"]
    idx = lookup(vocab, word)
    if idx is not None:
        q = vocab.rows[idx]
        d = direction(q, vocab.center)
        thr = dict(zip(MODES, (float(x) for x in vocab.thr[idx]), strict=True))
        _, n_excl = null_thresholds(bank, d, set(entries[idx]["excl"]))
    else:
        q = ensemble(enc, word)
        d = direction(q, vocab.center)
        thr, n_excl = null_thresholds(bank, d, set())
    chips = [entries[i]["name"] for i in competitors(vocab, q, idx, word)[:N_CHIPS]]
    pos_idx = set()
    pos = [(word, d, thr)]
    for name in also_hide:
        j = lookup(vocab, name)
        if j is None or j == idx or j in pos_idx:
            continue
        pos_idx.add(j)
        pos.append(
            (
                entries[j]["name"],
                direction(vocab.rows[j], vocab.center),
                dict(zip(MODES, map(float, vocab.thr[j]), strict=True)),
            )
        )
    comp = competitors(vocab, q, idx, word, pos_idx | ({idx} if idx is not None else set()), k)
    auto = {
        "rule": RULE,
        "bankId": bank.bank_id,
        "margin": margin,
        "excluded": n_excl,
        "chips": chips,
        "positives": [
            {"term": t[:64], "embedding": _emb(enc, v, t), "thresholds": {m: th[m] for m in MODES}}
            for t, v, th in pos
        ],
        "competitors": [
            {
                "term": entries[i]["name"][:64],
                "embedding": _emb(enc, direction(vocab.rows[i], vocab.center), entries[i]["name"]),
                "thresholds": {"balanced": float(vocab.thr[i][1])},
            }
            for i in comp
        ],
    }
    card = teacher.concept_card(word)
    if also_hide:
        card["alsoHide"] = [str(n)[:64] for n in also_hide][:16]
    ign_emb = [
        c["embedding"]
        for c, i in zip(auto["competitors"], comp, strict=True)
        if entries[i]["kind"] == "ignore"
    ]
    but_emb = [
        c["embedding"]
        for c, i in zip(auto["competitors"], comp, strict=True)
        if entries[i]["kind"] != "ignore"
    ]
    p0 = auto["positives"][0]["thresholds"]
    return {
        "contractVersion": "1.0",
        "conceptId": card["conceptId"],
        "spaceId": enc.space_id,
        "textModelId": enc.text_model_id,
        "conceptSha256": concept_sha256(card),
        "looksLike": [p["embedding"] for p in auto["positives"]],
        "butNot": but_emb[:32],
        "ignore": ign_emb[:16],
        "exampleCount": 0,
        "exceptions": [],
        "calibrationOffset": 0.0,
        "userOffset": 0.0,
        "thresholds": {m: float(np.clip(p0[m], 0.0, 1.0)) for m in MODES},
        "margin": margin,
        "auto": auto,
    }


def compile_words_auto(words, out, enc, bank_dir, also_hide=(), margin=PHONE_MARGIN, k=None):
    """Compile each word with the bank into <out>/<conceptId>.json. Returns the paths."""
    import json
    from pathlib import Path

    from workshop.twin.bank import bankio

    bank_dir, out = Path(bank_dir), Path(out)
    bank = bankio.read_bank(bank_dir / "bank.bin")
    vocab = bankio.read_vocab(bank_dir)
    out.mkdir(parents=True, exist_ok=True)
    paths = []
    for word in words:
        cc = compile_auto(word, enc, bank, vocab, also_hide=also_hide, margin=margin, k=k)
        path = out / f"{cc['conceptId']}.json"
        path.write_text(json.dumps(cc, indent=2), encoding="utf-8")
        paths.append(path)
    return paths


def main(argv: list[str] | None = None) -> int:
    import argparse
    import json
    from pathlib import Path

    ap = argparse.ArgumentParser(prog="workshop.twin.autocal")
    sub = ap.add_subparsers(dest="cmd", required=True)
    c = sub.add_parser("compile", help="compile words into auto CompiledConcept JSON files")
    c.add_argument("--bank", required=True, type=Path)
    c.add_argument("--out", required=True, type=Path)
    c.add_argument("--also-hide", nargs="*", default=[])
    c.add_argument("--margin", type=float, default=PHONE_MARGIN)
    c.add_argument("--k", type=int, default=PHONE_K)
    c.add_argument("words", nargs="+")
    a = ap.parse_args(argv)
    from workshop.forge.siglip2.runtime import OnnxDescriber

    for p in compile_words_auto(
        a.words, a.out, OnnxDescriber(), a.bank, a.also_hide, a.margin, a.k
    ):
        d = json.loads(p.read_text(encoding="utf-8"))["auto"]
        print(
            f"{p} positives={len(d['positives'])} competitors={len(d['competitors'])} "
            f"thr={d['positives'][0]['thresholds']} excluded={d['excluded']} chips={d['chips']}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
