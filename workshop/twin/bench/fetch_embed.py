"""Fetch, freeze, compose and embed the benchmark.

python -m workshop.twin.bench.fetch_embed --out DIR --engine onnx --provider dml [--threads 32]
Phases (each skipped when done): fetch, freeze, embed, replay set, thumbnails + cleanup.
Never prints image content.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import shutil
import sys
import time
from concurrent.futures import ThreadPoolExecutor
from io import BytesIO
from pathlib import Path

import numpy as np
from PIL import Image

from workshop.twin.bank import coco
from workshop.twin.bench import compose, fmt, oi

HERE = Path(__file__).resolve().parent
ONNX = oi.ROOT / "data" / "forge" / "siglip2"
MAX_SIDE = 320
CKPT = 64


def accepted(queue: list[str], state: dict[str, dict], quota: int) -> tuple[list[str], list[str]]:
    """Walk the queue in order: (accepted ids, ids still to try to reach the quota)."""
    got, todo = [], []
    for i in queue:
        if len(got) + len(todo) >= quota:
            break
        st = state.get(i)
        if st is None:
            todo.append(i)
        elif st["ok"]:
            got.append(i)
    return got, todo


def fetch_one(meta: dict, cache: Path) -> dict:
    try:
        raw = coco._get(meta["url"].replace("https://", "http://"), timeout=40)
        sha = hashlib.sha256(raw).hexdigest()
        im = Image.open(BytesIO(raw)).convert("RGB")
        if meta.get("rotation"):
            im = im.rotate(meta["rotation"], expand=True)
        im.thumbnail((MAX_SIDE, MAX_SIDE), Image.LANCZOS)
        im.save(cache / f"{meta['id']}.jpg", "JPEG", quality=85)
        return {"id": meta["id"], "ok": True, "sha256": sha}
    except Exception:  # noqa: BLE001
        return {"id": meta["id"], "ok": False}


def phase_fetch(out: Path, sel: dict, threads: int) -> dict[str, dict]:
    cache = out / "cache"
    cache.mkdir(exist_ok=True)
    ck = out / "fetched.jsonl"
    state: dict[str, dict] = {}
    if ck.exists():
        for line in ck.read_text(encoding="utf-8").splitlines():
            if line:
                r = json.loads(line)
                state[r["id"]] = r
    qp, ql, qo = sel["profile"]["quota"]
    t0, done0 = time.time(), len(state)
    with ThreadPoolExecutor(threads) as ex, ck.open("a", encoding="utf-8") as f:
        while True:
            todo: list[str] = []
            for name, q in sel["queues"].items():
                quota = qo if name == "pool" else qp if name.startswith("pos:") else ql
                todo += accepted(q, state, quota)[1]
            todo = sorted(set(todo) - set(state))
            if not todo:
                break
            for r in ex.map(lambda i: fetch_one(sel["images"][i], cache), todo):
                state[r["id"]] = r
                f.write(json.dumps(r) + "\n")
            f.flush()
            rate = (len(state) - done0) / max(1e-9, time.time() - t0)
            left = len(todo) / max(rate, 1e-9)
            print(
                f"FETCH tried={len(state)} {rate:.2f} img/s last batch {len(todo)} eta~{left:.0f}s"
            )
    return state


def freeze(out: Path, sel: dict, state: dict[str, dict]) -> dict:
    qp, ql, qo = sel["profile"]["quota"]
    roles: dict[str, list[str]] = {}
    for name, q in sel["queues"].items():
        quota = qo if name == "pool" else qp if name.startswith("pos:") else ql
        for i in accepted(q, state, quota)[0]:
            roles.setdefault(i, []).append("pool" if name == "pool" else name)
    words = [
        {k: w[k] for k in ("word", "category", "split", "mids", "descMids")} for w in sel["words"]
    ]
    wm = {w["word"]: set(w["descMids"]) for w in words}
    tagname = sel["tagMids"]
    images = []
    for i in sorted(roles):
        m = sel["images"][i]
        pos = set(m["posMids"])
        images.append(
            {
                "id": i,
                "source": "openimages",
                "subset": m["subset"],
                "url": m["url"],
                "landing": m["landing"],
                "license": m["license"],
                "author": m["author"],
                "flickrId": m["flickrId"],
                "rotation": m["rotation"],
                "sha256": state[i]["sha256"],
                "pos": sorted(w for w, ms in wm.items() if pos & ms),
                "neg": sorted(w for w, ms in wm.items() if set(m["negMids"]) & ms and not pos & ms),
                "roles": sorted(roles[i]),
                "tags": sorted({tagname[t] for t in pos if t in tagname}),
            }
        )
    pool = [im["id"] for im in images if "pool" in im["roles"]]
    plan = compose.plan_screens([im["id"] for im in images], pool=pool)
    screens = []
    for s in plan:
        photos = [Image.open(out / "cache" / f"{c}.jpg") for c in s["cards"]]
        _, rects, _ = compose.render_feed(compose.screen_rng(s["i"]), photos, s["dark"])
        screens.append({**s, "photoRects": rects})
    return {
        "version": 1,
        "name": out.name,
        "dataset": "Open Images V7 (validation,test) human-verified image-level labels",
        "labelLicence": "CC BY 4.0",
        "words": words,
        "images": images,
        "screens": screens,
    }


def phase_embed(out: Path, manifest: dict, engine: str, provider: str) -> None:
    from workshop.twin import run
    from workshop.twin.bank import engine as eng

    desc = eng.make_describer(engine, provider, ONNX)
    fn = run.describer_pieces(desc)
    part = out / "partial.npz"
    vecs: list[np.ndarray] = []
    regions: list[dict] = []
    if part.exists():
        vecs = [np.load(part)["vecs"]]
    start = sum(len(v) for v in vecs) // fmt.PIECES_PER_SCREEN
    t0 = time.time()
    for s in manifest["screens"][start:]:
        photos = [Image.open(out / "cache" / f"{c}.jpg") for c in s["cards"]]
        img, _, _ = compose.render_feed(compose.screen_rng(s["i"]), photos, s["dark"])
        regions, v = fn(None, img)
        vecs.append(np.asarray(v, dtype=np.float16))
        if (s["i"] + 1) % CKPT == 0:
            np.savez(part, vecs=np.concatenate(vecs))
            vecs = [np.concatenate(vecs)]
            rate = (s["i"] + 1 - start) / (time.time() - t0)
            print(f"EMBED screen {s['i'] + 1}/{len(manifest['screens'])} {rate:.2f}/s")
    if not regions:
        from workshop.twin.pieces import make_pieces

        regions = make_pieces(Image.new("RGB", compose.SIZE))
    allv = np.concatenate(vecs)
    h = fmt.write_bench(out, manifest, allv, regions)
    print(f"EMBED done vecs={allv.shape} manifestSha256={h}")


def commit_copies(out: Path, manifest: dict) -> None:
    lock = json.loads((out / "bench.lock.json").read_text(encoding="utf-8"))
    dest = HERE / "bench-v1.lock.json"
    if dest.exists():
        old = json.loads(dest.read_text(encoding="utf-8"))
        if old["manifestSha256"] != lock["manifestSha256"]:
            print("FREEZE REFUSED: bench-v1.lock.json holds a different hash")
            sys.exit(2)
    dest.write_text(json.dumps(lock, indent=1), encoding="utf-8")
    (HERE / "manifest-v1.json").write_bytes(fmt.canonical(manifest))
    with (HERE / "licences-v1.csv").open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["id", "licence", "author", "landing", "url", "sha256"])
        for im in manifest["images"]:
            w.writerow(
                [im["id"], im["license"], im["author"], im["landing"], im["url"], im["sha256"]]
            )


def cleanup(out: Path) -> None:
    thumbs = out / "thumbs"
    thumbs.mkdir(exist_ok=True)
    cache = out / "cache"
    for p in sorted(cache.glob("*.jpg"))[:64]:
        with Image.open(p) as im:
            im.thumbnail((128, 128))
            im.save(thumbs / p.name, "JPEG", quality=80)
    shutil.rmtree(cache, ignore_errors=True)
    for p in oi.SRC.glob("*"):
        if p.name.startswith(("oidv7-", "validation-images", "test-images", "bbox_labels")):
            p.unlink()


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", required=True)
    ap.add_argument("--engine", default="onnx")
    ap.add_argument("--provider", default="dml")
    ap.add_argument("--threads", type=int, default=32)
    a = ap.parse_args(argv)
    out = Path(a.out)
    sel = json.loads((out / "selection.json").read_text(encoding="utf-8"))
    pending = out / "manifest.pending.json"
    if (out / "pieces.npz").exists() and not (out / "cache").exists():
        print("already complete")
        return 0
    state = phase_fetch(out, sel, a.threads)
    if pending.exists():
        manifest = json.loads(pending.read_text(encoding="utf-8"))
    else:
        manifest = freeze(out, sel, state)
        pending.write_bytes(fmt.canonical(manifest))
    print(f"FREEZE images={len(manifest['images'])} screens={len(manifest['screens'])}")
    if not (out / "pieces.npz").exists():
        phase_embed(out, manifest, a.engine, a.provider)
    if out.name == "v1":
        commit_copies(out, manifest)
    try:
        from workshop.twin.bench import replay_set
    except ImportError:
        replay_set = None
    if replay_set is not None and not (out / "replay").exists():
        replay_set.build(out)
    cleanup(out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
