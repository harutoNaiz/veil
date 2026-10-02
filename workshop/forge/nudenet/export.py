"""Fix NudeNet graph shapes and save nudenet-320n.onnx / nudenet-640m.onnx."""

from __future__ import annotations

from pathlib import Path

import onnx

from workshop.forge import common
from workshop.forge.nudenet.fetch import SRC

MODELS = {"320n": 320, "640m": 640}
URL = "https://github.com/notAI-tech/NudeNet"
OUT = common.FORGE_DATA / "nudenet"


def _set_dims(t: onnx.ValueInfoProto, dims: list[int]) -> None:
    for d, v in zip(t.type.tensor_type.shape.dim, dims, strict=True):
        d.ClearField("dim_param")
        d.dim_value = v


def _probe_output_dims(model: onnx.ModelProto, size: int) -> dict[str, list[int]]:
    """Output shapes from one zero-input CPU run at the fixed input size."""
    import numpy as np
    import onnxruntime as ort

    sess = ort.InferenceSession(model.SerializeToString(), providers=["CPUExecutionProvider"])
    x = np.zeros((1, 3, size, size), dtype=np.float32)
    outs = sess.run(None, {sess.get_inputs()[0].name: x})
    return {o.name: list(a.shape) for o, a in zip(sess.get_outputs(), outs, strict=True)}


def export_one(name: str, size: int) -> Path:
    model = onnx.load(str(SRC / f"{name}.onnx"))
    if any(n.op_type == "NonMaxSuppression" for n in model.graph.node):
        raise SystemExit(f"{name}: in-graph NMS present; not supported by this export")
    _set_dims(model.graph.input[0], [1, 3, size, size])
    del model.graph.value_info[:]
    out_dims = _probe_output_dims(model, size)
    for t in model.graph.output:
        _set_dims(t, out_dims[t.name])
    opset = next((o.version for o in model.opset_import if o.domain in ("", "ai.onnx")), 0)
    if not common.OPSET_RANGE[0] <= opset <= common.OPSET_RANGE[1]:
        from onnx import version_converter

        model = version_converter.convert_version(model, common.OPSET)
    onnx.checker.check_model(model)
    OUT.mkdir(parents=True, exist_ok=True)
    dst = OUT / f"nudenet-{name}.onnx"
    onnx.save(model, str(dst))
    return dst


def _tensors(specs: list[dict]) -> list[dict]:
    return [{"name": s["name"], "shape": list(s["shape"]), "dtype": s["dtype"]} for s in specs]


def manifest(path: Path, name: str, size: int) -> dict:
    rep = common.shape_report(path)
    return {
        "contractVersion": "1.0",
        "modelId": f"nudenet-{name}",
        "name": f"NudeNet {name}",
        "version": "3.4",
        "task": "nsfwDetector",
        "inputs": _tensors(rep["inputs"]),
        "outputs": _tensors(rep["outputs"]),
        "preprocessing": {
            "kind": "image",
            "resizeWidth": size,
            "resizeHeight": size,
            "resizeMode": "letterbox",
            "colorOrder": "RGB",
            "layout": "NCHW",
            "scale": 1 / 255,
        },
        "precision": "float32",
        "runtime": "onnxruntime-cpu",
        "batch": 1,
        "file": {
            "path": f"data/forge/nudenet/{path.name}",
            "sha256": common.sha256_file(path),
            "bytes": path.stat().st_size,
        },
        "sourceUrl": URL,
        "licence": "AGPL-3.0 (verify)",
        "notes": "Decoding and NMS in app code (workshop/forge/nudenet/decode.py).",
    }


def main() -> None:
    files = []
    for name, size in MODELS.items():
        dst = export_one(name, size)
        files.append(dst)
        common.write_manifest(manifest(dst, name, size), "nudenet")
    common.write_checksums("nudenet", files)
    print("exported", [f.name for f in files])


if __name__ == "__main__":
    main()
