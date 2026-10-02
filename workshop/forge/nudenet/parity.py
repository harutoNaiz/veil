"""NudeNet parity on HARMLESS images only: original file vs exported file, same decode.

`--l1set <dir>` runs the same check on the human controlled set (report only).
"""

from __future__ import annotations

import argparse
import sys
from datetime import UTC, datetime
from pathlib import Path

import numpy as np
from PIL import Image

from workshop.forge import common
from workshop.forge.nudenet.decode import agreement, decode, letterbox_params
from workshop.forge.nudenet.export import MODELS, OUT, URL
from workshop.forge.nudenet.fetch import SRC

N_IMAGES = 200
THRESHOLD = 0.98
SUFFIXES = {".png", ".jpg", ".jpeg"}


def preprocess(img: Image.Image, size: int) -> tuple[np.ndarray, tuple[float, float, float]]:
    img = img.convert("RGB")
    w, h = img.size
    m = max(w, h)
    canvas = Image.new("RGB", (m, m), (0, 0, 0))
    canvas.paste(img, (0, 0))
    arr = np.asarray(canvas.resize((size, size), Image.BILINEAR), dtype=np.float32) / 255.0
    return arr.transpose(2, 0, 1)[None], letterbox_params(w, h, size)


def agreement_pooled(pairs: list[tuple[list, list]], iou_min: float = 0.5) -> float:
    m = t = 0
    for ref, new in pairs:
        a, b = agreement(ref, new, iou_min)
        m += a
        t += b
    return m / t if t else 1.0


def harmless_paths() -> list[Path]:
    from workshop.twin import data

    paths: list[Path] = []
    for name in ("public", "synthetic"):
        for split in ("dev", "test"):
            try:
                paths += [s.image for s in data.load_split(name, split)]
            except (FileNotFoundError, ValueError):
                pass
    fresh = data.CH1 / "fresh"
    if fresh.is_dir():
        for f in sorted(fresh.iterdir()):
            if f.is_dir():
                paths += [s.image for s in data.load_folder(f)]
    return paths


def build_images(paths: list[Path], n: int = N_IMAGES):
    """Yield n PIL images: originals first, then deterministic flips / crops to top up."""
    if not paths:
        raise SystemExit("no images found")
    for i in range(n):
        p = paths[i % len(paths)]
        k = i // len(paths)
        img = Image.open(p).convert("RGB")
        if k == 1:
            img = img.transpose(Image.FLIP_LEFT_RIGHT)
        elif k >= 2:
            w, h = img.size
            img = img.crop((w // 8 * (k % 3), h // 8 * (k % 3), w, h))
        yield img


def run_model(name: str, size: int, paths: list[Path], n: int) -> dict:
    import onnxruntime as ort

    ref_s = ort.InferenceSession(str(SRC / f"{name}.onnx"), providers=["CPUExecutionProvider"])
    new_s = ort.InferenceSession(
        str(OUT / f"nudenet-{name}.onnx"), providers=["CPUExecutionProvider"]
    )
    pairs = []
    for img in build_images(paths, n):
        x, lb = preprocess(img, size)
        r = ref_s.run(None, {ref_s.get_inputs()[0].name: x})[0]
        c = new_s.run(None, {new_s.get_inputs()[0].name: x})[0]
        pairs.append((decode(r, letterbox=lb), decode(c, letterbox=lb)))
    ag = agreement_pooled(pairs)
    return {"agreement": ag, "n": len(pairs), "pass": ag >= THRESHOLD}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--l1set", type=Path, default=None)
    ap.add_argument("--n", type=int, default=N_IMAGES)
    a = ap.parse_args(argv)
    if a.l1set:
        paths = sorted(p for p in a.l1set.rglob("*") if p.suffix.lower() in SUFFIXES)
        tag = "L1Set"
    else:
        paths = harmless_paths()
        tag = "harmless"
    checks = []
    for name, size in MODELS.items():
        r = run_model(name, size, paths, a.n if not a.l1set else len(paths))
        checks.append(
            {
                "id": f"AC-3.1-05.nudenet-{name}.{tag}.agreement",
                "value": round(r["agreement"], 5),
                "threshold": ">= 0.98",
                "n": r["n"],
                "pass": r["pass"],
                "note": "same class, IoU >= 0.5, pooled; harmless images only"
                if not a.l1set
                else "controlled set (human); positive-class parity",
            }
        )
        print(checks[-1]["id"], checks[-1]["value"], checks[-1]["pass"])
    if a.l1set:
        return 0 if all(c["pass"] for c in checks) else 1
    import onnx
    import onnxruntime

    files = []
    for name in MODELS:
        p = OUT / f"nudenet-{name}.onnx"
        files.append(
            {
                "path": common._rel(p),
                "sha256": common.sha256_file(p),
                "bytes": p.stat().st_size,
                **common.shape_report(p),
            }
        )
    ok = all(c["pass"] for c in checks)
    common.write_report(
        "nudenet",
        {
            "model": "nudenet",
            "subPhase": "3.1.3",
            "created": datetime.now(UTC).isoformat(),
            "tools": {"onnx": onnx.__version__, "onnxruntime": onnxruntime.__version__},
            "source": {"url": URL, "licence": "AGPL-3.0 (verify)", "revision": "v3.4-weights"},
            "files": files,
            "checks": checks,
            "nondeterminism": "",
            "pass": ok,
            "pendingHuman": "positive-class parity on the controlled set (HC-3.1-c)",
        },
    )
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
