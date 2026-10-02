"""Export the YOLOE-26s finder and the MobileCLIP2-B text encoder to ONNX (SPEC 3.1.2).

    python -m workshop.forge.yoloe.export [--out data/forge/yoloe]

HEAVY: loads the 254 MB text encoder. Run through `tools\verify\3.1.2.ps1 -Heavy`.
"""

from __future__ import annotations

import argparse
import contextlib
import json
import os
from pathlib import Path

import numpy as np

os.environ["YOLO_AUTOINSTALL"] = "False"

from workshop.forge.common import (  # noqa: E402
    FORGE_DATA,
    FORGE_SRC,
    OPSET,
    REPO,
    sha256_file,
    shape_report,
    write_checksums,
    write_manifest,
)
from workshop.forge.yoloe.wrapper import IMGSZ, N_PROMPTS, EmbedWrapper, TextWrapper  # noqa: E402

MODELS = REPO / "data" / "models"
WEIGHTS = "yoloe-26s-seg.pt"
HERE = FORGE_SRC / "yoloe"
FINDER_FILE = "yoloe-26s-embed-top100.onnx"
TEXT_FILE = "mobileclip2-b-text.onnx"
FINDER_ID = "yoloe-26s-embed-top100"
TEXT_ID = "mobileclip2-b-text"
SPACE_ID = "yoloe-26s-mobileclip2-b"
OUTPUTS = ["boxes", "objectness", "fingerprint", "fp_scale", "fp_bias"]


def load_model():
    """(YOLOE model, its YOLOEModel) unfused, eval, text encoder cached after get_text_pe."""
    from ultralytics import YOLOE

    with contextlib.chdir(MODELS):
        yolo = YOLOE(str(MODELS / WEIGHTS))
    return yolo.model.eval()


def text_pe(model, texts: list[str]):
    with contextlib.chdir(MODELS):
        return model.get_text_pe(list(texts), cache_clip_model=True)


def _export(module, args, path: Path, inputs: list[str], outputs: list[str]) -> str:
    """torch.onnx.export at OPSET, no dynamic axes. TorchScript exporter first, then dynamo."""
    import torch

    errors = []
    for dynamo in (False, True):
        try:
            with torch.inference_mode(False), torch.no_grad():
                torch.onnx.export(
                    module,
                    args,
                    str(path),
                    opset_version=OPSET,
                    input_names=inputs,
                    output_names=outputs,
                    dynamo=dynamo,
                )
            return "dynamo" if dynamo else "torchscript"
        except Exception as e:  # noqa: BLE001  (report, then try the next exporter)
            errors.append(f"dynamo={dynamo}: {type(e).__name__}: {str(e)[:300]}")
    raise RuntimeError(" | ".join(errors))


def _manifest(model_id, name, task, onnx: Path, report: dict, **extra) -> dict:
    spec = lambda s: {"name": s["name"], "shape": s["shape"], "dtype": s["dtype"]}  # noqa: E731
    return {
        "contractVersion": "1.0",
        "modelId": model_id,
        "name": name,
        "version": "26s-embed-1",
        "task": task,
        "inputs": [spec(s) for s in report["inputs"]],
        "outputs": [spec(s) for s in report["outputs"]],
        "precision": "float32",
        "runtime": "onnxruntime-cpu",
        "batch": 1,
        "file": {
            "path": onnx.resolve().relative_to(REPO).as_posix(),
            "sha256": sha256_file(onnx),
            "bytes": onnx.stat().st_size,
        },
        **extra,
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(FORGE_DATA / "yoloe"))
    out = Path(ap.parse_args(argv).out)
    out.mkdir(parents=True, exist_ok=True)
    import torch

    model = load_model()
    vocab = list(__import__("workshop.twin.finder", fromlist=["x"]).PROPOSAL_VOCAB)
    pe_np = text_pe(model, vocab).float().cpu().numpy().copy()  # (1,8,512): reprta + L2 applied
    assert pe_np.shape == (1, N_PROMPTS, 512), pe_np.shape
    np.save(HERE / "proposal_pe.npy", pe_np[0])
    pe = torch.from_numpy(pe_np)

    old = {}
    cs = HERE / "checksums.sha256"
    if cs.is_file():
        old = {r.split("  ", 1)[1]: r.split("  ", 1)[0] for r in cs.read_text().splitlines() if r}

    meta: dict = {"finderExporter": None, "text": None}
    wrapper = EmbedWrapper(model)
    finder_path = out / FINDER_FILE
    x = torch.rand(1, 3, IMGSZ, IMGSZ)
    meta["finderExporter"] = _export(
        wrapper, (x, pe), finder_path, ["images", "proposal_pe"], OUTPUTS
    )
    files = [finder_path]
    manifests = [
        (
            _manifest(
                FINDER_ID,
                "YOLOE-26s object finder (boxes + fingerprints, top-100)",
                "objectFinder",
                finder_path,
                shape_report(finder_path),
                preprocessing={
                    "kind": "image",
                    "resizeWidth": IMGSZ,
                    "resizeHeight": IMGSZ,
                    "resizeMode": "letterbox",
                    "colorOrder": "RGB",
                    "layout": "NCHW",
                    "scale": 1 / 255,
                },
                fingerprint={
                    "spaceId": SPACE_ID,
                    "dim": 512,
                    "role": "region",
                    "pairedWith": TEXT_ID,
                },
                sourceUrl="https://github.com/ultralytics/ultralytics",
                licence="AGPL-3.0",
                notes=(
                    "proposal_pe (1,8,512) is fed by the app. "
                    "Concept score = sigmoid(fp_scale*cos(fingerprint, text)+fp_bias)."
                ),
            ),
            "finder",
        )
    ]
    text_path = out / TEXT_FILE
    try:
        tw = TextWrapper(model.clip_model.encoder, model.model[-1].reprta).eval()
        ids = model.clip_model.tokenize(["a photo of a cat"])
        meta["text"] = "ok:" + _export(tw, (ids,), text_path, ["input_ids"], ["fingerprint"])
        files.append(text_path)
        manifests.append(
            (
                _manifest(
                    TEXT_ID,
                    "MobileCLIP2-B text encoder (YOLOE text branch)",
                    "textEmbedding",
                    text_path,
                    shape_report(text_path),
                    preprocessing={"kind": "text", "tokenizer": "clip-bpe", "maxTokens": 77},
                    fingerprint={
                        "spaceId": SPACE_ID,
                        "dim": 512,
                        "role": "text",
                        "pairedWith": FINDER_ID,
                    },
                    sourceUrl="https://github.com/apple/ml-mobileclip",
                    licence="Apple ML research (verify)",
                    notes="Apple ML research licence (research only; verify).",
                ),
                "text",
            )
        )
    except Exception as e:  # noqa: BLE001
        meta["text"] = f"BLOCKED: {str(e)[:600]}"
        print("TEXT ENCODER BLOCKED:", meta["text"])

    write_checksums("yoloe", files)
    new = {r.split("  ", 1)[1]: r.split("  ", 1)[0] for r in cs.read_text().splitlines() if r}
    meta["changedVsPrevious"] = sorted(k for k in new if k in old and old[k] != new[k])
    for m, _ in manifests:
        write_manifest(m, "yoloe")
    (HERE / "export_meta.json").write_text(json.dumps(meta, indent=2) + "\n", encoding="utf-8")
    print("export done:", meta)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
