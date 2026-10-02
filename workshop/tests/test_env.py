"""Checks that the pinned Python environment is the one the project expects."""

from __future__ import annotations

import importlib.metadata
import sys
import tomllib
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]


def test_python_is_311() -> None:
    assert sys.version_info[:2] == (3, 11)


def test_main_pins_installed() -> None:
    pyproject = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    dependencies = pyproject["project"]["dependencies"]
    assert dependencies, "pyproject.toml lists no dependencies"
    for dependency in dependencies:
        name, version = (part.strip() for part in dependency.split("=="))
        assert importlib.metadata.version(name) == version, name


def test_onnxruntime_runs_tiny_model() -> None:
    import onnx
    import onnxruntime
    from onnx import TensorProto, helper

    a_info = helper.make_tensor_value_info("a", TensorProto.FLOAT, [1, 4])
    b_info = helper.make_tensor_value_info("b", TensorProto.FLOAT, [1, 4])
    y_info = helper.make_tensor_value_info("y", TensorProto.FLOAT, [1, 4])
    node = helper.make_node("Add", ["a", "b"], ["y"])
    graph = helper.make_graph([node], "tiny_add", [a_info, b_info], [y_info])
    model = helper.make_model(graph, opset_imports=[helper.make_opsetid("", 17)], ir_version=10)
    onnx.checker.check_model(model)

    session = onnxruntime.InferenceSession(
        model.SerializeToString(), providers=["CPUExecutionProvider"]
    )
    a = np.array([[1.0, 2.0, 3.0, 4.0]], dtype=np.float32)
    b = np.array([[0.5, -1.0, 10.0, 0.0]], dtype=np.float32)
    (y,) = session.run(None, {"a": a, "b": b})
    np.testing.assert_array_equal(y, a + b)


def test_opencv_and_pillow() -> None:
    import cv2
    from PIL import Image

    img = np.zeros((8, 8, 3), np.uint8)
    assert cv2.cvtColor(img, cv2.COLOR_BGR2GRAY).shape == (8, 8)
    assert Image.fromarray(img).size == (8, 8)
