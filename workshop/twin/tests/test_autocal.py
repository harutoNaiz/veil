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
