"""Re-link the vocab: "kind of" relations from every WordNet sense, plus a near-synonym bridge.

python -m workshop.twin.bank.relink --src data/bank/v1 --out data/bank/v1b

The first vocab build followed only each word's first WordNet sense, so broad words lost their
kinds ("human" -> Homo, never man/woman/child), and those kinds then competed against the word
and inflated its null threshold: a person photo matched "man" better than "human" and nothing
was hidden. Here excl(v) = v + synonyms + hyponyms over all noun senses; a word with few known
kinds also takes the kinds of its near-synonyms (its single closest broad word with centred text
cosine >= BRIDGE_COS, e.g. human -> person 0.75). rel = excl + hypernyms. Thresholds are
recomputed with the new excl (falling back to the old excl when too little of the bank would
remain). Same files and format as the first build; only vocab.bin / vocab.json change.
"""

from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path

import numpy as np

from workshop.twin.bank import bankio
from workshop.twin.bank import vocab as V

BRIDGE_COS = 0.7
BRIDGE_FEW = 5  # a word with fewer in-vocab kinds than this borrows its near-synonyms' kinds
BRIDGE_MANY = 20  # ... from near-synonyms that have at least this many
MIN_NULL = 3000  # keep at least this many bank rows in a word's null set


def senses(wn, name: str) -> tuple[set[str], set[str]]:
    """(synonyms + hyponyms, hypernyms) over all noun senses, lower-case lemma names."""
    down, up = set(), set()
    for s in wn.synsets(name, "n"):
        for x in [s, *s.closure(lambda y: y.hyponyms())]:
            down |= {ln.lower() for ln in x.lemma_names()}
        for x in s.closure(lambda y: y.hypernyms()):
            up |= {ln.lower() for ln in x.lemma_names()}
    return down, up


def relink(src: Path, out: Path, repo: Path) -> dict:
    meta = json.loads((src / "vocab.json").read_text(encoding="utf-8"))
    entries = meta["entries"]
    nouns = [i for i, e in enumerate(entries) if e["kind"] == "noun"]
    pos = {entries[i]["name"]: i for i in nouns}
    wn = V.wn_setup(repo / "data" / "bank" / "src")
    excl, rel = {}, {}
    for i in nouns:
        down, up = senses(wn, entries[i]["name"])
        excl[i] = {i} | {pos[x] for x in down if x in pos}
        rel[i] = excl[i] | {pos[x] for x in up if x in pos}
    vrows = np.load(src / "vocab_emb.npy")
    n_noun = len(nouns)
    center = vrows[:n_noun].mean(0)
    dirs = bankio.direction(vrows[:n_noun], center)
    bridged = {}
    for _ in range(2):  # second pass: "humans" -> "human", bridged in the first pass
        for i in nouns:
            if len(excl[i]) >= BRIDGE_FEW or entries[i]["name"] in bridged:
                continue
            sims = dirs @ dirs[i]
            cand = [
                int(j)
                for j in np.argsort(-sims)
                if int(j) != i and len(excl[int(j)]) >= BRIDGE_MANY
            ]
            j = cand[0] if cand else None
            if j is not None and sims[j] >= BRIDGE_COS:
                excl[i] = excl[i] | excl[j]
                rel[i] = rel[i] | rel[j]
                bridged[entries[i]["name"]] = [entries[j]["name"], round(float(sims[j]), 3)]
    bank = bankio.read_bank(src / "bank.bin")
    lab_sets = [
        set(bank.lab_idx[bank.lab_off[r] : bank.lab_off[r + 1]].tolist())
        for r in range(len(bank.rows))
    ]
    rows_of = {}
    for r, labs in enumerate(lab_sets):
        for lab in labs:
            rows_of.setdefault(lab, set()).add(r)
    fallback = []
    excl_l = []
    for i in nouns:
        keep = len(bank.rows) - len(set().union(*(rows_of.get(x, set()) for x in excl[i])))
        if keep < MIN_NULL:
            excl[i] = set(entries[i]["excl"]) | {i}
            fallback.append(entries[i]["name"])
        excl_l.append(sorted(excl[i]))
    q, scale = bankio.quantise(vrows)
    vdeq = bankio.dequant(q, scale)
    thr = V.thresholds(bank.rows, vdeq[:n_noun], excl_l, lab_sets, center)
    ign = V.thresholds(
        bank.rows, vdeq[n_noun:], [[] for _ in range(len(vrows) - n_noun)], lab_sets, center
    )
    thr = np.concatenate([thr, ign])
    n_pos = {}
    for labs in lab_sets:
        for lab in labs:
            n_pos[lab] = n_pos.get(lab, 0) + 1
    for k, i in enumerate(nouns):
        entries[i]["excl"] = excl_l[k]
        entries[i]["rel"] = sorted(rel[i] | set(excl_l[k]))
        entries[i]["nPos"] = sum(n_pos.get(j, 0) for j in excl_l[k])
    meta["relations"] = "all-senses+bridge-v1"
    out.mkdir(parents=True, exist_ok=True)
    for f in ("bank.bin", "vocab_emb.npy", "engine.json", "items.jsonl"):
        if (src / f).exists():
            shutil.copy2(src / f, out / f)
    bankio.write_vocab(out, vrows, thr, meta)
    return {"bridged": bridged, "fallback": fallback}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="workshop.twin.bank.relink")
    ap.add_argument("--src", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    a = ap.parse_args(argv)
    repo = Path(__file__).resolve().parents[3]
    rep = relink(a.src, a.out, repo)
    print("bridged:", rep["bridged"])
    print("fallback (kept old excl):", len(rep["fallback"]), rep["fallback"][:20])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
