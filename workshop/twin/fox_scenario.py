"""Fox scenario: "cat" covers a fox; one notThis stops it and its repost, cats stay hidden.

Writes guard/brain/src/test/resources/corrections/fox.json for the Kotlin replay.
Exit 0 pass, 1 fail, 3 skipped (SigLIP2 cache absent).
"""

from __future__ import annotations

import io
import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image

from workshop.contracts.rules import decode_f16, encode_f16
from workshop.twin.corrections import CorrectionBook
from workshop.twin.judge import judge

PHOTOS = Path("data/public/photos")
OUT = Path("guard/brain/src/test/resources/corrections/fox.json")
LOOSE = "a small furry animal with pointed ears"


def repost(path: Path) -> Image.Image:
    im = Image.open(path).convert("RGB")
    w, h = im.size
    cw, ch = int(w * 0.9), int(h * 0.9)
    left, top = (w - cw) // 2, (h - ch) // 2
    im = im.crop((left, top, left + cw, top + ch))
    im = im.resize((256, max(1, round(256 * ch / cw))))
    buf = io.BytesIO()
    im.save(buf, "JPEG", quality=60)
    return Image.open(io.BytesIO(buf.getvalue())).convert("RGB")


def _decide(vecs, cc, mode, book=None, cid="cat"):
    out = judge(vecs, cc, mode)
    if book is not None:
        out = [book.filter(cid, v, o) for v, o in zip(vecs, out, strict=True)]
    return [o["decision"] for o in out]


def main() -> int:
    from workshop.twin.describer import Describer, weights_available

    if not weights_available():
        print("PENDING: SigLIP2 cache absent; fox scenario skipped")
        return 3
    from workshop.twin.teacher import compile_concept, concept_card

    desc = Describer()
    foxes = sorted((PHOTOS / "fox").glob("*.jpg"))
    cats = sorted((PHOTOS / "cat").glob("*.jpg"))
    imgs = [Image.open(p).convert("RGB") for p in foxes + cats] + [repost(p) for p in foxes]
    raw = desc.embed_images(imgs)
    vecs = np.stack([decode_f16(encode_f16(v), raw.shape[1]) for v in raw]).astype(np.float64)
    vecs /= np.linalg.norm(vecs, axis=1, keepdims=True)
    nf, nc = len(foxes), len(cats)
    fox_v, cat_v, rep_v = vecs[:nf], vecs[nf : nf + nc], vecs[nf + nc :]

    card = concept_card("cat")
    chosen = None
    loose = card["looksLike"] + [LOOSE]
    no_fox = [b for b in card["butNot"] if b != "a fox"]
    for label, c in (
        ("strict", card),
        ("loose", {**card, "looksLike": loose}),
        ("loose-no-fox-butNot", {**card, "looksLike": loose, "butNot": no_fox}),
    ):
        cc = compile_concept(c, desc)
        if any(d == "hide" for d in _decide(fox_v, cc, "strict")):
            chosen = (label, cc)
            break
    if chosen is None:
        print("FAIL: precondition: no fox is hide under strict or the loose cat card")
        return 1
    label, cc = chosen
    mode = "strict"
    fi = next(i for i, d in enumerate(_decide(fox_v, cc, mode)) if d == "hide")
    before_cat = _decide(cat_v, cc, mode)

    book = CorrectionBook()
    fb = {"kind": "notThis", "conceptId": "cat", "layer": 2}
    book.record(fb, fox_v[fi])
    adj = book.adjust(cc)
    after_fox = _decide(fox_v, adj, mode, book)
    after_rep = _decide(rep_v, adj, mode, book)
    after_cat = _decide(cat_v, adj, mode, book)
    ok = after_fox[fi] != "hide" and after_rep[fi] != "hide"
    ok = ok and all(a == "hide" for b, a in zip(before_cat, after_cat, strict=True) if b == "hide")
    print(f"fox scenario: card={label} fox[{fi}]={after_fox[fi]} repost={after_rep[fi]} ok={ok}")
    if not ok:
        return 1

    def pack(name, mat):
        return [{"name": f"{name}{i}", "vec": encode_f16(v)} for i, v in enumerate(mat)]

    doc = {
        "mode": mode,
        "dim": int(vecs.shape[1]),
        "conceptId": "cat",
        "feedbackIndex": fi,
        "concept": cc,
        "fox": pack("fox", fox_v),
        "repost": pack("rep", rep_v),
        "cat": pack("cat", cat_v),
        "before": {"fox": _decide(fox_v, cc, mode), "cat": before_cat},
        "after": {"fox": after_fox, "repost": after_rep, "cat": after_cat},
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(doc, separators=(",", ":")), encoding="utf-8")
    print(f"wrote {OUT} ({OUT.stat().st_size} bytes)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
