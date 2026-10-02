from pathlib import Path

import numpy as np
import onnx
from onnx import TensorProto, helper

from workshop.forge import common


def _model(path: Path, dims, opset: int = 17) -> Path:
    x = helper.make_tensor_value_info("x", TensorProto.FLOAT, dims)
    y = helper.make_tensor_value_info("y", TensorProto.FLOAT, dims)
    g = helper.make_graph([helper.make_node("Relu", ["x"], ["y"])], "g", [x], [y])
    m = helper.make_model(g, opset_imports=[helper.make_opsetid("", opset)])
    onnx.save(m, str(path))
    return path


def test_shape_report_fixed_vs_dynamic(tmp_path):
    fixed = common.shape_report(_model(tmp_path / "a.onnx", [1, 3]))
    assert fixed["fixed"] and fixed["opset"] == 17
    assert fixed["inputs"][0]["shape"] == [1, 3]
    dyn = common.shape_report(_model(tmp_path / "b.onnx", ["batch", 3]))
    assert not dyn["fixed"]


def test_shapes_cli(tmp_path, capsys):
    _model(tmp_path / "a.onnx", [1, 3])
    assert common.main(["shapes", str(tmp_path)]) == 0
    _model(tmp_path / "b.onnx", ["n", 3])
    assert common.main(["shapes", str(tmp_path)]) == 1
    _model(tmp_path / "c.onnx", [1, 3], opset=13)
    (tmp_path / "b.onnx").unlink()
    assert common.main(["shapes", str(tmp_path)]) == 1


def test_checksum_round_trip(tmp_path, monkeypatch):
    monkeypatch.setattr(common, "FORGE_SRC", tmp_path / "src")
    monkeypatch.setattr(common, "REPO", tmp_path)
    f = tmp_path / "data" / "m.bin"
    f.parent.mkdir()
    f.write_bytes(b"hello")
    out = common.write_checksums("zz", [f])
    assert out.read_text().strip().endswith("  data/m.bin")
    assert common.check_checksums("zz") == []
    f.write_bytes(b"other")
    assert common.check_checksums("zz") == ["data/m.bin"]


def test_manifest_validates(tmp_path, monkeypatch):
    import pytest
    from jsonschema import ValidationError

    monkeypatch.setattr(common, "FORGE_SRC", tmp_path)
    from workshop.forge.siglip2.export import manifest

    f = _model(tmp_path / "x.onnx", [1, 3])
    rep = common.shape_report(f)
    m = manifest("imageEmbedding", "siglip2-test", "siglip2-base-text", f, 1, rep)
    assert common.write_manifest(m, "zz").is_file()
    del m["licence"]
    with pytest.raises(ValidationError):
        common.write_manifest(m, "zz")


def test_cosine_rows():
    a = np.array([[1.0, 0.0], [1.0, 1.0]])
    assert np.allclose(common.cosine_rows(a, a), 1.0)
