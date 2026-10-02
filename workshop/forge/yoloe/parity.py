"""Parity of the exported YOLOE finder and text encoder against Ultralytics (SPEC 3.1.2).

python -m workshop.forge.yoloe.parity     (HEAVY; writes workshop/forge/yoloe/parity.json)
"""

from __future__ import annotations

import json
import os
from datetime import UTC, datetime
from pathlib import Path

import numpy as np
from PIL import Image

os.environ["YOLO_AUTOINSTALL"] = "False"

from workshop.forge.common import (  # noqa: E402
    FORGE_DATA,
    FORGE_SRC,
    REPO,
    cosine_rows,
    sha256_file,
    shape_report,
    write_report,
)
from workshop.forge.yoloe.runtime import (  # noqa: E402
    FINDER_FILE,
    TEXT_FILE,
    OnnxFinder,
    concept_score,
    iou_matrix,
    letterbox_tensor,
    pad_prompts,
)
from workshop.twin.finder import PROPOSAL_VOCAB  # noqa: E402

CAP = 60
REF_CONF = 0.05
IOU_MIN = 0.95
DSCORE_MAX = 0.02
NORM_TOL = 0.001
TEXT_COS_MIN = 0.999
LISTS = {
    "proposal": list(PROPOSAL_VOCAB),
    "list1": ["cat", "spider"],
    "list2": ["bicycle", "dog", "flower"],
}
WORDS = (
    "cats spiders dogs bicycles flowers birds cars trees houses horses fish boats clocks "
    "shoes hats cups books chairs lamps bananas apples bears rabbits snakes turtles"
).split()


def screens() -> list[Path]:
    from workshop.twin.data import load_split

    out: list[Path] = []
    for name in ("public", "synthetic"):
        try:
            out += [s.image for s in load_split(name, "dev")]
        except FileNotFoundError:
            pass
    return out[:CAP]


def text_prompts(n: int = 100) -> list[str]:
    from workshop.twin.teacher import concept_card

    seen: list[str] = []
    for w in WORDS:
        c = concept_card(w)
        for p in [*c["looksLike"], *c["butNot"]]:
            if p not in seen:
                seen.append(p)
    return seen[:n]


def _tools() -> dict:
    import onnx
    import onnxruntime
    import torch
    import ultralytics

    return {
        "torch": torch.__version__,
        "ultralytics": ultralytics.__version__,
        "onnx": onnx.__version__,
        "onnxruntime": onnxruntime.__version__,
    }


def compare(ref: np.ndarray, onnx_out: list[np.ndarray], pe_norm: np.ndarray) -> dict:
    """ref (k,6) [xyxy, conf, cls] vs one graph run (batch dim dropped). Keeps conf >= REF_CONF."""
    boxes, _obj, fp, scale, bias = (a[0] for a in onnx_out)
    r = ref[ref[:, 4] >= REF_CONF]
    res = {"ref": len(r), "matched": 0, "minIou": 1.0, "maxDScore": 0.0}
    if len(r):
        ious = iou_matrix(r[:, :4], boxes)
        scores = concept_score(fp, scale, bias, pe_norm)  # (100, n_prompts)
        for i, row in enumerate(r):
            j = int(np.argmax(ious[i]))
            d = abs(float(scores[j, int(row[5])]) - float(row[4]))
            res["minIou"] = min(res["minIou"], float(ious[i, j]))
            res["maxDScore"] = max(res["maxDScore"], d)
            res["matched"] += int(ious[i, j] > IOU_MIN and d < DSCORE_MAX)
    res["normErr"] = float(np.abs(np.linalg.norm(fp, axis=1) - 1).max())
    return res


