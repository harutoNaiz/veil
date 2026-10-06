"""Build a reference bank: python -m workshop.twin.bank.build_bank --out DIR --limit N --ui U."""

from __future__ import annotations

import argparse
import hashlib
import json
import time
from collections import Counter
from pathlib import Path

import numpy as np

from workshop.twin.bank import bankio, coco, engine, ui_synth, vocab
from workshop.twin.teacher import IGNORE

ROOT = Path(__file__).resolve().parents[3]
SRC = ROOT / "data" / "bank" / "src"
ONNX = ROOT / "data" / "forge" / "siglip2"
CHUNK = 64
CKPT = 256


def _sha(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def _labels(captions: list[str], form_to_idx: dict[str, int]) -> list[int]:
    return sorted({form_to_idx[t] for c in captions for t in vocab.tokens(c) if t in form_to_idx})


def _write_vocab(out, desc, lemmas, excl, rel, bank_id, labels, items, dim) -> int:
    """Vocab rows (cached text encodes), centred thresholds, vocab.bin/json, items.jsonl."""
    names = [x["name"] for x in lemmas]
    emb_p = out / "vocab_emb.npy"
    if emb_p.exists():
        vrows = np.load(emb_p)
    else:
        vrows = np.concatenate(
            [vocab.ensemble(desc.embed_texts, names), vocab.ignore_rows(desc.embed_texts)]
        )
        np.save(emb_p, vrows)
    bank = bankio.read_bank(out / "bank.bin")
    q, scale = bankio.quantise(vrows)
    vdeq = bankio.dequant(q, scale)
    lab_sets = [set(x) for x in labels]
    center = vdeq[: len(names)].mean(0)
    thr = vocab.thresholds(bank.rows, vdeq[: len(names)], excl, lab_sets, center)
    ign_thr = vocab.thresholds(
        bank.rows, vdeq[len(names) :], [[] for _ in IGNORE], lab_sets, center
    )
    thr = np.concatenate([thr, ign_thr])
    n_pos = Counter()
    for labs in lab_sets:
        for lab in labs:
            n_pos[lab] += 1
    entries = [
        {
            "name": x["name"],
            "kind": "noun",
            "forms": x["forms"],
            "excl": excl[i],
            "rel": rel[i],
            "nPos": sum(n_pos[j] for j in excl[i]),
        }
        for i, x in enumerate(lemmas)
    ] + [
        {"name": p, "kind": "ignore", "forms": [p], "excl": [], "rel": [], "nPos": 0}
        for p in IGNORE
    ]
    meta = {
        "version": 1,
        "bankId": bank_id,
        "dim": dim,
        "templates": vocab.TEMPLATES,
        "ignore": list(IGNORE),
        "quantilesPerMille": vocab.Q_PER_MILLE,
        "k": 8,
        "chips": 6,
        "margin": 0.0,
        "entries": entries,
    }
    bankio.write_vocab(out, vdeq, thr, meta)
    (out / "items.jsonl").write_text("".join(json.dumps(i) + "\n" for i in items), encoding="utf-8")
    return len(entries)


def _revocab(out, a, lemmas, excl, rel, form_to_idx, cands) -> int:
    """Rebuild vocab, labels and thresholds from the existing bank rows (no image embedding)."""
    items_p = out / "items.jsonl"
    items = [json.loads(x) for x in items_p.read_text(encoding="utf-8").splitlines() if x]
    caps = {f"{c['id']:012d}": c["captions"] for c in cands}
    for it in items:
        coco_it = it["source"] == "coco"
        it["labels"] = _labels(caps.get(it["id"], []), form_to_idx) if coco_it else []
    labels = [it["labels"] for it in items]
    bank_id = bankio.relabel_bank(out / "bank.bin", labels)
    eng = (
        json.loads((out / "engine.json").read_text(encoding="utf-8"))
        if (out / "engine.json").exists()
        else {"engine": a.engine, "provider": "cpu"}
    )
    desc = engine.make_describer(eng["engine"], "cpu", ONNX)
    dim = bankio.read_bank(out / "bank.bin").rows.shape[1]
    n = _write_vocab(out, desc, lemmas, excl, rel, bank_id, labels, items, dim)
    print(f"REVOCAB OK n={len(items)} vocab={n} bankId={bank_id}")
    return 0


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--ui", type=int, default=0)
    ap.add_argument("--revocab", action="store_true")
    ap.add_argument("--vocab-limit", type=int, default=5000)
    ap.add_argument("--engine", choices=["torch", "onnx"], default="torch")
    ap.add_argument("--provider", choices=["cpu", "dml"], default="cpu")
    ap.add_argument("--threads", type=int, default=32)
    a = ap.parse_args(argv)
    out = Path(a.out)
    if not out.is_absolute():
        out = ROOT / out
    out.mkdir(parents=True, exist_ok=True)
    if a.revocab:
        (out / "vocab_emb.npy").unlink(missing_ok=True)
    elif (out / "bank.bin").exists() and (out / "vocab.bin").exists():
        print("bank already built:", out)
        return 0

    eng_p = out / "engine.json"
    if a.revocab:
        pass
    elif (out / "partial.npz").exists():
        prev_eng = (
            json.loads(eng_p.read_text(encoding="utf-8"))["engine"] if eng_p.exists() else "torch"
        )
        if prev_eng != a.engine:
            print(f"partial bank was built with engine={prev_eng}, not {a.engine}; refusing")
            return 3
    if not a.revocab:
        eng_p.write_text(json.dumps({"engine": a.engine, "provider": a.provider}), encoding="utf-8")

    data = coco.load_captions(SRC)
    wn = vocab.wn_setup(SRC)
    all_caps = [x["caption"] for x in data["annotations"]]
    lemmas = vocab.build_lemmas(all_caps, a.vocab_limit, wn)
    names = [x["name"] for x in lemmas]
    excl, rel = vocab.relations(names, vocab.wordnet_neighbours(wn))
    form_to_idx = {f: i for i, x in enumerate(lemmas) for f in x["forms"]}
    cands = coco.filter_items(data)
    del data, all_caps

    if a.revocab:
        return _revocab(out, a, lemmas, excl, rel, form_to_idx, cands)

    desc = engine.make_describer(a.engine, a.provider, ONNX)

    # resume state
    items_p, part_p = out / "items.jsonl", out / "partial.npz"
    items: list[dict] = []
    vecs: list[np.ndarray] = []
    if items_p.exists() and part_p.exists():
        prev = np.load(part_p)["vecs"]
        lines = [json.loads(x) for x in items_p.read_text(encoding="utf-8").splitlines() if x]
        m = min(len(prev), len(lines))
        items, vecs = lines[:m], [prev[:m]]
        print("resuming at row", m)
    done = {(it["source"], it["id"]) for it in items}
    n_coco = sum(1 for it in items if it["source"] == "coco")
    n_ui = sum(1 for it in items if it["source"] == "ui")
    t0, t_rows = time.time(), 0

    def checkpoint() -> None:
        np.savez(part_p, vecs=np.concatenate(vecs) if vecs else np.zeros((0, 768), "f4"))
        items_p.write_text("".join(json.dumps(i) + "\n" for i in items), encoding="utf-8")

    def flush(batch_items: list[dict], images: list) -> None:
        nonlocal t_rows
        v = desc.embed_images(images)
        vecs.append(v)
        for it in batch_items:
            it["row"] = len(items)
            items.append(it)
        t_rows += len(batch_items)
        if len(items) // CKPT != (len(items) - len(batch_items)) // CKPT:
            checkpoint()
            rate = t_rows / max(time.time() - t0, 1e-9)
            total = a.limit + a.ui
            print(
                f"rows {len(items)}/{total} {rate:.2f} img/s eta {(total - len(items)) / rate:.0f}s"
            )

    def chunk_iter():
        pending = [c for c in cands if ("coco", f"{c['id']:012d}") not in done]
        for i in range(0, len(pending), CHUNK):
            yield pending[i : i + CHUNK]

    if n_coco < a.limit:
        fetch = lambda c: coco.fetch_image(coco.item_url(c["file_name"]))  # noqa: E731
        for chunk, imgs in engine.prefetch(chunk_iter(), fetch, a.threads):
            ok = [(c, im) for c, im in zip(chunk, imgs, strict=True) if im is not None]
            ok = ok[: a.limit - n_coco]
            if not ok:
                continue
            rows = [
                {
                    "row": 0,
                    "source": "coco",
                    "id": f"{c['id']:012d}",
                    "url": coco.item_url(c["file_name"]),
                    "licenseId": c["licenseId"],
                    "license": coco.LICENCES[c["licenseId"]],
                    "labels": _labels(c["captions"], form_to_idx),
                }
                for c, _ in ok
            ]
            flush(rows, [im for _, im in ok])
            n_coco += len(ok)
            if n_coco >= a.limit:
                break
    while n_ui < a.ui:
        idx = [i for i in range(n_ui, min(n_ui + CHUNK, a.ui))]
        rows = [
            {
                "row": 0,
                "source": "ui",
                "id": f"ui-{i:05d}",
                "url": "",
                "licenseId": 0,
                "license": ui_synth.LICENCE,
                "labels": [],
            }
            for i in idx
        ]
        flush(rows, [ui_synth.render_screen(i) for i in idx])
        n_ui += len(idx)
    checkpoint()
    print(f"EMBED {t_rows} rows {t_rows / max(time.time() - t0, 1e-9):.2f} img/s")

    allv = np.concatenate(vecs)
    labels = [it["labels"] for it in items]
    bank_id = bankio.write_bank(out / "bank.bin", allv, labels)
    _write_vocab(out, desc, lemmas, excl, rel, bank_id, labels, items, int(allv.shape[1]))
    part_p.unlink(missing_ok=True)

    if out.name == "v1":
        lic = Counter(it["license"] for it in items)
        src = Counter(it["source"] for it in items)
        man = {
            "n": len(items),
            "dim": int(allv.shape[1]),
            "bankId": bank_id,
            "sha256": {f: _sha(out / f) for f in ("bank.bin", "vocab.bin", "vocab.json")},
            "sources": dict(src),
            "licences": dict(lic),
            "engine": a.engine,
            "onnxSha256": {p.name: _sha(p) for p in sorted(ONNX.glob("siglip2-*.onnx"))},
        }
        here = Path(__file__).parent
        (here / "manifest-v1.json").write_text(json.dumps(man, indent=1), encoding="utf-8")
        rows = ["row,source,id,licenseId,license,url"] + [
            f"{i['row']},{i['source']},{i['id']},{i['licenseId']},{i['license']},{i['url']}"
            for i in items
        ]
        (here / "licences-v1.csv").write_text("\n".join(rows) + "\n", encoding="utf-8")
    print(f"BUILD OK n={len(items)} vocab={len(lemmas) + len(IGNORE)} bankId={bank_id}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
