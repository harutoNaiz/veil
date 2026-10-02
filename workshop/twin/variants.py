"""Compare the three finder variants (SPEC 1.3.2) and pick one.

A = SigLIP2 on tiles and crops; B = YOLOE per-box fingerprints judged against YOLOE's own text
encoder; C = YOLOE boxes judged by SigLIP2 crops plus the A pieces. Each (variant, concept) row is
the sweep's best point: highest recall with clean false-cover <= 5% (raw p, offsets 0).

    python -m workshop.twin.variants --set synthetic --split dev --concepts cats,spiders
"""

from __future__ import annotations

import argparse
import json
import statistics
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
CH1 = REPO / "data" / "ch1"
LIMIT = 0.05  # clean false-cover ceiling for the chosen point
TIE = 0.005  # recall difference treated as a tie (the faster variant wins)


def _best_point(points: list[dict]) -> tuple[dict, bool]:
    """Highest recall with cleanFalseCover <= LIMIT; else the lowest-false-cover point (False)."""

    def num(v):
        return -1.0 if v is None else float(v)

    ok = [p for p in points if num(p["cleanFalseCover"]) <= LIMIT]
    if ok:
        return max(ok, key=lambda p: (num(p["recall"]), num(p["precision"]), -p["t"])), True
    return min(points, key=lambda p: (num(p["cleanFalseCover"]), -num(p["recall"]))), False


def choose(rows: list[dict]) -> tuple[str | None, str]:
    """`chosen` = best mean recall at <= 5% clean false-cover, ties to the faster variant."""
    by_variant: dict[str, list[dict]] = {}
    for r in rows:
        if r.get("recall") is not None and not r["note"].startswith("not run"):
            by_variant.setdefault(r["variant"], []).append(r)
    if not by_variant:
        return None, "no variant ran"
    stats = {}
    for v, rs in by_variant.items():
        within = all(r["cleanFalseCover"] <= LIMIT for r in rs)
        recall = round(statistics.mean(r["recall"] for r in rs), 3)
        secs = [r["secPerScreen"] for r in rs if r.get("secPerScreen") is not None]
        stats[v] = (within, recall, statistics.mean(secs) if secs else float("inf"))
    pool = {v: s for v, s in stats.items() if s[0]} or stats  # variants within 5% everywhere first
    top = max(s[1] for s in pool.values())
    tied = [v for v, s in pool.items() if top - s[1] < TIE]
    chosen = min(tied, key=lambda v: pool[v][2])
    desc = ", ".join(
        f"{v}: recall {s[1]:.3f}, {s[2]:.2f} s/screen{'' if s[0] else ' (over 5% false-cover)'}"
        for v, s in sorted(stats.items())
    )
    why = "best mean recall at <=5% clean false-cover"
    if pool is stats and not all(s[0] for s in stats.values()):
        why = "no variant reached <=5% clean false-cover for every concept; best available"
    if len(tied) > 1:
        why += f"; {', '.join(sorted(tied))} tied within {TIE}, the faster one won"
    return chosen, f"{chosen} chosen: {why} ({desc})"


def _sec(set_name: str, split: str, variant: str) -> float | None:
    """Mean `sec` over the variant's cache entries (compute seconds of each screen's pieces)."""
    import numpy as np

    folder = CH1 / "cache" / f"{set_name}-{split}-{variant}"
    secs = []
    for f in folder.glob("*.npz"):
        try:
            with np.load(f, allow_pickle=False) as z:
                secs.append(float(z["sec"]))
        except (OSError, ValueError, KeyError):
            continue
    return statistics.mean(secs) if secs else None


def _not_run(variant: str, concepts: list[str], reason: str) -> list[dict]:
    return [
        {
            "variant": variant, "concept": c, "recall": None, "precision": None,
            "cleanFalseCover": None, "t": None, "secPerScreen": None, "note": f"not run: {reason}",
        }
        for c in concepts
    ]  # fmt: skip


def _run_variant(set_name, split, concepts, variant, ccs, piece_fn, encoder, lane, use_cache):
    from workshop.twin import run

    rows = []
    for i, c in enumerate(concepts):
        # --no-cache re-embeds once (first concept); later concepts reuse those fresh vectors
        pts = run.sweep(
            set_name, split, c, variant, ccs, piece_fn=piece_fn, encoder=encoder, lane=lane,
            use_cache=use_cache or i > 0,
        )  # fmt: skip
        best, ok = _best_point(pts)
        rows.append({
            "variant": variant, "concept": c, "recall": best["recall"],
            "precision": best["precision"], "cleanFalseCover": best["cleanFalseCover"],
            "t": best["t"], "secPerScreen": None,
            "note": "" if ok else "no point at <=5% clean false-cover; lowest shown",
        })  # fmt: skip
    sec = _sec(set_name, split, variant)
    for r in rows:
        r["secPerScreen"] = sec
    return rows


