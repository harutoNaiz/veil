"""PT-3.1 harness: run variant C with the torch or the ONNX engines, then compare decisions.

  python -m workshop.forge.proof --engine torch|onnx --out <dir> [--concepts cats,spiders]
  python -m workshop.forge.proof --compare <dirA> <dirB>
Each engine run writes <out>/summary.json: {screen: {concept: covered}} plus per-region findings.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from workshop.forge.common import FORGE_DATA

PT_DIR = FORGE_DATA / "pt-3.1"
FRESH = Path("data/ch1/fresh/_verify-smoke")


def decisions(findings: dict[str, dict[str, list[dict]]]) -> dict[str, bool]:
    """{"<screen>|<concept>": covered?} from {concept: {image: [finding]}}."""
    out = {}
    for concept, by_image in findings.items():
        for image, items in by_image.items():
            out[f"{image}|{concept}"] = len(items) > 0
    return out


def _iou(a: dict, b: dict) -> float:
    ax1, ay1, bx1, by1 = a["x"] + a["w"], a["y"] + a["h"], b["x"] + b["w"], b["y"] + b["h"]
    iw = max(0, min(ax1, bx1) - max(a["x"], b["x"]))
    ih = max(0, min(ay1, by1) - max(a["y"], b["y"]))
    inter = iw * ih
    union = a["w"] * a["h"] + b["w"] * b["h"] - inter
    return inter / union if union > 0 else 0.0


def region_agreement(a: dict[str, list[dict]], b: dict[str, list[dict]]) -> float:
    """Per-region: matched (same screen+concept, IoU >= 0.9) / max(#a, #b); both empty = agree."""
    matched = total = 0
    for key in sorted(set(a) | set(b)):
        ra, rb = list(a.get(key, [])), list(b.get(key, []))
        used: set[int] = set()
        for x in ra:
            for j, y in enumerate(rb):
                if j not in used and _iou(x, y) >= 0.9:
                    used.add(j)
                    matched += 1
                    break
        total += max(len(ra), len(rb))
    return matched / total if total else 1.0


def compare(a: dict, b: dict, threshold: float = 0.98) -> dict:
    """a, b: summaries {"decisions": {...}, "rects": {"screen|concept": [rect]}}."""
    da, db = a["decisions"], b["decisions"]
    keys = sorted(set(da) | set(db))
    same = sum(1 for k in keys if da.get(k) == db.get(k))
    agree = same / len(keys) if keys else 1.0
    return {
        "decisions": len(keys),
        "same": same,
        "agreement": agree,
        "threshold": threshold,
        "pass": agree >= threshold,
        "differences": [k for k in keys if da.get(k) != db.get(k)],
        "regionAgreement": region_agreement(a.get("rects", {}), b.get("rects", {})),
    }


def _rects(findings) -> dict[str, list[dict]]:
    out = {}
    for concept, by_image in findings.items():
        for image, items in by_image.items():
            out[f"{image}|{concept}"] = [f["rect"] for f in items if "rect" in f]
    return out


def run_engine(engine: str, out: Path, concepts: list[str], gallery: bool = True) -> dict:
    from workshop.twin import data, run

    screens = [
        *data.load_split("public", "dev"),
        *data.load_split("synthetic", "dev"),
        *data.load_folder(FRESH),
    ]
    if engine == "onnx":
        from workshop.forge.siglip2.runtime import OnnxDescriber
        from workshop.forge.yoloe.runtime import OnnxFinder

        desc = OnnxDescriber()
        piece_fn = run.describer_pieces(desc, finder_boxes_fn=OnnxFinder().boxes)
        kw = {"piece_fn": piece_fn, "encoder": desc}
    else:
        kw = {}
    out.mkdir(parents=True, exist_ok=True)
    scores, fbc = run.run_screens(
        screens, concepts, f"pt31-{engine}", "balanced", out / "findings", use_cache=False,
        variant="C", **kw,
    )  # fmt: skip
    summary = {
        "engine": engine,
        "concepts": concepts,
        "decisions": decisions(fbc),
        "rects": _rects(fbc),
    }
    (out / "summary.json").write_text(json.dumps(summary, indent=1) + "\n", encoding="utf-8")
    (out / "scores.json").write_text(json.dumps(scores, indent=1, default=str) + "\n", "utf-8")
    if gallery:
        from workshop.twin.gallery import build_gallery

        print("gallery", build_gallery(screens, fbc, out / "gallery" / "index.html"))
    return summary


def write_compare(dir_a: Path, dir_b: Path, out_dir: Path = PT_DIR) -> dict:
    a = json.loads((Path(dir_a) / "summary.json").read_text(encoding="utf-8"))
    b = json.loads((Path(dir_b) / "summary.json").read_text(encoding="utf-8"))
    res = compare(a, b)
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "diff.json").write_text(json.dumps(res, indent=1) + "\n", encoding="utf-8")
    lines = [
        "# PT-3.1 decision comparison",
        "",
        f"- A: {dir_a}",
        f"- B: {dir_b}",
        f"- decisions: {res['decisions']}, same: {res['same']}",
        f"- agreement: {res['agreement']:.4f} (need >= {res['threshold']}) "
        f"-> {'PASS' if res['pass'] else 'FAIL'}",
        f"- per-region agreement (IoU >= 0.9, information only): {res['regionAgreement']:.4f}",
        "",
        "## Differing decisions",
        *(f"- {k}" for k in res["differences"]),
    ]
    (out_dir / "diff.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    return res


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--engine", choices=["torch", "onnx"])
    ap.add_argument("--out", type=Path)
    ap.add_argument("--concepts", default="cats,spiders")
    ap.add_argument("--no-gallery", action="store_true")
    ap.add_argument("--compare", nargs=2, type=Path, metavar=("A", "B"))
    a = ap.parse_args(argv)
    if a.compare:
        res = write_compare(*a.compare)
        print(f"agreement {res['agreement']:.4f} {'PASS' if res['pass'] else 'FAIL'}")
        return 0 if res["pass"] else 1
    if not a.engine or not a.out:
        ap.error("need --engine and --out, or --compare")
    concepts = [c.strip() for c in a.concepts.split(",") if c.strip()]
    run_engine(a.engine, a.out, concepts, gallery=not a.no_gallery)
    return 0


if __name__ == "__main__":
    sys.exit(main())
