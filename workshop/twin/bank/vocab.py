"""Vocabulary: WordNet lemmas from COCO captions, excl/rel sets, ensembles, thresholds."""

from __future__ import annotations

import re
from collections import Counter
from collections.abc import Callable, Iterable
from pathlib import Path

import numpy as np

from workshop.twin.bank.bankio import direction
from workshop.twin.teacher import IGNORE

TEMPLATES = [
    "a photo of a {w}",
    "a {w}",
    "a close-up of a {w}",
    "a {w} in a meme",
    "a drawing of a {w}",
]
Q_PER_MILLE = {"light": 999, "balanced": 995, "strict": 980}
ROOTS = ("organism.n.01", "artifact.n.01", "food.n.01", "food.n.02", "natural_object.n.01")


def tokens(caption: str) -> list[str]:
    return re.findall(r"[a-z]+", caption.lower())


def wn_setup(src: Path):
    import nltk

    d = str(Path(src) / "nltk")
    if d not in nltk.data.path:
        nltk.data.path.insert(0, d)
    try:
        from nltk.corpus import wordnet as wn

        wn.ensure_loaded()
    except LookupError:
        nltk.download("wordnet", download_dir=d, quiet=True)
        from nltk.corpus import wordnet as wn

        wn.ensure_loaded()
    return wn


def _ok_synset(wn, lemma: str) -> bool:
    syns = wn.synsets(lemma, "n")
    if not syns:
        return False
    for s in syns:
        closure = {s.name()} | {x.name() for x in s.closure(lambda x: x.hypernyms())}
        if any(r in closure for r in ROOTS):
            return True
    return False


def build_lemmas(captions: Iterable[str], limit: int, wn) -> list[dict]:
    """Top `limit` noun lemmas (count >= 2) over all captions; forms = raw tokens."""
    counts: Counter = Counter()
    forms: dict[str, set[str]] = {}
    cache: dict[str, str | None] = {}
    for c in captions:
        for t in tokens(c):
            if t not in cache:
                cache[t] = wn.morphy(t, "n")
            lem = cache[t]
            if lem is None:
                continue
            counts[lem] += 1
            forms.setdefault(lem, set()).add(t)
    out = []
    for lem, n in sorted(counts.items(), key=lambda kv: (-kv[1], kv[0])):
        if n < 2:
            break
        if _ok_synset(wn, lem):
            out.append({"name": lem, "forms": sorted(forms[lem] | {lem}), "count": n})
            if len(out) >= limit:
                break
    return out


def wordnet_neighbours(wn) -> Callable[[str], tuple[set[str], set[str]]]:
    """name -> (synonyms + hyponyms, hypernyms) as lower-case lemma names."""

    def names(synsets) -> set[str]:
        return {ln.lower() for s in synsets for ln in s.lemma_names()}

    def f(name: str) -> tuple[set[str], set[str]]:
        syns = wn.synsets(name, "n")
        if not syns:
            return set(), set()
        s = syns[0]
        down = [s, *s.closure(lambda x: x.hyponyms())]
        up = list(s.closure(lambda x: x.hypernyms()))
        return names(down), names(up)

    return f


def relations(
    names: list[str], neighbours: Callable[[str], tuple[set[str], set[str]]]
) -> tuple[list[list[int]], list[list[int]]]:
    """excl(v) = {v} + synonyms + hyponyms in vocab; rel(v) = excl + hypernyms in vocab."""
    pos = {n: i for i, n in enumerate(names)}
    excl, rel = [], []
    for i, name in enumerate(names):
        down, up = neighbours(name)
        e = {i} | {pos[x] for x in down if x in pos}
        r = e | {pos[x] for x in up if x in pos}
        excl.append(sorted(e))
        rel.append(sorted(r))
    return excl, rel


def ensemble(embed_texts: Callable[[list[str]], np.ndarray], words: list[str]) -> np.ndarray:
    """e_w = l2(mean_k l2(text(template_k(w)))), float64."""
    texts = [t.format(w=w) for w in words for t in TEMPLATES]
    e = np.asarray(embed_texts(texts), dtype=np.float64)
    e /= np.maximum(np.linalg.norm(e, axis=1, keepdims=True), 1e-300)
    m = e.reshape(len(words), len(TEMPLATES), -1).mean(axis=1)
    return m / np.maximum(np.linalg.norm(m, axis=1, keepdims=True), 1e-300)


def ignore_rows(embed_texts: Callable[[list[str]], np.ndarray]) -> np.ndarray:
    e = np.asarray(embed_texts(list(IGNORE)), dtype=np.float64)
    return e / np.maximum(np.linalg.norm(e, axis=1, keepdims=True), 1e-300)


def quantile(d: np.ndarray, qm: int) -> float:
    d = np.sort(d)
    n = len(d)
    k = min(max((qm * n + 999) // 1000 - 1, 0), n - 1)
    return float(d[k])


def thresholds(
    bank_rows: np.ndarray,
    vocab_rows: np.ndarray,
    excl: list[list[int]],
    lab_sets: list[set[int]],
    center: np.ndarray | None = None,
) -> np.ndarray:
    """(n_vocab, 3) float32 thresholds (light, balanced, strict) from the null scores."""
    by_label: dict[int, list[int]] = {}
    for r, labs in enumerate(lab_sets):
        for lab in labs:
            by_label.setdefault(lab, []).append(r)
    thr = np.zeros((len(vocab_rows), 3), dtype=np.float32)
    for lo in range(0, len(vocab_rows), 256):
        blk = vocab_rows[lo : lo + 256]
        if center is not None:
            blk = direction(blk, center)
        scores = bank_rows @ blk.T  # float64
        for j in range(scores.shape[1]):
            v = lo + j
            keep = np.ones(len(bank_rows), dtype=bool)
            for lab in excl[v]:
                keep[by_label.get(lab, [])] = False
            d = scores[keep, j]
            if len(d) == 0:
                d = scores[:, j]
            thr[v] = [quantile(d, Q_PER_MILLE[m]) for m in ("light", "balanced", "strict")]
    return thr
