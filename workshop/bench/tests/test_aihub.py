from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import onnx
import onnxruntime as ort
import pytest

from workshop.bench import aihub


def test_make_tiny_onnx_is_valid_and_runs(tmp_path: Path) -> None:
    path = tmp_path / "tiny.onnx"
    aihub.make_tiny_onnx(path)
    model = onnx.load(str(path))
    onnx.checker.check_model(model)
    assert model.ir_version == 10
    assert model.opset_import[0].version == 17
    session = ort.InferenceSession(str(path), providers=["CPUExecutionProvider"])
    x = np.random.default_rng(1).standard_normal((1, 3, 32, 32)).astype(np.float32)
    (y,) = session.run(None, {"x": x})
    assert y.shape == (1, 8, 32, 32)
    assert float(y.min()) >= 0.0  # Relu


def test_make_tiny_onnx_is_deterministic(tmp_path: Path) -> None:
    aihub.make_tiny_onnx(tmp_path / "a.onnx")
    aihub.make_tiny_onnx(tmp_path / "b.onnx")
    assert (tmp_path / "a.onnx").read_bytes() == (tmp_path / "b.onnx").read_bytes()


def test_family_regex() -> None:
    assert aihub.FAMILY_RE.search("chipset:qualcomm-snapdragon-8-elite-gen5")
    assert aihub.FAMILY_RE.search("Snapdragon 8 Elite Gen 5 for Galaxy")
    assert aihub.FAMILY_RE.search("SM8850-AD")
    assert not aihub.FAMILY_RE.search("chipset:qualcomm-snapdragon-8gen3")
    assert not aihub.FAMILY_RE.search("Samsung Galaxy S24")


def test_family_devices_matches_name_or_attributes(monkeypatch: pytest.MonkeyPatch) -> None:
    devices = [
        SimpleNamespace(
            name="Samsung Galaxy S26 (Family)",
            attributes=["chipset:qualcomm-snapdragon-8-elite-gen5"],
        ),
        SimpleNamespace(name="Snapdragon 8 Elite Gen 5 QRD", attributes=[]),
        SimpleNamespace(
            name="Samsung Galaxy S24", attributes=["chipset:qualcomm-snapdragon-8gen3"]
        ),
        SimpleNamespace(
            name="Samsung Galaxy S26 (Family)",
            attributes=["chipset:qualcomm-snapdragon-8-elite-gen5"],
        ),
    ]
    monkeypatch.setitem(sys.modules, "qai_hub", SimpleNamespace(get_devices=lambda: devices))
    assert aihub.family_devices() == ["Samsung Galaxy S26 (Family)", "Snapdragon 8 Elite Gen 5 QRD"]


def test_is_configured_follows_the_ini_path(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    ini = tmp_path / "client.ini"
    monkeypatch.setenv("QAIHUB_CLIENT_INI", str(ini))
    assert not aihub.is_configured()
    ini.write_text("[api]\n", encoding="utf-8")
    assert aihub.is_configured()
