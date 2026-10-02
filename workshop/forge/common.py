"""Shared helpers for the model exports (3.1): hashing, shape checks, checksums, manifests, reports.

Imported by every forge sub-package. Cheap to import: onnx is loaded inside the functions.
"""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parents[2]
FORGE_DATA = REPO / "data" / "forge"
FORGE_SRC = REPO / "workshop" / "forge"
OPSET = 17
OPSET_RANGE = (17, 20)

_DTYPES = {
    1: "float32",
    2: "uint8",
    3: "int8",
    4: "uint16",
    5: "int16",
    6: "int32",
    7: "int64",
    9: "bool",
    10: "float16",
}


def sha256_file(p: Path) -> str:
    h = hashlib.sha256()
    with open(p, "rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def _spec(vi) -> dict:
    tt = vi.type.tensor_type
    dims: list[int | str | None] = []
    fixed = True
    for d in tt.shape.dim:
        if d.HasField("dim_value") and d.dim_value > 0 and not d.dim_param:
            dims.append(int(d.dim_value))
        else:
            fixed = False
            dims.append(d.dim_param or None)
    if not tt.HasField("shape"):
        fixed = False
    return {
        "name": vi.name,
        "shape": dims,
        "dtype": _DTYPES.get(tt.elem_type, str(tt.elem_type)),
        "fixed": fixed,
    }


def shape_report(onnx_path: Path) -> dict:
    """{"opset", "inputs", "outputs", "fixed"}; fixed = every I/O dim is a positive number."""
    import onnx

    m = onnx.load(str(onnx_path), load_external_data=False)
    init = {i.name for i in m.graph.initializer}
    ins = [_spec(v) for v in m.graph.input if v.name not in init]
    outs = [_spec(v) for v in m.graph.output]
    opset = next((int(o.version) for o in m.opset_import if o.domain in ("", "ai.onnx")), 0)
    fixed = all(s["fixed"] for s in ins + outs) and bool(ins) and bool(outs)
    return {"opset": opset, "inputs": ins, "outputs": outs, "fixed": fixed}


def _rel(p: Path) -> str:
    try:
        return Path(p).resolve().relative_to(REPO).as_posix()
    except ValueError:
        return Path(p).as_posix()


def _checksum_file(model: str) -> Path:
    return FORGE_SRC / model / "checksums.sha256"


def write_checksums(model: str, files: list[Path]) -> Path:
    out = _checksum_file(model)
    out.parent.mkdir(parents=True, exist_ok=True)
    lines = [f"{sha256_file(Path(f))}  {_rel(Path(f))}" for f in sorted(files, key=_rel)]
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return out


def _read_checksums(model: str) -> list[tuple[str, str]]:
    f = _checksum_file(model)
    rows = []
    for line in f.read_text(encoding="utf-8").splitlines():
        if line.strip():
            sha, rel = line.split("  ", 1)
            rows.append((sha, rel))
    return rows


def check_checksums(model: str) -> list[str]:
    """Paths whose sha256 differs from checksums.sha256 or are missing; [] = reproducible."""
    bad = []
    for sha, rel in _read_checksums(model):
        p = REPO / rel
        if not p.is_file() or sha256_file(p) != sha:
            bad.append(rel)
    return bad


def write_manifest(m: dict, model: str) -> Path:
    from workshop.contracts.validate import validate

    validate("ModelManifest", m)
    out = FORGE_SRC / model / "manifests" / f"{m['modelId']}.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(m, indent=2) + "\n", encoding="utf-8")
    return out


def write_report(model: str, report: dict) -> Path:
    out = FORGE_SRC / model / "parity.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    return out


def cosine_rows(a, b) -> np.ndarray:
    a = np.asarray(a, dtype=np.float64)
    b = np.asarray(b, dtype=np.float64)
    num = (a * b).sum(axis=1)
    den = np.maximum(np.linalg.norm(a, axis=1) * np.linalg.norm(b, axis=1), 1e-300)
    return num / den


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    if argv[:1] == ["shapes"] and len(argv) == 2:
        bad = False
        for f in sorted(Path(argv[1]).rglob("*.onnx")):
            r = shape_report(f)
            ok = r["fixed"] and OPSET_RANGE[0] <= r["opset"] <= OPSET_RANGE[1]
            bad |= not ok
            ins = [(s["name"], s["shape"]) for s in r["inputs"]]
            outs = [(s["name"], s["shape"]) for s in r["outputs"]]
            print(f"{'ok' if ok else 'FAIL'} {_rel(f)} opset={r['opset']} in={ins} out={outs}")
        return 1 if bad else 0
    if argv[:1] == ["checksums"]:
        for f in sorted(FORGE_SRC.glob("*/checksums.sha256")):
            for line in f.read_text(encoding="utf-8").splitlines():
                if line.strip():
                    print(line)
        return 0
    print("usage: python -m workshop.forge.common shapes <dir> | checksums", file=sys.stderr)
    return 2


if __name__ == "__main__":
    sys.exit(main())
