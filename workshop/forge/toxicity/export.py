"""Export the chosen toxicity classifier at fixed lengths 128 and 256 (opset 17, float32)."""

from __future__ import annotations

import json
import os
from pathlib import Path

from workshop.forge import common
from workshop.forge.toxicity.fetch import CHOICE

LENGTHS = (128, 256)
OUT = common.FORGE_DATA / "toxicity"


def choice() -> dict:
    return json.loads(CHOICE.read_text(encoding="utf-8"))


def load_model():
    from transformers import AutoModelForSequenceClassification, AutoTokenizer

    mid = choice()["model"]["id"]
    tok = AutoTokenizer.from_pretrained(mid)
    model = AutoModelForSequenceClassification.from_pretrained(mid).eval()
    return tok, model


def export_one(model, length: int) -> Path:
    import torch

    class Wrap(torch.nn.Module):
        def __init__(self, m):
            super().__init__()
            self.m = m

        def forward(self, input_ids, attention_mask):
            return self.m(input_ids=input_ids, attention_mask=attention_mask).logits

    OUT.mkdir(parents=True, exist_ok=True)
    dst = OUT / f"toxicity-seq{length}.onnx"
    ids = torch.ones((1, length), dtype=torch.int64)
    with torch.no_grad():
        torch.onnx.export(
            Wrap(model),
            (ids, ids.clone()),
            str(dst),
            input_names=["input_ids", "attention_mask"],
            output_names=["logits"],
            opset_version=common.OPSET,
            dynamo=False,
        )
    return dst


def manifest(path: Path, length: int, tok_name: str) -> dict:
    rep = common.shape_report(path)
    ch = choice()["model"]
    return {
        "contractVersion": "1.0",
        "modelId": f"toxicity-seq{length}",
        "name": f"Toxicity classifier ({ch['id']}) seq{length}",
        "version": (ch.get("revision") or "unknown")[:12],
        "task": "toxicityClassifier",
        "inputs": [
            {"name": s["name"], "shape": list(s["shape"]), "dtype": s["dtype"]}
            for s in rep["inputs"]
        ],
        "outputs": [
            {"name": s["name"], "shape": list(s["shape"]), "dtype": s["dtype"]}
            for s in rep["outputs"]
        ],
        "preprocessing": {"kind": "text", "tokenizer": tok_name[:100], "maxTokens": length},
        "precision": "float32",
        "runtime": "onnxruntime-cpu",
        "batch": 1,
        "file": {
            "path": f"data/forge/toxicity/{path.name}",
            "sha256": common.sha256_file(path),
            "bytes": path.stat().st_size,
        },
        "sourceUrl": ch["url"],
        "licence": ch["licence"],
        "notes": "Tokenizer and softmax/sigmoid in app code.",
    }


def main() -> None:
    os.environ.setdefault("HF_HUB_OFFLINE", "1")
    tok, model = load_model()
    files = []
    for n in LENGTHS:
        dst = export_one(model, n)
        files.append(dst)
        common.write_manifest(manifest(dst, n, type(tok).__name__), "toxicity")
    common.write_checksums("toxicity", files)
    print("exported", [f.name for f in files])


if __name__ == "__main__":
    main()
