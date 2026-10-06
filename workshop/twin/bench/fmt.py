"""Frozen-benchmark file format: canonical manifest, lock, pieces.npz, labels."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

import numpy as np

PIECES_PER_SCREEN = 22


@dataclass
class Bench:
    manifest: dict
    lock: dict
    vecs: np.ndarray
    regions: list[dict]
    dir: Path


def canonical(obj: dict) -> bytes:
    return json.dumps(obj, sort_keys=True, separators=(",", ":")).encode("utf-8")


def manifest_hash(obj: dict) -> str:
    return hashlib.sha256(canonical(obj)).hexdigest()


def write_bench(dir: Path, manifest: dict, vecs: np.ndarray, regions: list[dict]) -> str:
    dir = Path(dir)
    dir.mkdir(parents=True, exist_ok=True)
    h = manifest_hash(manifest)
    (dir / "manifest.json").write_bytes(canonical(manifest))
    np.savez(dir / "pieces.npz", vecs=np.asarray(vecs, dtype=np.float16))
    (dir / "regions.json").write_text(json.dumps(regions), encoding="utf-8")
    words = manifest.get("words", [])
    lock = {
        "manifestSha256": h,
        "frozenAt": datetime.now(UTC).isoformat(timespec="seconds"),
        "words": sum(1 for w in words if w.get("split") == "test"),
        "devWords": sum(1 for w in words if w.get("split") == "dev"),
        "images": len(manifest.get("images", [])),
        "screens": len(manifest.get("screens", [])),
    }
    (dir / "bench.lock.json").write_text(json.dumps(lock, indent=1), encoding="utf-8")
    return h


def load_bench(dir: Path) -> Bench:
    dir = Path(dir)
    raw = (dir / "manifest.json").read_bytes()
    manifest = json.loads(raw.decode("utf-8"))
    lock = json.loads((dir / "bench.lock.json").read_text(encoding="utf-8"))
    if manifest_hash(manifest) != lock["manifestSha256"]:
        raise ValueError("bench manifest hash does not match lock (tampered or stale)")
    with np.load(dir / "pieces.npz") as z:
        vecs = z["vecs"]
    regions = json.loads((dir / "regions.json").read_text(encoding="utf-8"))
    return Bench(manifest, lock, vecs, regions, dir)


def screen_vecs(b: Bench, i: int) -> np.ndarray:
    n = PIECES_PER_SCREEN
    return b.vecs[i * n : (i + 1) * n].astype(np.float32)


def screen_name(i: int) -> str:
    return f"s{i:05d}.png"


def labels_for(b: Bench, word: str) -> list[dict]:
    """ScreenLabels: one box per card positive for `word`; clean = no box."""
    pos = {im["id"] for im in b.manifest["images"] if word in im.get("pos", [])}
    out = []
    for s in b.manifest["screens"]:
        boxes = [
            {
                "rect": {k: int(r[k]) for k in ("x", "y", "w", "h")},
                "concept": word,
                "kind": "photo",
                "scope": "object",
            }
            for cid, r in zip(s["cards"], s["photoRects"], strict=True)
            if cid in pos
        ]
        out.append(
            {
                "contractVersion": "1.0",
                "image": screen_name(s["i"]),
                "width": 360,
                "height": 780,
                "clean": not boxes,
                "boxes": boxes,
                "labeller": "openimages",
            }
        )
    return out
