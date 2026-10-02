"""1.3.3 tests on stub data: calibration maths, thresholds, decision block, report skeleton."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from workshop.twin import calibrate as C
from workshop.twin import report as R


def rect(x=0, y=0, w=10, h=10):
    return {"x": x, "y": y, "w": w, "h": h}


def hits_stub(a, b):
    return a == b


def test_offset_formula():
    vals = list(range(101))  # q95 of 0..100 is exactly 95 -> scale to 0..1
    q = C.q95([v / 100 for v in vals])
    assert q == pytest.approx(0.95)
    assert C.offset_from_q95(q) == pytest.approx(-0.45)
    assert C.offset_from_q95(0.0) == 0.5
    assert C.offset_from_q95(5.0) == -1.0  # clipped
    assert C.offset_from_q95(-5.0) == 1.0  # clipped
    assert C.offset_from_q95(None) == 0.0
    labels = [
        {"image": "a.png", "boxes": [{"concept": "cats", "rect": rect()}]},
        {"image": "b.png", "boxes": []},
        {"image": "c.png", "boxes": [{"concept": "spiders", "rect": rect()}]},
    ]
    # a.png has a cat box so it is excluded; b and c count: q95 of [0.2, 0.4] = 0.39
    off = C.offset_for_concept(labels, {"a.png": 0.99, "b.png": 0.2, "c.png": 0.4}, "cats")
    assert off == pytest.approx(0.5 - 0.39, abs=1e-6)


def _rows(fc_by_t):
    return [
        {"t": t, "recall": 0.9, "precision": 0.9, "cleanFalseCover": fc_by_t(t)} for t in C.GRID
    ]


def test_threshold_ordering_and_all_concepts():
    sweeps = {
        "cats": _rows(
            lambda t: max(0.0, 0.5 - t)
        ),  # 0.05 reached at t=0.45, 0.01 at 0.5 (0.0), 0.15 at 0.35
        "spiders": _rows(lambda t: max(0.0, 0.6 - t)),  # slower: 0.05 at 0.55, 0.15 at 0.45
    }
    thr, notes = C.pick_thresholds(sweeps)
    assert thr["light"] >= thr["balanced"] >= thr["strict"]
    assert thr["balanced"] == 0.55 and thr["strict"] == 0.45  # the worst concept decides
    assert notes == []


def test_threshold_enforces_order_and_unreachable():
    # a non-monotone sweep that would give Strict > Balanced is repaired by raising
    sweeps = {"cats": _rows(lambda t: 0.0 if t in (0.1, 0.9) else 0.5)}
    thr, _ = C.pick_thresholds(sweeps)
    assert thr["strict"] <= thr["balanced"] <= thr["light"]
    thr2, notes = C.pick_thresholds({"cats": _rows(lambda t: 0.5)})
    assert thr2["light"] == thr2["balanced"] == thr2["strict"] == C.GRID[-1]
    assert len(notes) == 3


def test_lookalike_extras_needs_two_screens():
    labels = [
        {"image": "a.png", "clean": True, "boxes": [], "lookalikes": ["dog", "fox"]},
        {"image": "b.png", "clean": True, "boxes": [], "lookalikes": ["dog"]},
        {
            "image": "c.png",
            "clean": False,
            "boxes": [{"concept": "cats", "rect": rect()}],
            "lookalikes": ["dog"],
        },
    ]
    out = C.lookalike_extras(labels, {"cats": {"a.png", "b.png", "c.png"}})
    assert out["cats"] == ["a dog"]  # fox on 1 screen only; c has a real cat so it does not count


def test_decision_block_replaced_not_duplicated(tmp_path: Path):
    f = tmp_path / "decisions.md"
    f.write_text(
        "# Decisions\n\n## D-001 · One\n\nbody\n\n## D-002 · Two\n\nbody2\n", encoding="utf-8"
    )
    d1 = C.write_decision_block(f, "First", "models: torch", "2026-10-02")
    assert d1 == "D-003"
    # another script appends D-004 after our block; a re-run must keep D-003 and not duplicate
    f.write_text(f.read_text(encoding="utf-8") + "\n## D-004 · Later\n\nlater\n", encoding="utf-8")
    d2 = C.write_decision_block(f, "Second", "models: torch 2", "2026-10-03")
    text = f.read_text(encoding="utf-8")
    assert d2 == "D-003"
    assert text.count(C.BEGIN) == 1 and text.count(C.END) == 1
    assert "Second" in text and "First" not in text
    assert "## D-001 · One" in text and "## D-004 · Later" in text and "body2" in text


def test_test_run_count_and_ordering(tmp_path: Path):
    log = tmp_path / "test-runs.jsonl"
    log.write_text(
        "\n".join(json.dumps({"set": s, "n": 1}) for s in ("synthetic", "synthetic", "real"))
        + "\n",
        encoding="utf-8",
    )
    assert C.count_test_runs("synthetic", log) == 2
    assert C.count_test_runs("public", log) == 0
    ok = {
        m: {"cats": {"recall": r, "cleanFalseCover": c}}
        for m, r, c in (("light", 0.5, 0.0), ("balanced", 0.7, 0.04), ("strict", 0.9, 0.1))
    }
    assert C.check_ordering(ok) == []
    ok["strict"]["cats"]["recall"] = 0.6
    assert len(C.check_ordering(ok)) == 1


def test_compare_ignores_timing_and_tolerance():
    a = {
        "chosenVariant": "A",
        "dev": {"x": 0.50},
        "variants": {"secPerScreen": 1.0},
        "test": {"y": 1},
    }
    b = {"chosenVariant": "A", "dev": {"x": 0.504}, "variants": {"secPerScreen": 9.0}, "test": None}
    assert C.compare_results(a, b) == []
    b["dev"]["x"] = 0.51
    assert len(C.compare_results(a, b)) == 1


def _stub_results():
    sc = lambda r, f: {"recall": r, "precision": 0.9, "cleanFalseCover": f}  # noqa: E731
    return {
        "set": "synthetic",
        "generatedUtc": "2026-10-02T00:00:00Z",
        "chosenVariant": "C",
        "variants": {
            "rows": [
                {
                    "variant": "C",
                    "concept": "cats",
                    "recall": 0.9,
                    "precision": 0.9,
                    "cleanFalseCover": 0.04,
                    "t": 0.5,
                    "secPerScreen": 1.2,
                    "note": "",
                }
            ],
            "chosen": "C",
            "reason": "best recall at <=5% false-cover",
        },
        "calibration": C.calibration_doc("synthetic", "C", {"cats": {"calibrationOffset": 0.1}}),
        "thresholds": C.thresholds_doc({"light": 0.7, "balanced": 0.5, "strict": 0.3}),
        "thresholdNotes": [],
        "dev": {
            "light": {"cats": sc(0.5, 0.0)},
            "balanced": {"cats": sc(0.8, 0.04)},
            "strict": {"cats": sc(0.9, 0.1)},
        },
        "examples": {
            "concept": "cats",
            "n": 4,
            "gain": 0.05,
            "recallOff": 0.8,
            "recallOn": 0.85,
            "exampleThreshold": 0.8,
            "kept": True,
            "note": "indicative",
        },
        "newWord": {
            "word": "snakes",
            "cardValid": True,
            "compiledValid": True,
            "endToEnd": True,
            "scores": {"covers": 2, "cleanFalseCover": 0.0, "recall": None},
            "note": "",
        },
        "listSwitch": {
            "result": "PASS",
            "sequence": "cats -> spiders",
            "sameInstances": True,
            "sameWeights": True,
            "finderTest": "pass",
        },
        "test": None,
        "successes": [{"image": "a.png", "concept": "cats", "reason": "covered (photo)"}],
        "failures": [{"image": "b.png", "concept": "cats", "reason": "missed (cartoon)"}],
        "models": {
            "torch": "2.14.1 (CPU)",
            "transformers": "5.18.0",
            "ultralytics": "8.4.171",
            "siglip2HfCommit": "abc",
            "yoloeFile": "yoloe-26s-seg.pt",
            "yoloeSha256": "ff",
            "spaceIds": {"describer": "siglip2-base-p16-224", "finder": "yoloe-26s-mobileclip2"},
            "licences": R.LICENCES,
        },
    }


def test_report_headings_decision_and_check(tmp_path: Path):
    res = _stub_results()
    (tmp_path / "results.json").write_text(json.dumps(res), encoding="utf-8")
    (tmp_path / "calibration.json").write_text(json.dumps(res["calibration"]), encoding="utf-8")
    (tmp_path / "thresholds.json").write_text(json.dumps(res["thresholds"]), encoding="utf-8")
    (tmp_path / "report.md").write_text(R.render_report(res, {}), encoding="utf-8")
    title, body = R.render_decision(res)
    C.write_decision_block(tmp_path / "decisions.md", title, body, "2026-10-02")
    problems = C.check_outputs(
        "synthetic",
        tmp_path / "results.json",
        tmp_path / "calibration.json",
        tmp_path / "thresholds.json",
        tmp_path / "report.md",
        tmp_path / "decisions.md",
        tmp_path / "none.jsonl",
    )
    assert problems == []
    assert "PENDING-HUMAN" in (tmp_path / "report.md").read_text(encoding="utf-8")


def test_successes_failures():
    labels = [
        {
            "image": "a.png",
            "clean": False,
            "boxes": [{"concept": "cats", "rect": rect(), "kind": "photo"}],
        },
        {
            "image": "b.png",
            "clean": False,
            "boxes": [{"concept": "cats", "rect": rect(), "kind": "cartoon"}],
        },
        {"image": "c.png", "clean": True, "boxes": [], "lookalikes": ["dog"]},
    ]
    hide = lambda r: {"decision": "hide", "rect": r}  # noqa: E731
    findings = {"cats": {"a.png": [hide(rect())], "c.png": [hide(rect(50, 50))]}}
    succ, fail = C.successes_failures(labels, findings, hits_stub)
    assert [x["image"] for x in succ] == ["a.png"]
    reasons = {x["image"]: x["reason"] for x in fail}
    assert "missed (cartoon)" in reasons["b.png"]
    assert "clean screen" in reasons["c.png"] and "dog" in reasons["c.png"]
