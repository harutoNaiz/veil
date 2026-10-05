import json

import onnx
from onnx import TensorProto, helper

from workshop.forge.phone.manifests import write_manifest


def test_manifest_schema(tmp_path):
    x = helper.make_tensor_value_info("x", TensorProto.FLOAT, ["N", 3])
    ids = helper.make_tensor_value_info("ids", TensorProto.INT64, [1, 4])
    y = helper.make_tensor_value_info("y", TensorProto.FLOAT, ["N", 3])
    graph = helper.make_graph([helper.make_node("Identity", ["x"], ["y"])], "g", [x, ids], [y])
    path = tmp_path / "tiny.onnx"
    onnx.save(helper.make_model(graph), str(path))
    doc = json.loads(write_manifest(path).read_text(encoding="utf-8"))
    assert doc["inputs"] == [
        {"name": "x", "shape": [1, 3], "dtype": "float32"},
        {"name": "ids", "shape": [1, 4], "dtype": "int64"},
    ]
    assert doc["outputs"][0]["shape"] == [1, 3]
