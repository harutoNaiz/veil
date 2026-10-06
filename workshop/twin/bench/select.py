"""Select words and image queues for the benchmark (count-only, before any image is seen).

python -m workshop.twin.bench.select --out DIR [--mini|--smoke]
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

from workshop.twin.bench import oi

HERE = Path(__file__).resolve().parent
CATS = ["animal", "object", "food", "vehicle"]
PROFILES = {
    "full": {
        "per_cat": 25,
        "min_pos": 40,
        "dev": True,
        "subsets": ["validation", "test"],
        "q": (60, 20, 450),
        "quota": (36, 8, 300),
        "dev_n": 12,
        "min_dev": 10,
    },
    "mini": {
        "per_cat": 3,
        "min_pos": 15,
        "dev": True,
        "subsets": ["validation", "test"],
        "q": (24, 8, 60),
        "quota": (12, 2, 30),
        "dev_n": 4,
        "min_dev": 10,
    },
    "smoke": {
        "per_cat": 1,
        "cap": 2,
        "min_pos": 5,
        "dev": False,
        "subsets": ["validation"],
        "q": (10, 4, 12),
        "quota": (4, 1, 6),
        "dev_n": 0,
        "min_dev": 1,
    },
}


def singular(w: str) -> str:
    w = w.lower().strip()
    if w.endswith("ies") and len(w) > 4:
        return w[:-3] + "y"
    if w.endswith(("ses", "xes", "ches", "shes")):
        return w[:-2]
    if w.endswith("s") and not w.endswith("ss"):
        return w[:-1]
    return w


def banned_set(cands: dict) -> set[str]:
    return {singular(w) for w in cands["banned"]}


def key(word: str, image_id: str) -> str:
    return hashlib.sha256((word + image_id).encode()).hexdigest()


def eligible(i: str, labels: dict, meta: dict, block: set[str], bank_flickr: set[str]) -> bool:
    m = meta.get(i)
    if m is None or not oi.licence_ok(m["license"]):
        return False
    if labels["pos"].get(i, set()) & block:
        return False
    fid = oi.flickr_id(m["url"])
    return not (fid and fid in bank_flickr)


def word_images(mids: set[str], labels: dict, ok: set[str]) -> tuple[list[str], list[str]]:
    pos = [i for i in ok if labels["pos"].get(i, set()) & mids]
    neg = [
        i
        for i in ok
        if labels["neg"].get(i, set()) & mids and not (labels["pos"].get(i, set()) & mids)
    ]
    return pos, neg


def choose_words(cands: dict, counts: dict[str, int], prof: dict) -> list[dict]:
    """counts: word -> eligible positives (only words with exactly one MID are present)."""
    ban = banned_set(cands)
    own: dict[str, list[str]] = {}
    for cat in CATS:
        own[cat] = [
            c["word"]
            for c in cands["categories"][cat]
            if singular(c["word"]) not in ban and counts.get(c["word"], 0) >= prof["min_pos"]
        ]
    chosen = {cat: own[cat][: prof["per_cat"]] for cat in CATS}
    used = {w for ws in chosen.values() for w in ws}
    cursor = {c: len(chosen[c]) for c in CATS}
    short = sum(prof["per_cat"] - len(chosen[c]) for c in CATS)
    while short > 0:
        moved = False
        for cat in CATS:
            if short <= 0:
                break
            if len(chosen[cat]) >= prof["per_cat"]:
                continue
            for donor in CATS:  # next unused word from another category, round-robin
                if donor == cat:
                    continue
                rest = [w for w in own[donor][cursor[donor] :] if w not in used]
                if rest:
                    chosen[cat].append(rest[0])
                    used.add(rest[0])
                    short -= 1
                    moved = True
                    break
        if not moved:
            break
    cat_of = {c["word"]: cat for cat in CATS for c in cands["categories"][cat]}
    return [
        {"word": w, "category": cat_of[w], "split": "test"} for cat in CATS for w in chosen[cat]
    ]


def balance(words: list[dict]) -> dict[str, int]:
    out = {c: 0 for c in CATS}
    for w in words:
        out[w["category"]] += 1
    return out


def build_selection(
    cands: dict,
    prof: dict,
    classes: dict[str, list[str]],
    desc: dict[str, set[str]],
    labels: dict,
    meta: dict,
    bank_flickr: set[str],
) -> dict:
    block: set[str] = set()
    for n in cands["block"]:
        for m in classes.get(n.lower(), []):
            block |= desc.get(m, {m})
    ok = {i for i in meta if eligible(i, labels, meta, block, bank_flickr)}

    def mid_of(name: str) -> str | None:
        ms = classes.get(name.lower(), [])
        return ms[0] if len(ms) == 1 else None

    counts: dict[str, int] = {}
    info: dict[str, tuple[set[str], str, list[str], list[str]]] = {}
    for cat in CATS:
        for c in cands["categories"][cat]:
            mid = mid_of(c["oi"])
            if mid is None:
                continue
            mids = desc.get(mid, {mid})
            pos, neg = word_images(mids, labels, ok)
            counts[c["word"]] = len(pos)
            info[c["word"]] = (mids, mid, pos, neg)
    words = choose_words(cands, counts, prof)[: prof.get("cap", 999)]
    if prof["dev"]:
        n = 0
        for w in cands["dev"]:
            mid = mid_of(w)
            if mid is None or n >= prof["dev_n"]:
                continue
            mids = desc.get(mid, {mid})
            pos, neg = word_images(mids, labels, ok)
            if len(pos) >= prof["min_dev"]:
                info[w] = (mids, mid, pos, neg)
                words.append({"word": w, "category": "dev", "split": "dev"})
                n += 1
    word_mids: set[str] = set()
    for w in words:
        mids, mid, _, _ = info[w["word"]]
        word_mids |= mids
        w["mids"] = [mid]
        w["descMids"] = sorted(mids)
    qp, ql, qo = prof["q"]
    queues: dict[str, list[str]] = {}
    for w in words:
        _, _, pos, neg = info[w["word"]]
        name = w["word"]
        queues[f"pos:{name}"] = sorted(pos, key=lambda i, n=name: key(n, i))[:qp]
        queues[f"look:{name}"] = sorted(neg, key=lambda i, n=name: key(n, i))[:ql]
    cand_mids: set[str] = set()
    for v in info.values():
        cand_mids |= v[0]
    pool = [
        i for i in ok if i in labels["anypos"] and not (labels["pos"].get(i, set()) & cand_mids)
    ]
    queues["pool"] = sorted(pool, key=lambda i: key("pool", i))[:qo]
    used = {i for q in queues.values() for i in q}
    keep_pos = word_mids | set(labels["tagMids"])
    images = {}
    for i in sorted(used):
        m = dict(meta[i])
        m["flickrId"] = oi.flickr_id(m["url"])
        m["posMids"] = sorted(labels["pos"].get(i, set()) & keep_pos)
        m["negMids"] = sorted(labels["neg"].get(i, set()) & word_mids)
        images[i] = m
    return {
        "profile": prof,
        "words": words,
        "queues": queues,
        "images": images,
        "tagMids": labels["tagMids"],
        "eligible": len(ok),
    }


def load_bank_flickr(bank: Path, src: Path, need_captions: bool) -> set[str]:
    cap = src / "captions_train2017.json"
    if not cap.exists():
        if not need_captions:
            print("WARN no captions_train2017.json: bank flickr ids empty (smoke only)")
            return set()
        from workshop.twin.bank import coco

        cap = coco.captions_path(src)
    data = json.loads(cap.read_text(encoding="utf-8"))
    fl = {im["id"]: oi.flickr_id(im.get("flickr_url", "")) for im in data["images"]}
    items = Path(bank) / "items.jsonl"
    if items.exists():
        ids = {json.loads(x)["id"] for x in items.read_text(encoding="utf-8").splitlines() if x}
        return {fl[i] for i in ids if fl.get(i)}
    return {v for v in fl.values() if v}


def read_inputs(cands: dict, prof: dict, src: Path):
    files = {k: oi.download(rel, src) for k, rel in oi.urls(prof["subsets"]).items()}
    classes = oi.read_classes(files["classes"])
    desc = oi.load_hierarchy(files["hierarchy"])
    names = [c["oi"] for cat in CATS for c in cands["categories"][cat]] + list(cands["dev"])
    names += cands["block"] + cands["tags"]
    rel: set[str] = set()
    tag_mids: dict[str, str] = {}
    for n in names:
        for m in classes.get(n.lower(), []):
            rel |= desc.get(m, {m})
    for n in cands["tags"]:
        for m in classes.get(n.lower(), []):
            tag_mids[m] = n
    pos: dict[str, set] = {}
    neg: dict[str, set] = {}
    anypos: set[str] = set()
    for s in prof["subsets"]:
        for i, mid, positive, keep in oi.stream_labels(files[f"labels-{s}"], rel | set(tag_mids)):
            if positive:
                anypos.add(i)
            if keep:
                (pos if positive else neg).setdefault(i, set()).add(mid)
    cand_ids = anypos | set(neg)
    meta = {}
    for s in prof["subsets"]:
        for m in oi.stream_images(files[f"images-{s}"], cand_ids):
            meta[m["id"]] = m
    labels = {"pos": pos, "neg": neg, "anypos": anypos, "tagMids": tag_mids}
    return classes, desc, labels, meta


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    g = ap.add_mutually_exclusive_group()
    g.add_argument("--mini", action="store_true")
    g.add_argument("--smoke", action="store_true")
    ap.add_argument("--bank", default=str(oi.ROOT / "data" / "bank" / "v1"))
    a = ap.parse_args(argv)
    prof = PROFILES["smoke" if a.smoke else "mini" if a.mini else "full"]
    cands = json.loads((HERE / "candidates.json").read_text(encoding="utf-8"))
    classes, desc, labels, meta = read_inputs(cands, prof, oi.SRC)
    bank_src = oi.ROOT / "data" / "bank" / "src"
    flickr = load_bank_flickr(Path(a.bank), bank_src, need_captions=not a.smoke)
    sel = build_selection(cands, prof, classes, desc, labels, meta, flickr)
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    (out / "selection.json").write_text(json.dumps(sel), encoding="utf-8")
    test = [w for w in sel["words"] if w["split"] == "test"]
    print(f"SELECT test={len(test)} dev={len(sel['words']) - len(test)} balance={balance(test)}")
    print(
        f"SELECT eligible={len(sel['images'])}/{sel['eligible']} pool={len(sel['queues']['pool'])}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
