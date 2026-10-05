"""Write <id>.manifest.json next to every exported .onnx under data/forge (phone loader schema)."""

from __future__ import annotations

import json
from pathlib import Path

import onnx

ROOT = Path(__file__).resolve().parents[3]
FORGE = ROOT / "data" / "forge"
DTYPES = {1: "float32", 10: "float16", 7: "int64", 6: "int32"}


def _io(values) -> list[dict]:
    out = []
    for v in values:
        t = v.type.tensor_type
        dims = [d.dim_value if d.dim_value > 0 else 1 for d in t.shape.dim]
        out.append({"name": v.name, "shape": dims, "dtype": DTYPES[t.elem_type]})
    return out


def write_manifest(path: Path) -> Path:
    model = onnx.load(str(path), load_external_data=False)
    init = {i.name for i in model.graph.initializer}
    inputs = [i for i in model.graph.input if i.name not in init]
    doc = {"inputs": _io(inputs), "outputs": _io(model.graph.output)}
    dest = path.with_name(path.stem + ".manifest.json")
    dest.write_text(json.dumps(doc, indent=2) + "\n", encoding="utf-8")
    return dest


def main(root: Path = FORGE) -> int:
    n = 0
    for p in sorted(root.rglob("*.onnx")):
        write_manifest(p)
        n += 1
    print(f"wrote {n} manifests under {root}")
    return 0 if n else 1


if __name__ == "__main__":
    raise SystemExit(main())
