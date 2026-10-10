"""Phone-like evaluation of concepts on the 60 composed public screens plus generated clean UI.

Pipeline = the phone's: whole + 3x6 tiles + 3 crops + YOLOE finder boxes (variant C) embedded by the
ONNX SigLIP2 image model, judged by workshop.twin.judge, then the Planner's pad / merge / cap.

    python -m workshop.twin.phone_eval --concepts-dir data/phone-kit/concepts [--v0] [--guards flat]

Reports, per concept and mode:
  falseCover   share of concept-absent screens (and of truly clean generated UI) with any mask
  recall       share of true boxes that the masks contain (>= 70 % of the box area)
  precision    share of mask area that lies on true boxes of that concept (screens with that
  concept)
  wholeScreen  share of concept-absent screens whose masks cover >= 50 % of the screen
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
from PIL import Image, ImageDraw

from workshop.twin import data, run
from workshop.twin.judge import judge

PAD = {"light": 4, "balanced": 6, "strict": 10}
DROP_SHORT = {"light": 32, "balanced": 0, "strict": 0}
MAX_MASKS = 24
SIZE = (360, 780)
MODES = ("light", "balanced", "strict")
OUT = data.CH1 / "phone-eval"


# ---------------------------------------------------------------- generated clean screens
def make_clean_screens(folder: Path) -> list[Path]:
    """Deterministic blank / loading / text-only / app-chrome screens (no objects at all)."""
    folder.mkdir(parents=True, exist_ok=True)
    w, h = SIZE
    out = {}

    def new(bg):
        im = Image.new("RGB", SIZE, bg)
        return im, ImageDraw.Draw(im)

    for name, bg in (("white", (255, 255, 255)), ("black", (0, 0, 0)), ("gray", (128, 128, 128))):
        out[f"blank-{name}"] = new(bg)[0]
    im, d = new((240, 240, 240))
    d.ellipse((150, 360, 210, 420), outline=(120, 120, 120), width=6)
    out["loading-spinner"] = im
    im, d = new((20, 20, 20))
    d.rectangle((20, 100, 340, 130), fill=(50, 50, 50))
    d.rectangle((20, 150, 250, 170), fill=(40, 40, 40))
    out["loading-skeleton"] = im
    for dark in (False, True):
        bg, fg = ((18, 18, 18), (230, 230, 230)) if dark else ((255, 255, 255), (30, 30, 30))
        im, d = new(bg)
        for i in range(38):
            d.text(
                (16, 20 + i * 19),
                f"Line {i}: quarterly report summary and meeting notes for next week",
                fill=fg,
            )
        out[f"text-{'dark' if dark else 'light'}"] = im
        im, d = new(bg)
        d.rectangle((0, 0, w, 24), fill=(60, 60, 60))
        d.rectangle((0, 24, w, 80), fill=(25, 118, 210))
        d.text((16, 44), "Settings", fill=(255, 255, 255))
        for i in range(10):
            y = 100 + i * 60
            d.ellipse((16, y, 56, y + 40), fill=(150, 150, 150))
            d.text((70, y + 6), f"Setting number {i}", fill=fg)
            d.text((70, y + 22), "description text goes here", fill=(130, 130, 130))
        d.rectangle((0, h - 56, w, h), fill=(40, 40, 40))
        out[f"chrome-{'dark' if dark else 'light'}"] = im
    paths = []
    for name, im in out.items():
        p = folder / f"clean-{name}.png"
        im.save(p)
        paths.append(p)
    return paths


def load_screens() -> list[data.Screen]:
    shown = data.load_split("public", "dev") + data.load_split("public", "test")
    folder = data.CH1 / "phone-eval-clean"
    clean = [
        data.Screen(p, {"image": p.name, "clean": True, "boxes": []})
        for p in make_clean_screens(folder)
    ]
    return sorted(shown, key=lambda s: s.image.name) + clean


# ---------------------------------------------------------------- planner port (pad, merge, cap)
def _pad(r, pct, sw, sh):
    p = min(r[2], r[3]) * pct // 100
    x0, y0 = max(0, r[0] - p), max(0, r[1] - p)
    x1, y1 = min(sw, r[0] + r[2] + p), min(sh, r[1] + r[3] + p)
    return None if x1 <= x0 or y1 <= y0 else (x0, y0, x1 - x0, y1 - y0)


def _meets(a, b):
    """Same rule as workshop.twin.planner._meets (genuine overlap, not mere touching)."""
    from workshop.twin import planner

    def d(r):
        return {"x": r[0], "y": r[1], "w": r[2], "h": r[3]}

    return planner._meets(d(a), d(b))


def _union(a, b):
    x0, y0 = min(a[0], b[0]), min(a[1], b[1])
    x1, y1 = max(a[0] + a[2], b[0] + b[2]), max(a[1] + a[3], b[1] + b[3])
    return (x0, y0, x1 - x0, y1 - y0)


def _merge(rs):
    cur = sorted(rs, key=lambda r: (r[1], r[0], r[2], r[3]))
    changed = True
    while changed:
        changed = False
        for i in range(len(cur)):
            for j in range(i + 1, len(cur)):
                if _meets(cur[i], cur[j]):
                    cur[i] = _union(cur[i], cur[j])
                    del cur[j]
                    changed = True
                    break
            if changed:
                break
    return sorted(cur, key=lambda r: (r[1], r[0], r[2], r[3]))


def plan_masks(rects, mode, sw=SIZE[0], sh=SIZE[1]):
    raw = []
    for r in rects:
        if min(r[2], r[3]) < DROP_SHORT[mode]:
            continue
        p = _pad(r, PAD[mode], sw, sh)
        if p:
            raw.append(p)
    cur = _merge(raw)
    while len(cur) > MAX_MASKS:
        best = None
        for i in range(len(cur)):
            for j in range(i + 1, len(cur)):
                u = _union(cur[i], cur[j])
                cost = u[2] * u[3] - cur[i][2] * cur[i][3] - cur[j][2] * cur[j][3]
                if best is None or cost < best[0]:
                    best = (cost, i, j)
        _, i, j = best
        cur[i] = _union(cur[i], cur[j])
        del cur[j]
        cur = _merge(cur)
    return cur


# ---------------------------------------------------------------- piece embedding (cached)
def embed(screens, no_cache=False):
    from workshop.forge.siglip2.runtime import OnnxDescriber
    from workshop.twin.finder import Finder

    desc = OnnxDescriber()
    fn = run.describer_pieces(desc, finder_boxes_fn=Finder().boxes)
    return run.embed_set(screens, fn, "phone-eval-C", use_cache=not no_cache), desc


def flat_mask(regions, screens, flat_std):
    """Per-screen list of bools: True for pieces whose pixels are near-uniform (guard `flat`)."""
    out = []
    for s in screens:
        from workshop.twin import guards

        img = Image.open(s.image)
        res = [guards.is_flat(guards.sample_luma(img, r["rect"])) for r in regions[len(out)]]
        out.append(res)
    return out


# ---------------------------------------------------------------- metrics
def _area_mask(rects, shape=(SIZE[1], SIZE[0])):
    m = np.zeros(shape, dtype=bool)
    for x, y, w, h in rects:
        m[y : y + h, x : x + w] = True
    return m


def evaluate(
    screens,
    embedded,
    ccs,
    modes=MODES,
    use_flat=False,
    use_container=None,
    use_tighten=False,
    grow=0.15,
):
    """{concept: {mode: metrics}}; guards (workshop.twin.guards) are applied after the Judge."""
    from workshop.twin import guards

    flats = flat_mask([e[0] for e in embedded], screens, guards.FLAT_STD) if use_flat else None
    res = {}
    for word, cc in ccs.items():
        res[word] = {}
        for mode in modes:
            fc_absent = fc_clean = n_absent = n_clean = whole = 0
            fc_ui = n_ui = 0
            hit = nbox = 0
            cover_on_true = cover_total = 0
            masks_per_screen = []
            for i, (screen, (regions, vecs, _sec)) in enumerate(
                zip(screens, embedded, strict=True)
            ):
                verdicts = judge(vecs, cc, mode)
                hide = [v["decision"] == "hide" for v in verdicts]
                hide = guards.apply(regions, hide, flats[i] if flats else None, use_container)
                cover = (
                    guards.tighten(regions, hide, SIZE[0] * SIZE[1], grow)
                    if use_tighten
                    else [rg["rect"] for rg, h in zip(regions, hide, strict=True) if h]
                )
                rects = [(rc["x"], rc["y"], rc["w"], rc["h"]) for rc in cover]
                masks = plan_masks(rects, mode)
                masks_per_screen.append(len(masks))
                area = _area_mask(masks)
                boxes = [
                    b["rect"]
                    for b in (screen.label or {}).get("boxes", [])
                    if b["concept"] == cc_name(cc)
                ]
                if boxes:
                    for b in boxes:
                        nbox += 1
                        sub = area[b["y"] : b["y"] + b["h"], b["x"] : b["x"] + b["w"]]
                        hit += int(sub.mean() >= 0.7) if sub.size else 0
                    truth = _area_mask([(b["x"], b["y"], b["w"], b["h"]) for b in boxes])
                    cover_on_true += int((area & truth).sum())
                    cover_total += int(area.sum())
                else:
                    n_absent += 1
                    fc_absent += int(bool(masks))
                    whole += int(area.mean() >= 0.5)
                    if screen.image.name.startswith("clean-"):
                        n_ui += 1
                        fc_ui += int(bool(masks))
                    elif (screen.label or {}).get("clean"):
                        n_clean += 1
                        fc_clean += int(bool(masks))
            res[word][mode] = {
                "falseCoverAbsent": fc_absent / max(n_absent, 1),
                "falseCoverClean": fc_clean / max(n_clean, 1),
                "falseCoverUI": fc_ui / max(n_ui, 1),
                "recall": hit / nbox if nbox else None,
                "precisionArea": cover_on_true / cover_total if cover_total else None,
                "wholeScreenAbsent": whole / max(n_absent, 1),
                "nAbsent": n_absent,
                "nClean": n_clean,
                "nBoxes": nbox,
            }
    return res


def cc_name(cc):
    return cc["conceptId"]


def table(res) -> str:
    rows = ["concept   mode      fcAbsent fcClean fcUI    recall  precArea whole50"]
    f = lambda x: "  n/a " if x is None else f"{x:6.3f}"  # noqa: E731
    for w, by in res.items():
        for m, r in by.items():
            rows.append(
                f"{w:9s} {m:8s} {f(r['falseCoverAbsent'])}  {f(r['falseCoverClean'])} "
                f"{f(r['falseCoverUI'])} "
                f"{f(r['recall'])} {f(r['precisionArea'])} {f(r['wholeScreenAbsent'])}"
            )
    return "\n".join(rows)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(prog="workshop.twin.phone_eval")
    ap.add_argument("--concepts-dir", type=Path)
    ap.add_argument("--v0", nargs="*", help="compile these words with the v0 teacher")
    ap.add_argument("--out", type=Path)
    ap.add_argument("--no-cache", action="store_true")
    ap.add_argument("--flat", action="store_true")
    ap.add_argument("--container", choices=["agree", "wins"])
    ap.add_argument(
        "--tighten", action="store_true", help="phone RegionLane.tighten: tight hides win"
    )
    ap.add_argument("--grow", type=float, default=0.15)
    a = ap.parse_args(argv)
    screens = load_screens()
    embedded, desc = embed(screens, a.no_cache)
    ccs = {}
    if a.v0:
        from workshop.twin import teacher

        for w in a.v0:
            ccs[teacher.concept_card(w)["conceptId"]] = teacher.compile_concept(
                teacher.concept_card(w), desc
            )
    if a.concepts_dir:
        for p in sorted(a.concepts_dir.glob("*.json")):
            cc = json.loads(p.read_text(encoding="utf-8"))
            ccs[cc["conceptId"]] = cc
    res = evaluate(
        screens,
        embedded,
        ccs,
        use_flat=a.flat,
        use_container=a.container,
        use_tighten=a.tighten,
        grow=a.grow,
    )
    print(table(res))
    if a.out:
        a.out.parent.mkdir(parents=True, exist_ok=True)
        a.out.write_text(json.dumps(res, indent=1), encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
