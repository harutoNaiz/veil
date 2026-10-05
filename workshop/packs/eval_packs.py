"""Score the topic packs.

python -m workshop.packs.eval_packs --pack spiders
python -m workshop.packs.eval_packs --all --cached

Images: Describer + compile_concept + judge(balanced) on data/public/photos. Recall = share of
target photos marked hide; cleanFalseCoverRate = share of clean photos (cat/dog/fox/neutral) marked
hide. Text: keyword rules on text_sets/<pack>.jsonl. Only spiders have an image test set; alcohol
has no licensed photo set (PENDING-HUMAN); needles, gore and spoilers are text-only (no images).
Embeddings are cached in data/public/photo_emb.npz so --cached never loads the model.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

import numpy as np

from workshop.packs.build_packs import HERE, PACKS, REPORTS, concept_doc, write_pack
from workshop.twin.judge import judge
from workshop.twin.public_set import PHOTOS
from workshop.twin.teacher import compile_concept

CACHE = PHOTOS.parent / "photo_emb.npz"
CLEAN = ("cat", "dog", "fox", "neutral")
IMAGE_TARGET = {"spiders": "spider"}  # pack -> photo folder holding its targets
BAR_RECALL, BAR_FALSE = 0.80, 0.05


def photo_files() -> list[Path]:
    return sorted(p for g in (*CLEAN, "spider") for p in (PHOTOS / g).glob("*.jpg"))


def embeddings(cached: bool) -> dict[str, np.ndarray]:
    files = photo_files()
    keys = [f"{p.parent.name}/{p.name}" for p in files]
    if CACHE.is_file():
        data = np.load(CACHE)
        if set(data["keys"].tolist()) >= set(keys):
            return dict(zip(data["keys"].tolist(), data["vecs"], strict=True))
        if cached:
            print("cache is stale; recomputing", file=sys.stderr)
    from PIL import Image

    enc = _text_encoder()
    images = []
    for p in files:
        with Image.open(p) as im:
            images.append(im.convert("RGB"))
    vecs = enc.embed_images(images)
    np.savez(CACHE, keys=np.array(keys), vecs=vecs)
    return dict(zip(keys, vecs, strict=True))


_ENC = []


def _text_encoder():
    if not _ENC:
        from workshop.twin.describer import Describer

        _ENC.append(Describer())
    return _ENC[0]


def text_metrics(pack_id: str) -> dict:
    kws = PACKS[pack_id]["concept"]["keywords"]
    rx = re.compile(r"\b(?:" + "|".join(re.escape(k) for k in kws) + r")\b", re.I)
    rows = [
        json.loads(x)
        for x in (HERE / "text_sets" / f"{pack_id}.jsonl").read_text("utf-8").splitlines()
        if x
    ]
    pos = [r for r in rows if r["label"] == 1]
    neg = [r for r in rows if r["label"] == 0]
    return {
        "textRecall": round(sum(bool(rx.search(r["text"])) for r in pos) / len(pos), 4),
        "textFalseRate": round(sum(bool(rx.search(r["text"])) for r in neg) / len(neg), 4),
        "textLines": [len(pos), len(neg)],
    }


def image_metrics(pack_id: str, cached: bool) -> dict:
    emb = embeddings(cached)
    cc = compile_concept(concept_doc(PACKS[pack_id]), _text_encoder())
    target = IMAGE_TARGET[pack_id]
    keys = sorted(emb)
    verdicts = judge(np.stack([emb[k] for k in keys]), cc, "balanced")
    hide = {k: v["decision"] == "hide" for k, v in zip(keys, verdicts, strict=True)}
    pos = [k for k in keys if k.startswith(target + "/")]
    neg = [k for k in keys if k.split("/")[0] in CLEAN]
    return {
        "recall": round(sum(hide[k] for k in pos) / len(pos), 4),
        "cleanFalseCoverRate": round(sum(hide[k] for k in neg) / len(neg), 4),
        "testImages": len(pos) + len(neg),
        "testSet": f"public-photos ({len(pos)} {target}, {len(neg)} clean)",
        "missed": [k for k in pos if not hide[k]],
        "falseCovers": [k for k in neg if hide[k]],
    }


def evaluate(pack_id: str, cached: bool) -> dict:
    text = text_metrics(pack_id)
    if pack_id in IMAGE_TARGET:
        img = image_metrics(pack_id, cached)
        ok = img["recall"] >= BAR_RECALL and img["cleanFalseCoverRate"] <= BAR_FALSE
        status = "PASS" if ok else "FAIL"
        line = (
            f"image recall {img['recall']:.2f}, clean false-cover {img['cleanFalseCoverRate']:.2f} "
            f"on {img['testSet']}; text recall {text['textRecall']:.2f}, "
            f"text false {text['textFalseRate']:.2f}."
        )
        report = {**img, **text, "status": status, "line": line}
    else:
        why = "no licensed photo set" if pack_id == "alcohol" else "text-only pack, no images"
        line = (
            f"image rows PENDING-HUMAN ({why}); text recall {text['textRecall']:.2f}, "
            f"text false {text['textFalseRate']:.2f} on {text['textLines'][0]}+"
            f"{text['textLines'][1]} hand-written lines."
        )
        report = {
            "recall": text["textRecall"],
            "cleanFalseCoverRate": text["textFalseRate"],
            "testImages": sum(text["textLines"]),
            "testSet": "hand-written text lines (image set PENDING-HUMAN)",
            **text,
            "status": "PENDING-HUMAN",
            "line": line,
        }
    REPORTS.mkdir(exist_ok=True)
    (REPORTS / f"{pack_id}.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    write_pack(pack_id, report)
    return report


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--pack")
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--cached", action="store_true")
    args = ap.parse_args(argv)
    ids = list(PACKS) if args.all else [args.pack]
    for pid in ids:
        r = evaluate(pid, args.cached)
        print(f"{pid}: {r['status']}  {r['line']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
