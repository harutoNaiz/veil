"""Toxicity parity: AUC of the PyTorch float model vs each ONNX length. Never prints text."""

from __future__ import annotations

import json
import os
import sys
from datetime import UTC, datetime

import numpy as np

from workshop.forge import common
from workshop.forge.toxicity.export import LENGTHS, OUT, choice

MAX_DROP = 0.005


def auc(labels, scores) -> float:
    """Rank-based AUC (ties averaged). NaN when only one class is present."""
    y = np.asarray(labels).astype(int)
    s = np.asarray(scores, dtype=np.float64)
    pos, neg = int((y == 1).sum()), int((y == 0).sum())
    if pos == 0 or neg == 0:
        return float("nan")
    order = np.argsort(s, kind="stable")
    ranks = np.empty(len(s), dtype=np.float64)
    ranks[order] = np.arange(1, len(s) + 1)
    for v in np.unique(s):  # average ranks of ties
        m = s == v
        if m.sum() > 1:
            ranks[m] = ranks[m].mean()
    return float((ranks[y == 1].sum() - pos * (pos + 1) / 2) / (pos * neg))


def pad_truncate(ids: list[int], length: int, pad_id: int) -> tuple[np.ndarray, np.ndarray]:
    """(1, L) int64 input_ids and attention_mask: truncate to L or pad with pad_id."""
    ids = list(ids)[:length]
    n = len(ids)
    out = np.full((1, length), pad_id, dtype=np.int64)
    out[0, :n] = ids
    mask = np.zeros((1, length), dtype=np.int64)
    mask[0, :n] = 1
    return out, mask


def toxic_score(logits: np.ndarray, pos_index: int) -> float:
    z = np.asarray(logits, dtype=np.float64).reshape(-1)
    if z.size == 1:
        return float(1 / (1 + np.exp(-z[0])))
    e = np.exp(z - z.max())
    return float((e / e.sum())[pos_index])


def positive_index(id2label: dict) -> int:
    for i, name in sorted(id2label.items(), key=lambda kv: int(kv[0])):
        n = str(name).lower()
        if ("toxic" in n or "offens" in n or "hate" in n) and not any(
            w in n for w in ("non", "not", "neutral")
        ):
            return int(i)
    return max(int(i) for i in id2label)


def main() -> int:
    os.environ.setdefault("HF_HUB_OFFLINE", "1")
    import onnx
    import onnxruntime as ort
    import torch

    from workshop.forge.toxicity.export import load_model

    tok, model = load_model()
    pos = positive_index(model.config.id2label)
    rows = [
        json.loads(line)
        for line in (OUT / "sample.jsonl").read_text(encoding="utf-8").splitlines()
        if line
    ]
    labels = [r["label"] for r in rows]
    pad_id = tok.pad_token_id if tok.pad_token_id is not None else 0
    enc = [tok(r["text"], truncation=True, max_length=512)["input_ids"] for r in rows]

    ref = []
    with torch.no_grad():
        for ids in enc:
            t = torch.tensor([ids])
            ref.append(
                toxic_score(
                    model(input_ids=t, attention_mask=torch.ones_like(t)).logits.numpy(), pos
                )
            )
    base = auc(labels, ref)
    checks = []
    files = []
    for n in LENGTHS:
        p = OUT / f"toxicity-seq{n}.onnx"
        sess = ort.InferenceSession(str(p), providers=["CPUExecutionProvider"])
        sc = []
        for ids in enc:
            i, m = pad_truncate(ids, n, pad_id)
            sc.append(toxic_score(sess.run(None, {"input_ids": i, "attention_mask": m})[0], pos))
        a = auc(labels, sc)
        checks.append(
            {
                "id": f"AC-3.1-05.toxicity-seq{n}.auc_drop",
                "value": round(base - a, 6),
                "threshold": f"<= {MAX_DROP}",
                "n": len(rows),
                "pass": bool(base - a <= MAX_DROP),
                "note": f"torch AUC {base:.4f}, onnx AUC {a:.4f}",
            }
        )
        print(checks[-1]["id"], checks[-1]["value"], checks[-1]["pass"])
        files.append(
            {
                "path": common._rel(p),
                "sha256": common.sha256_file(p),
                "bytes": p.stat().st_size,
                **common.shape_report(p),
            }
        )
    ch = choice()
    ok = all(c["pass"] for c in checks) and not np.isnan(base)
    common.write_report(
        "toxicity",
        {
            "model": "toxicity",
            "subPhase": "3.1.3",
            "created": datetime.now(UTC).isoformat(),
            "tools": {
                "torch": torch.__version__,
                "onnx": onnx.__version__,
                "onnxruntime": ort.__version__,
            },
            "source": {
                "url": ch["model"]["url"],
                "licence": ch["model"]["licence"],
                "revision": ch["model"].get("revision"),
            },
            "dataset": ch.get("dataset"),
            "files": files,
            "checks": checks,
            "nondeterminism": "",
            "pass": ok,
        },
    )
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
