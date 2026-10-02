"""AC-1.2-05 on the real data: runs only once the human has frozen docs/datasets.md."""

from __future__ import annotations

from pathlib import Path

import pytest

from workshop.eval import freeze

REPO = Path(__file__).resolve().parents[3]
DOC = REPO / "docs" / "datasets.md"
LABELS = REPO / "data" / "labels" / "screens.json"
SPLITS = REPO / "data" / "labels" / "splits.json"


def test_real_test_set_is_unchanged():
    if not DOC.is_file() or "PENDING-HUMAN" in DOC.read_text(encoding="utf-8"):
        pytest.skip("datasets.md says PENDING-HUMAN: real test set not frozen yet")
    if not LABELS.is_file() or not SPLITS.is_file():
        pytest.skip("data/labels/screens.json or splits.json missing")
    args = [
        "check",
        "--screens",
        str(REPO / "data" / "screens"),
        "--labels",
        str(LABELS),
        "--splits",
        str(SPLITS),
        "--doc",
        str(DOC),
    ]
    assert freeze.main(args) == 0
