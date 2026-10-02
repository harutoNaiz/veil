"""The validator command line."""

from __future__ import annotations

import json

from workshop.contracts.validate import SCHEMA_DIR, main, type_for_path

EXAMPLES = SCHEMA_DIR / "examples"


def test_cli_ok(capsys):
    code = main([str(EXAMPLES / "rect" / "valid-01-basic.json")])
    assert code == 0
    assert capsys.readouterr().out.startswith("OK Rect ")


def test_cli_invalid(capsys):
    code = main([str(EXAMPLES / "mask" / "invalid-01-layer1-peekable.json")])
    assert code == 1
    assert capsys.readouterr().out.startswith("INVALID Mask ")


def test_cli_type_option_and_jsonl(tmp_path, capsys):
    good = json.loads((EXAMPLES / "rect" / "valid-01-basic.json").read_text(encoding="utf-8"))
    path = tmp_path / "rects.jsonl"
    path.write_text(json.dumps(good) + "\n" + json.dumps({"x": 1}) + "\n", encoding="utf-8")
    code = main([str(path), "--type", "Rect", "--jsonl"])
    out = capsys.readouterr().out.splitlines()
    assert code == 1
    assert out[0].startswith("OK Rect ")
    assert out[1].startswith("INVALID Rect ")


def test_type_for_path():
    assert type_for_path(EXAMPLES / "ui-event" / "valid-01-scrolled.json") == "UiEvent"
    sample = EXAMPLES / "model-manifest" / "valid-01-siglip2-image-w8a16.json"
    assert type_for_path(sample) == "ModelManifest"