def compare(set_name: str, split: str, concepts: list[str], use_cache: bool = True) -> dict:
    """{"rows": [...], "chosen", "reason"}; also written to data/ch1/variants-<set>.json."""
    from workshop.twin import data, run, teacher

    concepts = list(concepts)
    rows: list[dict] = []
    notes: dict[str, str] = {}
    desc = finder = None
    try:
        from workshop.twin.describer import Describer

        desc = Describer()
    except Exception as exc:  # weights missing or unreadable
        notes["A"] = notes["C"] = f"describer unavailable ({type(exc).__name__}: {exc})"
    try:
        from workshop.twin.finder import Finder

        finder = Finder()
    except Exception as exc:
        notes["B"] = f"finder unavailable ({type(exc).__name__}: {exc})"
        notes.setdefault("C", notes["B"])

    def cards(enc):
        return {
            c: teacher.compile_concept(teacher.concept_card(c), enc, None, None) for c in concepts
        }

    if desc is not None:
        ccs = cards(desc)
        rows += _run_variant(set_name, split, concepts, "A", ccs, run.describer_pieces(desc), desc,
                             "describer", use_cache)  # fmt: skip
    else:
        rows += _not_run("A", concepts, notes["A"])
    if desc is not None and finder is not None:
        rows += _run_variant(set_name, split, concepts, "C", ccs,
                             run.describer_pieces(desc, finder_boxes_fn=finder.boxes), desc,
                             "describer", use_cache)  # fmt: skip
    else:
        rows += _not_run("C", concepts, notes.get("C", "no finder"))
    if finder is not None:
        try:
            first = data.load_split(set_name, split)[0]
            from PIL import Image

            finder.box_embeddings(
                Image.open(first.image).convert("RGB")
            )  # probe: raises if unsupported

            def b_pieces(_screen, img):
                return finder.box_embeddings(img)

            rows += _run_variant(set_name, split, concepts, "B", cards(finder), b_pieces, finder,
                                 "finder", use_cache)  # fmt: skip
        except NotImplementedError as exc:
            rows += _not_run("B", concepts, f"box embeddings: {exc}")
    else:
        rows += _not_run("B", concepts, notes["B"])
    rows.sort(key=lambda r: (r["variant"], r["concept"]))
    chosen, reason = choose(rows)
    out = {"set": set_name, "split": split, "concepts": concepts, "rows": rows, "chosen": chosen,
           "reason": reason}  # fmt: skip
    CH1.mkdir(parents=True, exist_ok=True)
    (CH1 / f"variants-{set_name}.json").write_text(json.dumps(out, indent=2), encoding="utf-8")
    return out


def markdown(result: dict) -> str:
    def f(v, pct=True):
        return "-" if v is None else (f"{v * 100:.1f}%" if pct else f"{v:.2f}")

    lines = ["| variant | concept | recall | precision | clean false-cover | t | s/screen | note |",
             "| --- | --- | --- | --- | --- | --- | --- | --- |"]  # fmt: skip
    for r in result["rows"]:
        lines.append(
            f"| {r['variant']} | {r['concept']} | {f(r['recall'])} | {f(r['precision'])} | "
            f"{f(r['cleanFalseCover'])} | {f(r['t'], False)} | "
            f"{f(r['secPerScreen'], False)} | {r['note']} |"
        )
    lines.append("")
    lines.append(f"chosen: {result['chosen']} - {result['reason']}")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument(
        "--set", dest="set_name", required=True, choices=["synthetic", "public", "real"]
    )
    ap.add_argument("--split", default="dev", choices=["dev", "test"])
    ap.add_argument("--concepts", default="cats,spiders")
    ap.add_argument("--no-cache", action="store_true")
    a = ap.parse_args(argv)
    result = compare(a.set_name, a.split, [c.strip() for c in a.concepts.split(",") if c.strip()],
                     use_cache=not a.no_cache)  # fmt: skip
    print(markdown(result))
    return 0


if __name__ == "__main__":
    sys.exit(main())