def main() -> int:
    import torch

    from workshop.forge.yoloe.export import load_model, text_pe

    data = FORGE_DATA / "yoloe"
    meta_p = FORGE_SRC / "yoloe" / "export_meta.json"
    meta = json.loads(meta_p.read_text()) if meta_p.is_file() else {}
    model = load_model()
    model.model[-1].end2end = True  # the one2one branch, as exported
    pes = {k: text_pe(model, v).float().cpu().numpy().copy() for k, v in LISTS.items()}
    runner = OnnxFinder(data)
    zero = {"ref": 0, "matched": 0, "minIou": 1.0, "maxDScore": 0.0, "normErr": 0.0}
    agg = {k: dict(zero) for k in LISTS}
    imgs = screens()
    for path in imgs:
        x = letterbox_tensor(Image.open(path))
        xt = torch.from_numpy(x)
        for k, names in LISTS.items():
            pe = pes[k]  # (1,n,512)
            model.set_classes(names, torch.from_numpy(pe))
            with torch.inference_mode():
                ref = model(xt)[0][0][0].numpy()
            out = runner.run_raw(x, pad_prompts(pe[0]))
            c = compare(ref, out, pe[0] / np.linalg.norm(pe[0], axis=1, keepdims=True))
            a = agg[k]
            a["ref"] += c["ref"]
            a["matched"] += c["matched"]
            a["minIou"] = min(a["minIou"], c["minIou"])
            a["maxDScore"] = max(a["maxDScore"], c["maxDScore"])
            a["normErr"] = max(a["normErr"], c["normErr"])
    checks = []
    for k, a in agg.items():
        note = f"minIou={a['minIou']:.4f} maxDScore={a['maxDScore']:.4f} screens={len(imgs)}"
        checks.append(
            {
                "id": f"AC-3.1-03.boxes.{k}",
                "value": a["matched"] / max(a["ref"], 1),
                "threshold": f"all ref detections: IoU > {IOU_MIN}, |dscore| < {DSCORE_MAX}",
                "n": a["ref"],
                "pass": a["ref"] > 0 and a["matched"] == a["ref"],
                "note": note,
            }
        )
        checks.append(
            {
                "id": f"AC-3.1-03.norm.{k}",
                "value": a["normErr"],
                "threshold": f"<= {NORM_TOL}",
                "n": len(imgs) * 100,
                "pass": a["normErr"] <= NORM_TOL,
                "note": "max | ||fingerprint|| - 1 |",
            }
        )
    both = [c["pass"] for c in checks if c["id"].endswith(("boxes.list1", "boxes.list2"))]
    checks.append(
        {
            "id": "AC-3.1-04.list-not-baked-in",
            "value": 1.0,
            "threshold": "same file sha, both lists pass",
            "n": 2,
            "pass": all(both),
            "note": f"one file sha256={sha256_file(data / FINDER_FILE)}",
        }
    )
    if (data / TEXT_FILE).is_file():
        prompts = text_prompts()
        ref = text_pe(model, prompts).float().cpu().numpy().reshape(len(prompts), -1)
        cos = cosine_rows(ref, runner.embed_texts(prompts))
        checks.append(
            {
                "id": "AC-3.1-03.text.min",
                "value": float(cos.min()),
                "threshold": f">= {TEXT_COS_MIN} (our choice; PLAN gives none)",
                "n": len(prompts),
                "pass": bool(cos.min() >= TEXT_COS_MIN),
                "note": f"mean={cos.mean():.6f}",
            }
        )
    else:
        checks.append(
            {
                "id": "AC-3.1-03.text.min",
                "value": None,
                "threshold": f">= {TEXT_COS_MIN}",
                "n": 0,
                "pass": True,
                "note": (
                    "ACCEPTED-DEVIATION (variant C: concepts are judged by SigLIP2 text; YOLOE "
                    "gets the fixed proposal_pe input). Text export BLOCKED: "
                    + str(meta.get("text"))[:300]
                ),
            }
        )
    files = []
    for f in sorted(data.glob("*.onnx")):
        files.append(
            {
                "path": f.resolve().relative_to(REPO).as_posix(),
                "sha256": sha256_file(f),
                "bytes": f.stat().st_size,
                **shape_report(f),
            }
        )
    changed = meta.get("changedVsPrevious") or []
    pt = getattr(model, "pt_path", None)
    report = {
        "model": "yoloe",
        "subPhase": "3.1.2",
        "created": datetime.now(UTC).isoformat(),
        "tools": _tools(),
        "source": {
            "url": "https://github.com/ultralytics/ultralytics",
            "licence": "AGPL-3.0",
            "revision": sha256_file(Path(pt)) if pt else "",
        },
        "files": files,
        "checks": checks,
        "nondeterminism": ("re-export changed: " + ", ".join(changed)) if changed else "",
        "textEncoder": meta.get("text"),
        "pass": all(c["pass"] for c in checks),
    }
    write_report("yoloe", report)
    for c in checks:
        print("ok  " if c["pass"] else "FAIL", c["id"], c["value"], c["note"])
    return 0 if report["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
