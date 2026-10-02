"""Export SigLIP2 (google/siglip2-base-patch16-224) to fixed-shape float32 ONNX, opset 17.

Run: python -m workshop.forge.siglip2.export --out data/forge/siglip2
Loads the model from the local HF cache only (HF_HUB_OFFLINE=1). HEAVY: needs ~2 GB RAM.
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

os.environ.setdefault("HF_HUB_OFFLINE", "1")

from workshop.forge import common  # noqa: E402

HF_ID = "google/siglip2-base-patch16-224"
SOURCE_URL = "https://huggingface.co/google/siglip2-base-patch16-224"
SPACE_ID = "siglip2-base-p16-224"
TEXT_LEN = 64
DIM = 768
BATCHES = (1, 4, 16)


def _wrappers(model):
    import torch
    import torch.nn.functional as F

    def pooled(out):
        return out if hasattr(out, "dtype") else out.pooler_output

    class Image(torch.nn.Module):
        def __init__(self, m):
            super().__init__()
            self.m = m

        def forward(self, pixel_values):
            return F.normalize(pooled(self.m.get_image_features(pixel_values=pixel_values)), dim=-1)

    class Text(torch.nn.Module):
        def __init__(self, m):
            super().__init__()
            self.m = m

        def forward(self, input_ids):
            return F.normalize(pooled(self.m.get_text_features(input_ids=input_ids)), dim=-1)

    return Image(model).eval(), Text(model).eval()


def manifest(task: str, model_id: str, paired: str, file: Path, batch: int, rep: dict) -> dict:
    is_img = task == "imageEmbedding"
    if is_img:
        pre = {
            "kind": "image",
            "resizeWidth": 224,
            "resizeHeight": 224,
            "resizeMode": "stretch",
            "colorOrder": "RGB",
            "layout": "NCHW",
            "scale": 1 / 255,
            "mean": [0.5, 0.5, 0.5],
            "std": [0.5, 0.5, 0.5],
        }
    else:
        pre = {
            "kind": "text",
            "tokenizer": "siglip2 (lower-case, pad to 64)",
            "maxTokens": TEXT_LEN,
        }
    return {
        "contractVersion": "1.0",
        "modelId": model_id,
        "name": "SigLIP2 base patch16 224 " + ("image encoder" if is_img else "text encoder"),
        "version": "1.0",
        "task": task,
        "inputs": [{k: s[k] for k in ("name", "shape", "dtype")} for s in rep["inputs"]],
        "outputs": [{k: s[k] for k in ("name", "shape", "dtype")} for s in rep["outputs"]],
        "preprocessing": pre,
        "fingerprint": {
            "spaceId": SPACE_ID,
            "dim": DIM,
            "role": "image" if is_img else "text",
            "pairedWith": paired,
        },
        "precision": "float32",
        "runtime": "onnxruntime-cpu",
        "batch": batch,
        "file": {
            "path": common._rel(file),
            "sha256": common.sha256_file(file),
            "bytes": file.stat().st_size,
        },
        "sourceUrl": SOURCE_URL,
        "licence": "Apache-2.0",
    }


def write_outputs(files: dict[str, Path]) -> list[Path]:
    """Checksums + one manifest per file. files: {key: path}, key in b1/b4/b16/text."""
    common.write_checksums("siglip2", list(files.values()))
    written = []
    for key, f in files.items():
        rep = common.shape_report(f)
        if key == "text":
            m = manifest("textEmbedding", "siglip2-base-text", "siglip2-base-image", f, 1, rep)
        else:
            mid = f"siglip2-base-image-{key}"
            m = manifest("imageEmbedding", mid, "siglip2-base-text", f, int(key[1:]), rep)
        written.append(common.write_manifest(m, "siglip2"))
    return written


def export(out: Path) -> dict[str, Path]:
    import torch
    from transformers import AutoModel

    out.mkdir(parents=True, exist_ok=True)
    model = AutoModel.from_pretrained(HF_ID, attn_implementation="eager").eval().float()
    img, txt = _wrappers(model)
    files: dict[str, Path] = {}
    with torch.inference_mode():
        for b in BATCHES:
            f = out / f"siglip2-image-b{b}.onnx"
            torch.onnx.export(
                img,
                (torch.zeros(b, 3, 224, 224),),
                str(f),
                input_names=["pixel_values"],
                output_names=["fingerprint"],
                opset_version=common.OPSET,
                dynamo=False,
            )
            files[f"b{b}"] = f
        f = out / "siglip2-text.onnx"
        torch.onnx.export(
            txt,
            (torch.zeros(1, TEXT_LEN, dtype=torch.int64),),
            str(f),
            input_names=["input_ids"],
            output_names=["fingerprint"],
            opset_version=common.OPSET,
            dynamo=False,
        )
        files["text"] = f
    write_outputs(files)
    return files


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", type=Path, default=common.FORGE_DATA / "siglip2")
    a = ap.parse_args(argv)
    for k, f in export(a.out).items():
        print(k, f, common.sha256_file(f))
    return 0


if __name__ == "__main__":
    sys.exit(main())
