"""Run the twin end to end: pieces -> Describer -> Judge -> Findings -> 1.2's scorer.

python -m workshop.twin.run (--set synthetic|public|real --split dev|test | --images DIR)
    --concepts cats,spiders [--variant A|C] [--mode balanced] [--out DIR] [--gallery] [--no-cache]

This module is the ONLY caller of workshop.eval.score_screens. It prints the scores as JSON.
Piece fingerprints are cached in data/ch1/cache/<key>/<image stem>.npz so threshold sweeps and
reports do not re-run the model.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import time
from collections.abc import Callable
from pathlib import Path

os.environ.setdefault("HF_HUB_OFFLINE", "1")
os.environ.setdefault("YOLO_AUTOINSTALL", "False")

import numpy as np  # noqa: E402
from PIL import Image  # noqa: E402

from workshop.eval.score_screens import score  # noqa: E402
from workshop.twin import data, teacher  # noqa: E402
from workshop.twin.data import Screen  # noqa: E402
from workshop.twin.judge import judge, to_findings  # noqa: E402
from workshop.twin.pieces import crop, make_pieces  # noqa: E402

PieceFn = Callable[[Screen, Image.Image], tuple[list[dict], np.ndarray]]
CACHE = data.CH1 / "cache"
RUNS = data.CH1 / "runs"
GALLERY = data.CH1 / "gallery"
GRID = [round(0.05 * k, 2) for k in range(1, 20)]


def describer_pieces(desc, finder_boxes_fn=None, tiles: bool = True) -> PieceFn:
    """Variant A (whole + tiles + crops, by SigLIP2); variant C passes finder boxes too."""

    def fn(_screen: Screen, img: Image.Image) -> tuple[list[dict], np.ndarray]:
        boxes = finder_boxes_fn(img) if finder_boxes_fn else None
        regions = make_pieces(img, finder_boxes=boxes, tiles=tiles)
        vecs = desc.embed_images([crop(img, r["rect"]) for r in regions])
        return regions, vecs

    return fn


def _sig(path: Path) -> str:
    return hashlib.sha1(path.read_bytes()).hexdigest()[:16]


def _save_cache(file: Path, sig: str, regions: list[dict], vecs: np.ndarray, sec: float) -> None:
    file.parent.mkdir(parents=True, exist_ok=True)
    tmp = file.with_name(f"{file.stem}.{os.getpid()}.tmp.npz")
    np.savez(
        tmp,
        sig=np.array(sig),
        regions=np.frombuffer(json.dumps(regions).encode("utf-8"), dtype=np.uint8),
        vecs=np.asarray(vecs, dtype=np.float32),
        sec=np.array(sec, dtype=np.float64),
    )
    os.replace(tmp, file)


def _load_cache(file: Path, sig: str):
    try:
        with np.load(file, allow_pickle=False) as z:
            if str(z["sig"]) != sig:
                return None
            regions = json.loads(bytes(z["regions"]).decode("utf-8"))
            return regions, z["vecs"].astype(np.float32), float(z["sec"])
    except Exception:  # corrupt or truncated entry: treat as a cache miss
        return None


def embed_set(
    screens: list[Screen], piece_fn: PieceFn, cache_key: str, use_cache: bool = True
) -> list[tuple[list[dict], np.ndarray, float]]:
    """(regions, vecs, compute seconds) per screen, cached per image stem."""
    out = []
    for screen in screens:
        file = CACHE / cache_key / f"{screen.image.stem}.npz"
        sig = _sig(screen.image)
        hit = _load_cache(file, sig) if use_cache and file.is_file() else None
        if hit is None:
            img = Image.open(screen.image).convert("RGB")
            start = time.perf_counter()
            regions, vecs = piece_fn(screen, img)
            sec = time.perf_counter() - start
            vecs = np.asarray(vecs, dtype=np.float32)
            _save_cache(file, sig, regions, vecs, sec)
            hit = (regions, vecs, sec)
        out.append(hit)
    return out


def score_findings(
    screens: list[Screen], findings_by_image: dict[str, list[dict]], concept_id: str
) -> dict:
    """recall / precision / cleanFalseCover (fractions, None when undefined) via 1.2's scorer."""
    labelled = [s for s in screens if s.label is not None]
    if not labelled:
        covers = sum(
            1
            for fs in findings_by_image.values()
            for f in fs
            if f["conceptId"] == concept_id and f["decision"] == "hide"
        )
        return {
            "recall": None,
            "precision": None,
            "cleanFalseCover": None,
            "covers": covers,
            "labels": 0,
        }
    findings = [
        f
        for s in labelled
        for f in findings_by_image.get(s.image.name, [])
        if f["conceptId"] == concept_id
    ]
    res = score([s.label for s in labelled], findings)
    c = res["concepts"].get(concept_id) or {}
    return {
        "recall": c.get("recall"),
        "precision": c.get("precision"),
        "cleanFalseCover": c.get("cleanFalseCover", 0.0),
        "covers": c.get("covers", 0),
        "labels": c.get("labels", 0),
    }


