import json
from pathlib import Path

import pytest

from workshop.contracts.validate import validate

HERE = Path(__file__).resolve().parents[1]
SENSITIVE = {
    "spiders": False,
    "needles": True,
    "gore": True,
    "alcohol": True,
    "spoiler-breaking-bad": False,
}


def _pack(pid):
    for d in (HERE, HERE / "rejected"):
        p = d / f"{pid}.json"
        if p.is_file():
            return json.loads(p.read_text("utf-8"))
    raise AssertionError(f"pack {pid} missing")


@pytest.mark.parametrize("pid", SENSITIVE)
def test_pack_valid_and_flagged(pid):
    doc = _pack(pid)
    validate("ConceptPack", doc)
    assert doc["sensitive"] is SENSITIVE[pid]
    for c in doc["concepts"]:
        assert 4 <= len(c["looksLike"]) <= 8
        assert 3 <= len(c["butNot"]) <= 6
        assert 5 <= len(c["keywords"]) <= 15


@pytest.mark.parametrize("pid", SENSITIVE)
def test_report_status(pid):
    r = json.loads((HERE / "reports" / f"{pid}.json").read_text("utf-8"))
    assert r["status"] in {"PASS", "FAIL", "PENDING-HUMAN"}
    assert 0 <= r["recall"] <= 1
    assert (HERE / "rejected" / f"{pid}.json").is_file() == (r["status"] == "FAIL")


@pytest.mark.parametrize("pid", SENSITIVE)
def test_text_sets_size(pid):
    rows = [
        json.loads(x) for x in (HERE / "text_sets" / f"{pid}.jsonl").read_text("utf-8").splitlines()
    ]
    assert sum(r["label"] == 1 for r in rows) >= 20
    assert sum(r["label"] == 0 for r in rows) >= 40
