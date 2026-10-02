"""AC-3.1-02 parity: exported SigLIP2 ONNX vs the laptop torch model. HEAVY (loads real weights).

Run: python -m workshop.forge.siglip2.parity
"""

from __future__ import annotations

import os
import sys
from datetime import UTC, datetime
from pathlib import Path

os.environ.setdefault("HF_HUB_OFFLINE", "1")

import numpy as np  # noqa: E402

from workshop.forge import common  # noqa: E402

N_CROPS = 200
N_PROMPTS = 100
WORDS = [
    "cats", "spiders", "dogs", "bicycles", "flowers", "birds", "cars", "horses", "trees",
    "boats", "snakes", "clocks", "rabbits", "fish", "tigers", "buses", "roses", "bees",
    "frogs", "motorcycles", "guitars", "mountains", "cows", "elephants", "lions", "owls",
]  # fmt: skip
SOURCE_URL = "https://huggingface.co/google/siglip2-base-patch16-224"


def judge_images(cos: np.ndarray) -> dict:
    """Image rule: mean >= 0.98 and the mean of the worst 5% >= 0.95."""
    cos = np.sort(np.asarray(cos, dtype=np.float64))
    k = max(1, int(np.ceil(0.05 * len(cos))))
    return {"mean": float(cos.mean()), "worst5": float(cos[:k].mean()), "min": float(cos[0])}


def prompts(n: int = N_PROMPTS) -> list[str]:
    from workshop.twin.teacher import concept_card

    seen: list[str] = []
    for w in WORDS:
        card = concept_card(w)
        for p in [*card["looksLike"], *card["butNot"]]:
            if p not in seen:
                seen.append(p)
    return seen[:n]


def crops(n: int = N_CROPS):
    from PIL import Image

    from workshop.twin import data
    from workshop.twin.pieces import crop, make_pieces

    out = []
    for set_name in ("public", "synthetic"):
        for screen in data.load_split(set_name, "dev"):
            img = Image.open(screen.image).convert("RGB")
            for r in make_pieces(img):
                out.append(crop(img, r["rect"]))
                if len(out) >= n:
                    return out
    return out


def _hf_revision() -> str:
    try:
        from huggingface_hub import snapshot_download

        return Path(snapshot_download("google/siglip2-base-patch16-224")).name
    except Exception:
        return ""


def run(folder: Path) -> dict:
    import onnx
    import onnxruntime
    import torch
    import transformers

    from workshop.forge.siglip2.runtime import OnnxDescriber
    from workshop.twin.describer import Describer

    ref = Describer()
    ox = OnnxDescriber(folder)
    imgs = crops()
    texts = prompts()
    checks = []
    ref_img = ref.embed_images(imgs)
    for b in (1, 4, 16):
        got = ox.embed_images(imgs, batch=b)
        j = judge_images(common.cosine_rows(ref_img, got))
        ok = j["mean"] >= 0.98 and j["worst5"] >= 0.95
        checks.append(
            {
                "id": f"AC-3.1-02.image.b{b}.mean",
                "value": j["mean"],
                "threshold": ">= 0.98",
                "n": len(imgs),
                "pass": j["mean"] >= 0.98,
                "note": "",
            }
        )
        checks.append(
            {
                "id": f"AC-3.1-02.image.b{b}.worst5",
                "value": j["worst5"],
                "threshold": ">= 0.95",
                "n": len(imgs),
                "pass": ok and j["worst5"] >= 0.95,
                "note": f"min {j['min']:.6f}",
            }
        )
    tc = common.cosine_rows(ref.embed_texts(texts), ox.embed_texts(texts))
    checks.append(
        {
            "id": "AC-3.1-02.text.min",
            "value": float(tc.min()),
            "threshold": ">= 0.999",
            "n": len(texts),
            "pass": bool(tc.min() >= 0.999),
            "note": f"mean {float(tc.mean()):.6f}",
        }
    )
    files = []
    for f in sorted(Path(folder).glob("*.onnx")):
        rep = common.shape_report(f)
        files.append(
            {
                "path": common._rel(f),
                "sha256": common.sha256_file(f),
                "bytes": f.stat().st_size,
                "opset": rep["opset"],
                "fixed": rep["fixed"],
                "inputs": rep["inputs"],
                "outputs": rep["outputs"],
            }
        )
    return {
        "model": "siglip2",
        "subPhase": "3.1.1",
        "created": datetime.now(UTC).isoformat(timespec="seconds"),
        "tools": {
            "torch": torch.__version__,
            "transformers": transformers.__version__,
            "onnx": onnx.__version__,
            "onnxruntime": onnxruntime.__version__,
        },
        "source": {"url": SOURCE_URL, "licence": "Apache-2.0", "revision": _hf_revision()},
        "files": files,
        "checks": checks,
        "nondeterminism": "",
        "pass": all(c["pass"] for c in checks) and all(f["fixed"] for f in files),
    }


def main(argv: list[str] | None = None) -> int:
    folder = common.FORGE_DATA / "siglip2"
    rep = run(folder)
    out = common.write_report("siglip2", rep)
    for c in rep["checks"]:
        print(f"{'ok  ' if c['pass'] else 'FAIL'} {c['id']} = {c['value']:.6f} ({c['threshold']})")
    print("report", out, "pass" if rep["pass"] else "FAIL")
    return 0 if rep["pass"] else 1


if __name__ == "__main__":
    sys.exit(main())