def _findings_for(screens, embedded, cc, mode, lane, concept_id) -> dict[str, list[dict]]:
    out = {}
    for screen, (regions, vecs, _sec) in zip(screens, embedded, strict=True):
        verdicts = judge(vecs, cc, mode)
        out[screen.image.name] = to_findings(screen.image.name, regions, verdicts, concept_id, lane)
    return out


def _defaults(variant, piece_fn, encoder):
    """Build the Describer (and Finder for C) when the caller did not pass a piece function."""
    if piece_fn is not None:
        return piece_fn, encoder
    if variant == "B":
        raise ValueError("variant B needs a piece_fn (Finder.box_embeddings) and its encoder")
    from workshop.twin.describer import Describer

    desc = Describer()
    if variant == "C":
        from workshop.twin.finder import Finder

        return describer_pieces(desc, finder_boxes_fn=Finder().boxes), encoder or desc
    return describer_pieces(desc), encoder or desc


def _compile(concepts, ccs, encoder) -> dict[str, dict]:
    ccs = dict(ccs or {})
    for word in concepts:
        if word not in ccs:
            if encoder is None:
                raise ValueError(f"no compiled concept and no encoder for {word!r}")
            ccs[word] = teacher.compile_concept(teacher.concept_card(word), encoder)
    return ccs


def run_screens(
    screens: list[Screen],
    concepts: list[str],
    cache_key: str,
    mode: str = "balanced",
    out: Path | None = None,
    piece_fn: PieceFn | None = None,
    encoder=None,
    lane: str = "describer",
    ccs: dict[str, dict] | None = None,
    use_cache: bool = True,
    variant: str = "A",
) -> tuple[dict, dict[str, dict[str, list[dict]]]]:
    """Scores and findings for any screens. Returns (scores, {concept: {image: findings}})."""
    piece_fn, encoder = _defaults(variant, piece_fn, encoder)
    ccs = _compile(concepts, ccs, encoder)
    embedded = embed_set(screens, piece_fn, cache_key, use_cache)
    result: dict = {}
    fbc: dict[str, dict[str, list[dict]]] = {}
    for word in concepts:
        cc = ccs[word]
        found = _findings_for(screens, embedded, cc, mode, lane, cc["conceptId"])
        fbc[word] = found
        result[word] = score_findings(screens, found, cc["conceptId"])
        if out is not None:
            folder = Path(out) / word
            folder.mkdir(parents=True, exist_ok=True)
            for screen in screens:
                text = json.dumps(found[screen.image.name], indent=1) + "\n"
                (folder / f"{screen.image.stem}.json").write_text(text, encoding="utf-8")
    secs = [sec for _r, _v, sec in embedded]
    result["secPerScreen"] = float(np.mean(secs)) if secs else 0.0
    return result, fbc


