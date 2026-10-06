"""Check the benchmark is disjoint from the reference bank and from banned/dev words.

python -m workshop.twin.bench.disjoint --bench DIR --bank data/bank/v1
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from workshop.twin.bench import oi
from workshop.twin.bench.select import banned_set, singular


def check(manifest: dict, bank_ids: set[str], bank_flickr: set[str], cands: dict) -> dict:
    imgs = manifest["images"]
    id_overlap = len({im["id"] for im in imgs} & {str(i) for i in bank_ids})
    fl_overlap = len({im["flickrId"] for im in imgs if im["flickrId"]} & bank_flickr)
    test = {singular(w["word"]) for w in manifest["words"] if w["split"] == "test"}
    forbidden = banned_set(cands) | {singular(w) for w in cands["dev"]}
    return {
        "bankRows": len(bank_ids),
        "benchImages": len(imgs),
        "idOverlap": id_overlap,
        "flickrOverlap": fl_overlap,
        "wordOverlap": sorted(test & forbidden),
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--bench", required=True)
    ap.add_argument("--bank", required=True)
    a = ap.parse_args(argv)
    manifest = json.loads((Path(a.bench) / "manifest.json").read_text(encoding="utf-8"))
    cands = json.loads((Path(__file__).parent / "candidates.json").read_text(encoding="utf-8"))
    lines = (Path(a.bank) / "items.jsonl").read_text(encoding="utf-8").splitlines()
    ids = {json.loads(x)["id"] for x in lines if x}
    cap = oi.ROOT / "data" / "bank" / "src" / "captions_train2017.json"
    data = json.loads(cap.read_text(encoding="utf-8"))
    fl = {im["id"]: oi.flickr_id(im.get("flickr_url", "")) for im in data["images"]}
    bank_fl = {fl[i] for i in ids if fl.get(i)}
    r = check(manifest, ids, bank_fl, cands)
    print(
        f"DISJOINT bankRows={r['bankRows']} benchImages={r['benchImages']} "
        f"idOverlap={r['idOverlap']} flickrOverlap={r['flickrOverlap']}"
    )
    if r["wordOverlap"]:
        print(f"WORDS OVERLAP {r['wordOverlap']}")
    bad = r["idOverlap"] or r["flickrOverlap"] or r["wordOverlap"]
    return 1 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main())
