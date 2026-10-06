"""7.1.2 auto threshold twin: quantile, exclusion, competitors, auto judge, schema, fixture."""

from __future__ import annotations

import importlib.util
import json
from pathlib import Path

import numpy as np
import pytest

from workshop.contracts.validate import REPO_ROOT, validate
from workshop.twin import autocal, judge
from workshop.twin.bank import bankio

FIX = Path(__file__).resolve().parent / "fixtures" / "autocal"
GOLDEN = REPO_ROOT / "guard" / "brain" / "src" / "test" / "resources" / "judge-golden.json"


def _make_mod():
    spec = importlib.util.spec_from_file_location("autocal_make", FIX / "make.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


MAKE = _make_mod()


@pytest.fixture(scope="module")
def world():
    bank = bankio.read_bank(FIX / "bank.bin")
    vocab = bankio.read_vocab(FIX)
    expected = json.loads((FIX / "expected.json").read_text(encoding="utf-8"))
    return bank, vocab, expected, MAKE.StubEncoder()


def test_fixture_regenerates_identical(tmp_path):
    MAKE.make_fixture(tmp_path)
    for name in ("bank.bin", "vocab.bin", "vocab.json", "expected.json"):
        assert (tmp_path / name).read_bytes() == (FIX / name).read_bytes(), name


@pytest.mark.parametrize("n", [600, 2000, 30000])
def test_quantile_index(n):
    for qm in autocal.Q_PER_MILLE.values():
        k = autocal.quantile_index(n, qm)
        assert k == (qm * n + 999) // 1000 - 1
        assert 0 <= k <= n - 1
        assert (k + 1) * 1000 >= qm * n
    assert autocal.quantile_index(1, 995) == 0
    assert autocal.quantile_index(600, 995) == 596


def test_exclusion_changes_thresholds(world):
    bank, vocab, _, _ = world
    q = vocab.rows[3]
    ex = set(vocab.meta["entries"][3]["excl"])
    _, n0 = autocal.null_thresholds(bank, q, set())
    thr_ex, n1 = autocal.null_thresholds(bank, q, ex)
    assert n0 == 0 and n1 > 0
    mask = bankio.excluded_rows(bank, ex)
    d = np.sort(bank.rows[~mask] @ q)
    assert thr_ex["balanced"] == float(d[autocal.quantile_index(len(d), 995)])


def test_in_vocab_uses_stored_thresholds(world):
    bank, vocab, _, enc = world
    cc = autocal.compile_auto("noun03", enc, bank, vocab)
    got = cc["auto"]["positives"][0]["thresholds"]
    for m, v in zip(autocal.MODES, vocab.thr[3], strict=True):
        assert got[m] == float(v)
    assert cc["auto"]["bankId"] == bank.bank_id
    assert autocal.lookup(vocab, "NOUN03s ") == 3
    assert autocal.lookup(vocab, "zorp") is None


def test_competitor_order(world):
    _, vocab, _, enc = world
    entries = vocab.meta["entries"]
    idx = 3
    comp = autocal.competitors(vocab, vocab.rows[idx], idx, "noun03")
    nouns = comp[: autocal.K_COMPETITORS]
    ign = comp[autocal.K_COMPETITORS :]
    assert len(nouns) == 8 and [entries[i]["kind"] for i in ign] == ["ignore"] * 3
    rel = set(entries[idx]["rel"]) | {idx}
    assert not (set(nouns) & rel)
    sims = [vocab.rows[i] @ vocab.rows[idx] for i in nouns]
    assert sims == sorted(sims, reverse=True)
    more = autocal.competitors(vocab, vocab.rows[idx], idx, "noun03", {nouns[0]})
    assert nouns[0] not in more
    assert len(autocal.chips_for(vocab, enc, "noun03")) == autocal.N_CHIPS
    oov = autocal.competitors(vocab, autocal.ensemble(enc, "zorp"), None, "zorp")
    assert len([i for i in oov if entries[i]["kind"] == "noun"]) == 8


def _cc(thr_m, comp_thr=None):
    e = MAKE.StubEncoder()
    p = np.zeros(8)
    p[0] = 1.0
    c = np.zeros(8)
    c[1] = 1.0
    auto = {
        "rule": "null-quantile-v1",
        "bankId": "x",
        "margin": 0.0,
        "excluded": 0,
        "chips": [],
        "positives": [
            {
                "term": "a",
                "embedding": autocal._emb(e, p, "a"),
                "thresholds": {"light": thr_m + 0.1, "balanced": thr_m, "strict": thr_m - 0.1},
            }
        ],
        "competitors": [],
    }
    if comp_thr is not None:
        auto["competitors"] = [
            {
                "term": "c",
                "embedding": autocal._emb(e, c, "c"),
                "thresholds": {"balanced": comp_thr},
            }
        ]
    return {"auto": auto, "thresholds": {"light": 0.5, "balanced": 0.5, "strict": 0.5}}


def _v(a, b):
    v = np.zeros(8)
    v[0], v[1] = a, b
    v[2] = np.sqrt(max(0.0, 1 - a * a - b * b))
    return v


def test_auto_judge_cases():
    cc = _cc(0.4)
    assert judge.judge(_v(0.5, 0), cc)[0]["decision"] == "hide"
    assert judge.judge(_v(0.39, 0), cc)[0]["decision"] == "nearMiss"
    assert judge.judge(_v(0.3, 0), cc)[0]["decision"] == "leave"
    assert judge.judge(_v(0.45, 0), cc, "light")[0]["decision"] != "hide"
    assert judge.judge(_v(0.45, 0), cc, "strict")[0]["decision"] == "hide"
    cc2 = _cc(0.4, comp_thr=0.3)
    assert judge.judge(_v(0.5, 0.8), cc2)[0]["decision"] != "hide"
    assert judge.judge(_v(0.5, 0.1), cc2)[0]["decision"] == "hide"
    v = judge.judge(_v(0.5, 0.0), cc)[0]
    assert v["probability"] == v["p_raw"] and v["margin"] > 1e8


def test_auto_judge_matches_fixture(world):
    _, _, expected, _ = world
    for j in expected["judge"]:
        cc = {"auto": expected["queries"][j["query"]]["auto"]}
        got = judge.judge(np.array(j["vector"]), cc, j["mode"])[0]
        assert got == j["verdict"]


def test_old_cards_unchanged():
    cases = json.loads(GOLDEN.read_text(encoding="utf-8"))["cases"]
    assert cases
    for c in cases:
        assert "auto" not in c["concept"]
        assert judge.judge(np.array(c["vecs"]), c["concept"], c["mode"]) == c["verdicts"]


def test_schemas(world):
    bank, vocab, _, enc = world
    cc = autocal.compile_auto("noun07", enc, bank, vocab, also_hide=["noun25", "noun23"])
    validate("CompiledConcept", cc)
    assert [p["term"] for p in cc["auto"]["positives"]] == ["noun07", "noun25", "noun23"]
    card = {
        "contractVersion": "1.0",
        "conceptId": "noun07",
        "displayName": "Noun07",
        "layer": 2,
        "enabled": True,
        "looksLike": ["a photo of a noun07"],
        "butNot": [],
        "scope": "object",
        "coverStyle": "solid",
        "showLabel": False,
        "alsoHide": ["noun25"],
    }
    validate("Concept", card)
    with pytest.raises(Exception):  # noqa: B017
        validate("Concept", dict(card, alsoHide=["x"] * 17))
    bad_cc = json.loads(json.dumps(cc))
    bad_cc["auto"]["extra"] = 1
    with pytest.raises(Exception):  # noqa: B017
        validate("CompiledConcept", bad_cc)


def test_center_is_noun_mean(world):
    _, vocab, _, _ = world
    ents = vocab.meta["entries"]
    nouns = [i for i, e in enumerate(ents) if e["kind"] == "noun"]
    assert len(nouns) < len(ents)
    assert np.array_equal(vocab.center, vocab.rows[nouns].mean(0))
    d = bankio.direction(vocab.rows[3], vocab.center)
    assert abs(np.linalg.norm(d) - 1) < 1e-12
    assert autocal.RULE == "null-quantile-v2"


def test_v2_fixes_common_mode_offset():
    """Two domains with different mean projections on the shared direction: v1 fails, v2 passes."""
    rng = np.random.default_rng(5)
    dim, n = 64, 4000
    u0 = np.zeros(dim)
    u0[0] = 1.0

    def unit(x):
        return x / np.linalg.norm(x, axis=-1, keepdims=True)

    def domain(off, m):
        x = rng.normal(size=(m, dim)) / np.sqrt(dim)
        x[:, 0] = off
        return unit(x)

    bank_rows, clean = domain(0.05, n), domain(0.35, 500)  # screens project harder on u0
    nouns = unit(0.92 * u0 + 0.4 * rng.normal(size=(50, dim)) / np.sqrt(dim))
    center = nouns.mean(0)
    word = nouns[0]
    bank = bankio.Bank(bank_rows, np.zeros(n + 1, dtype=np.uint32), np.zeros(0, np.uint16), "x")
    thr1, _ = autocal.null_thresholds(bank, word, set())
    d = bankio.direction(word, center)
    thr2, _ = autocal.null_thresholds(bank, d, set())
    fc1 = float(np.mean(clean @ word >= thr1["balanced"]))
    fc2 = float(np.mean(clean @ d >= thr2["balanced"]))
    assert fc1 > 0.5 and fc2 < 0.05, (fc1, fc2)


def test_kite_in_vocabulary():
    from workshop.twin.bank import vocab as bv

    src = REPO_ROOT / "data" / "bank" / "src"
    if not (src / "nltk").exists():
        pytest.skip("wordnet data not present")
    wn = bv.wn_setup(src)
    assert bv._ok_synset(wn, "kite")
    assert not bv._ok_synset(wn, "qzxv")