def run_set(
    set_name: str,
    split: str,
    concepts: list[str],
    variant: str = "A",
    mode: str = "balanced",
    out: Path | None = None,
    piece_fn: PieceFn | None = None,
    encoder=None,
    lane: str = "describer",
    ccs: dict[str, dict] | None = None,
    use_cache: bool = True,
) -> dict:
    """{concept: scores, "secPerScreen": float}. A test-split run is logged first (3 allowed)."""
    if split == "test":
        data.log_test_run(set_name, f"variant={variant} mode={mode} concepts={','.join(concepts)}")
    screens = data.load_split(set_name, split)
    result, _ = run_screens(
        screens,
        concepts,
        f"{set_name}-{split}-{variant}",
        mode,
        out,
        piece_fn,
        encoder,
        lane,
        ccs,
        use_cache,
        variant,
    )
    return result


def sweep(
    set_name: str,
    split: str,
    concept: str,
    variant: str,
    ccs: dict[str, dict] | None,
    grid: list[float] = GRID,
    piece_fn: PieceFn | None = None,
    encoder=None,
    lane: str = "describer",
    use_cache: bool = True,
    **_ignored,
) -> list[dict]:
    """Balanced threshold swept over `grid` on cached vectors: [{t, recall, precision, ...}]."""
    if split == "test":
        raise ValueError("never tune on the test split: sweep is dev only")
    screens = data.load_split(set_name, split)
    piece_fn, encoder = _defaults(variant, piece_fn, encoder)
    cc = _compile([concept], ccs, encoder)[concept]
    embedded = embed_set(screens, piece_fn, f"{set_name}-{split}-{variant}", use_cache)
    rows = []
    for t in grid:
        cc_t = {**cc, "thresholds": {**cc["thresholds"], "balanced": t}}
        found = _findings_for(screens, embedded, cc_t, "balanced", lane, cc["conceptId"])
        s = score_findings(screens, found, cc["conceptId"])
        rows.append({"t": t, **{k: s[k] for k in ("recall", "precision", "cleanFalseCover")}})
    return rows


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        prog="python -m workshop.twin.run", description=__doc__.split("\n")[0]
    )
    src = ap.add_mutually_exclusive_group(required=True)
    src.add_argument("--set", dest="set_name", choices=data.SETS)
    src.add_argument("--images", type=Path)
    ap.add_argument("--split", choices=data.SPLITS, default="dev")
    ap.add_argument("--concepts", required=True)
    ap.add_argument("--variant", choices=["A", "C"], default="A")
    ap.add_argument("--mode", choices=["light", "balanced", "strict"], default="balanced")
    ap.add_argument("--out", type=Path)
    ap.add_argument("--gallery", action="store_true")
    ap.add_argument("--no-cache", action="store_true")
    a = ap.parse_args(argv)
    concepts = [c.strip() for c in a.concepts.split(",") if c.strip()]
    if a.images is not None:
        screens = data.load_folder(a.images)
        key = f"images-{a.images.resolve().name}-{a.variant}"
        name = f"fresh-{a.images.resolve().name}-{'+'.join(concepts)}"
    else:
        if a.split == "test":
            data.log_test_run(a.set_name, f"cli variant={a.variant} mode={a.mode}")
        screens = data.load_split(a.set_name, a.split)
        key = f"{a.set_name}-{a.split}-{a.variant}"
        name = f"{a.set_name}-{a.split}-{a.variant}-{a.mode}"
    out = a.out or RUNS / name
    result, fbc = run_screens(
        screens, concepts, key, a.mode, out, use_cache=not a.no_cache, variant=a.variant
    )
    if a.gallery:
        from workshop.twin.gallery import build_gallery

        result["gallery"] = str(build_gallery(screens, fbc, GALLERY / out.name / "index.html"))
    result["out"] = str(out)
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
