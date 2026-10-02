"""Freeze write/check and the tamper tests."""

from __future__ import annotations

import json
from pathlib import Path

from workshop.eval import freeze, split

DOC = "# Datasets\n\n<!-- veil:testset -->\nchecksum: PENDING-HUMAN\n<!-- /veil:testset -->\n"


def _setup(tmp_path: Path, labels: list[dict], screens: Path):
    lp, sp, doc = tmp_path / "l.json", tmp_path / "s.json", tmp_path / "datasets.md"
    lp.write_text(json.dumps(labels))
    sp.write_text(json.dumps(split.split(labels, None, 12)))
    doc.write_text(DOC)
    common = [
        "--screens",
        str(screens),
        "--labels",
        str(lp),
        "--splits",
        str(sp),
        "--doc",
        str(doc),
    ]
    return lp, sp, doc, common


def test_freeze_write_check_and_tamper(tmp_path, labels, screens, capsys):
    lp, sp, doc, common = _setup(tmp_path, labels, screens)
    assert freeze.main(["check", *common]) == 2  # PENDING-HUMAN: nothing to check yet
    assert freeze.main(["write", *common]) == 0
    text = doc.read_text()
    assert "checksum: sha256:" in text and "PENDING-HUMAN" not in text
    assert freeze.main(["check", *common]) == 0
    splits = json.loads(sp.read_text())
    dev_name, test_name = splits["dev"][0], splits["test"][0]
    # Edit a dev label: still ok.
    edited = json.loads(lp.read_text())
    next(x for x in edited if x["image"] == dev_name)["labeller"] = "someone-else"
    lp.write_text(json.dumps(edited))
    assert freeze.main(["check", *common]) == 0
    # Edit a test label: fails.
    next(x for x in edited if x["image"] == test_name)["labeller"] = "someone-else"
    lp.write_text(json.dumps(edited))
    capsys.readouterr()
    assert freeze.main(["check", *common]) == 1
    assert "TEST SET CHANGED" in capsys.readouterr().out
    # Restore the label, tamper one byte of a test PNG: fails.
    next(x for x in edited if x["image"] == test_name)["labeller"] = "synth"
    lp.write_text(json.dumps(edited))
    assert freeze.main(["check", *common]) == 0
    png = screens / test_name
    data = bytearray(png.read_bytes())
    data[-20] ^= 0xFF
    png.write_bytes(bytes(data))
    assert freeze.main(["check", *common]) == 1
