# ruff: noqa: E501  (report templates carry long f-string table rows)
"""One command for sub-phase 1.3.3: calibrate, thresholds, analysis, report and decision record.

    python -m workshop.twin.report --set synthetic|public|real [--test] [--no-cache]

Sets: `public` is a small real-photo sample (indicative baseline, NOT the frozen real test set),
`synthetic` is 1.2's drawn shapes (pipeline check only), `real` is the frozen real set (human run).
Heavy imports (torch, the other twin modules) happen inside `build`, so the renderers import light.
"""

from __future__ import annotations

import argparse
import contextlib
import hashlib
import importlib.metadata as md
import json
import os
import shutil
import subprocess
import sys
import time
from datetime import UTC, datetime
from pathlib import Path

from workshop.twin import calibrate as C

REPO = C.REPO
DATA_CH1 = C.DATA_CH1
CONCEPTS = ["cats", "spiders"]
NEW_WORD = "snakes"
ROLE = {
    "public": "public sample, not the frozen real test set (indicative baseline)",
    "synthetic": "1.2's synthetic drawn shapes: pipeline check only, the numbers mean little",
    "real": "the frozen real labelled set (the gate set)",
}
LICENCES = {
    "SigLIP2": "Apache-2.0",
    "YOLOE (Ultralytics)": "AGPL-3.0",
    "YOLOE text encoder (MobileCLIP family)": "Apple research-only (per D-001, verify)",
}
GATE_PENDING = (
    "Gate: PENDING-HUMAN (real frozen test set); fallback rule per PLAN 1.3 'If rejected'."
)


def _pct(x: float | None) -> str:
    return "n/a" if x is None else f"{100 * x:.1f}%"


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def hf_snapshot() -> Path | None:
    home = Path(os.environ.get("HF_HOME", r"D:\veil-toolchain\cache\huggingface"))
    snaps = sorted(
        (home / "hub" / "models--google--siglip2-base-patch16-224" / "snapshots").glob("*")
    )
    return snaps[-1] if snaps else None


def yoloe_file() -> Path | None:
    found = sorted((REPO / "data" / "models").glob("yoloe-*seg.pt"))
    return found[0] if found else None


def weights_files() -> list[Path]:
    snap = hf_snapshot()
    st = [snap / "model.safetensors"] if snap and (snap / "model.safetensors").exists() else []
    return st + ([yoloe_file()] if yoloe_file() else [])


def model_info(space_ids: dict[str, str]) -> dict:
    def ver(pkg: str) -> str:
        try:
            return md.version(pkg)
        except md.PackageNotFoundError:
            return "not installed"

    snap, yo = hf_snapshot(), yoloe_file()
    return {
        "torch": ver("torch") + " (CPU)",
        "transformers": ver("transformers"),
        "ultralytics": ver("ultralytics"),
        "siglip2HfCommit": snap.name if snap else "unknown",
        "yoloeFile": yo.name if yo else "unknown",
        "yoloeSha256": sha256_file(yo) if yo else "unknown",
        "spaceIds": space_ids,
        "licences": LICENCES,
    }


# --- renderers (pure) -------------------------------------------------------------------------
def _score_row(label: str, scores: dict | None) -> str:
    s = scores or {}
    return f"| {label} | {_pct(s.get('recall'))} | {_pct(s.get('precision'))} | {_pct(s.get('cleanFalseCover'))} |"


def gate_status(res: dict) -> str:
    test = res.get("test")
    if res.get("set") != "real" or not test or "balanced" not in test:
        return GATE_PENDING
    b = test["balanced"]
    cats, spi = b.get("cats", {}), b.get("spiders", {})
    ok_c = (cats.get("recall") or 0) >= 0.90 and (cats.get("cleanFalseCover") or 0) <= 0.05
    ok_s = (spi.get("recall") or 0) >= 0.80 and (spi.get("cleanFalseCover") or 0) <= 0.05
    if ok_c and ok_s:
        return (
            "Gate: PASS on the real frozen test set (cats >= 90% / <= 5%, spiders >= 80% / <= 5%)."
        )
    return (
        "Gate: FAIL on the real frozen test set; apply the PLAN 1.3 fallback "
        "(cats >= 85%, clean false-cover <= 5%)."
    )


def render_report(res: dict, others: dict[str, dict | None] | None = None) -> str:
    s = res["set"]
    concepts = list(res["dev"]["balanced"].keys())
    L = [f"# Chapter 1 SEE prototype report ({s})", ""]
    L += [f"Set: **{s}**, {ROLE.get(s, s)}. Generated {res.get('generatedUtc', 'n/a')}.", ""]
    if s != "real":
        L += [
            "> Numbers here are NOT the Chapter 1 gate. The real gate (AC-1.3-01/02/03) is PENDING-HUMAN.",
            "",
        ]
    L += [
        "| Set | Role | Balanced cats recall | Balanced clean false-cover (cats) |",
        "| --- | --- | --- | --- |",
    ]
    for name in ("public", "synthetic", "real"):
        r = (others or {}).get(name) if name != s else res
        if r is None:
            note = "PENDING-HUMAN" if name == "real" else "not run"
            L.append(f"| {name} | {ROLE[name]} | {note} | {note} |")
        else:
            b = r["dev"]["balanced"].get("cats", {})
            L.append(
                f"| {name} | {ROLE[name]} | {_pct(b.get('recall'))} | {_pct(b.get('cleanFalseCover'))} |"
            )
    L += [
        "",
        "## Score table",
        "",
        "Dev split, calibrated thresholds, per mode (recall / precision / clean false-cover).",
        "",
    ]
    L += [
        "| Mode · concept | Recall | Precision | Clean false-cover |",
        "| --- | --- | --- | --- |",
    ]
    for mode in C.MODES:
        for c in concepts:
            L.append(_score_row(f"{mode} · {c}", res["dev"][mode].get(c)))
    ordering = C.check_ordering(res["dev"])
    L += [
        "",
        "AC-1.3-04 ordering (Light <= Balanced <= Strict, recall and wrong covers): "
        + ("OK" if not ordering else "FAILED: " + "; ".join(ordering)),
        "",
    ]
    test = res.get("test")
    if test and "balanced" in test:
        L += ["Test split (Balanced only; each test run is logged, 3 allowed in total):", ""]
        L += ["| Concept | Recall | Precision | Clean false-cover |", "| --- | --- | --- | --- |"]
        for c, sc in test["balanced"].items():
            L.append(_score_row(c, sc))
        L.append("")
    elif test:
        L += [f"Test split not scored: {test.get('note', 'unknown')}", ""]
    else:
        L += ["Test split: not run (use `-Test`).", ""]

    v = res["variants"]
    L += ["## Variants", "", f"Chosen: **{res['chosenVariant']}**. {v.get('reason', '')}", ""]
    L += [
        "| Variant | Concept | Recall | Precision | Clean false-cover | t | Sec/screen | Note |",
        "| --- | --- | --- | --- | --- | --- | --- | --- |",
    ]
    for r in v.get("rows", []):
        sec = r.get("secPerScreen")
        L.append(
            f"| {r.get('variant')} | {r.get('concept')} | {_pct(r.get('recall'))} | {_pct(r.get('precision'))} "
            f"| {_pct(r.get('cleanFalseCover'))} | {r.get('t')} | {'n/a' if sec is None else f'{sec:.2f}'} "
            f"| {r.get('note', '')} |"
        )
    L += ["", "Speed is CPU torch and relative only (DV-1).", ""]

    cal, thr = res["calibration"], res["thresholds"]
    L += [
        "## Calibration and thresholds",
        "",
        "| Concept | calibrationOffset | butNotExtra | exampleThreshold |",
        "| --- | --- | --- | --- |",
    ]
    for c, v2 in cal["concepts"].items():
        L.append(
            f"| {c} | {v2.get('calibrationOffset')} | {', '.join(v2.get('butNotExtra', [])) or 'none'} | {v2.get('exampleThreshold')} |"
        )
    m = thr["modes"]
    L += [
        "",
        f"Thresholds: Light {m['light']}, Balanced {m['balanced']}, Strict {m['strict']}; margin {thr['margin']}.",
        "",
    ]
    for n in res.get("thresholdNotes", []):
        L.append(f"- {n}")
    L.append("")

    ex = res["examples"]
    L += ["## Examples gain", "", f"{ex.get('note', '')}", ""]
    if ex.get("gain") is not None:
        L += [
            f"Concept {ex.get('concept')}, {ex.get('n')} example crops (their screens excluded). Balanced recall on the remaining dev screens: "
            f"{_pct(ex.get('recallOff'))} without, {_pct(ex.get('recallOn'))} with; gain {_pct(ex.get('gain'))} (indicative). "
            f"exampleThreshold {ex.get('exampleThreshold')}. Kept: {ex.get('kept')}.",
            "",
        ]

    nw = res["newWord"]
    L += [
        "## Unseen concept",
        "",
        f"Word **{nw.get('word')}** (never tuned): card valid = {nw.get('cardValid')}, compiled card valid = {nw.get('compiledValid')}, "
        f"end to end = {nw.get('endToEnd')}. {nw.get('note', '')}",
        "",
    ]
    if nw.get("scores"):
        sc = nw["scores"]
        L += [
            f"Scores on dev with the shared thresholds and no per-word calibration (no pass/fail threshold): "
            f"covers {sc.get('covers')}, clean false-cover {_pct(sc.get('cleanFalseCover'))}, recall {_pct(sc.get('recall'))}.",
            "",
        ]

    ls = res["listSwitch"]
    L += ["## List switch", "", f"Result: **{ls.get('result')}**. {ls.get('note', '')}", ""]
    for k in ("sequence", "sameInstances", "sameWeights", "finderTest"):
        if k in ls:
            L.append(f"- {k}: {ls[k]}")
    L.append("")

    L += ["## Successes (10)", "", "| Image | Concept | Reason |", "| --- | --- | --- |"]
    L += [f"| {x['image']} | {x['concept']} | {x['reason']} |" for x in res.get("successes", [])]
    L += ["", "## Failures (10)", "", "| Image | Concept | Reason |", "| --- | --- | --- |"]
    L += [f"| {x['image']} | {x['concept']} | {x['reason']} |" for x in res.get("failures", [])]
    L += [
        "",
        "The gallery stays in git-ignored `data/ch1/gallery/`; this report cites image names only.",
        "",
    ]

    mo = res["models"]
    L += [
        "## Chosen models",
        "",
        f"- Variant {res['chosenVariant']}; spaceIds: {json.dumps(mo['spaceIds'])}",
        f"- torch {mo['torch']}, transformers {mo['transformers']}, ultralytics {mo['ultralytics']}",
        f"- SigLIP2 HF commit {mo['siglip2HfCommit']}; YOLOE {mo['yoloeFile']} sha256 {mo['yoloeSha256']}",
    ]
    L += [f"- Licence, {k}: {v3}" for k, v3 in mo["licences"].items()]
    L += ["", "## Gate", "", gate_status(res), ""]
    if s != "real":
        L += [
            "AC-1.3-01, 02, 03 and the Chapter 1 gate need `tools\\ch1_see.ps1 -Set real -Test` (HC-1.3-a).",
            "",
        ]
    return "\n".join(L)


def render_decision(res: dict) -> tuple[str, str]:
    mo, thr, cal = res["models"], res["thresholds"], res["calibration"]
    m = thr["modes"]
    title = "SEE prototype: SigLIP2 Describer with a YOLOE finder, calibrated thresholds"
    lines = [
        f"Status: proposed. Run on set **{res['set']}** ({ROLE.get(res['set'], '')}); chosen variant **{res['chosenVariant']}**.",
        "",
        f"- Models and versions: torch {mo['torch']}, transformers {mo['transformers']}, ultralytics {mo['ultralytics']}; "
        f"SigLIP2 HF commit {mo['siglip2HfCommit']}; YOLOE file {mo['yoloeFile']}, sha256 {mo['yoloeSha256']}.",
        f"- spaceIds: {json.dumps(mo['spaceIds'])}.",
        "- Licences: " + "; ".join(f"{k} {v}" for k, v in mo["licences"].items()) + ".",
        f"- Thresholds (calibrated p): Light {m['light']}, Balanced {m['balanced']}, Strict {m['strict']}; margin {thr['margin']}.",
        "- Calibration (per concept): "
        + "; ".join(
            f"{c} offset {v.get('calibrationOffset')}, butNotExtra {v.get('butNotExtra') or 'none'}, exampleThreshold {v.get('exampleThreshold')}"
            for c, v in cal["concepts"].items()
        )
        + ".",
        f"- Why this variant: {res['variants'].get('reason', '')}",
        "- Dev Balanced: "
        + "; ".join(
            f"{c} recall {_pct(s.get('recall'))}, clean false-cover {_pct(s.get('cleanFalseCover'))}"
            for c, s in res["dev"]["balanced"].items()
        )
        + ".",
        f"- {gate_status(res)}",
        "- Full numbers: docs/reports/ch1-see.md.",
    ]
    return title, "\n".join(lines)


# --- pipeline ---------------------------------------------------------------------------------
def _scores(res: dict, concept: str) -> dict:
    s = res.get(concept) or {}
    return {k: s.get(k) for k in ("recall", "precision", "cleanFalseCover")} | {
        k: s[k] for k in ("covers", "labels") if k in s
    }


def build(
    set_name: str, test: bool = False, use_cache: bool = True, concepts: list[str] | None = None
) -> dict:
    os.environ.setdefault("HF_HUB_OFFLINE", "1")
    os.environ.setdefault("YOLO_AUTOINSTALL", "False")
    from workshop.contracts.validate import validate
    from workshop.eval.score_screens import hits
    from workshop.twin import data as D
    from workshop.twin import describer as DS
    from workshop.twin import judge as J
    from workshop.twin import pieces as P
    from workshop.twin import run as R
    from workshop.twin import teacher as T
    from workshop.twin import variants as V

    concepts = concepts or CONCEPTS
    if not use_cache:
        shutil.rmtree(DATA_CH1 / "cache", ignore_errors=True)
    dev = D.load_split(set_name, "dev")
    labels = [s.label for s in dev if s.label]

    v = V.compare(set_name, "dev", concepts)
    chosen = v["chosen"]
    desc = DS.Describer()
    finder = None
    with contextlib.suppress(Exception):
        from workshop.twin.finder import Finder

        finder = Finder()
    if chosen in ("B", "C") and finder is None:
        raise RuntimeError(f"variant {chosen} chosen but the Finder could not be loaded")
    if chosen == "A":
        piece_fn, enc, lane = R.describer_pieces(desc), desc, "describer"
    elif chosen == "C":
        piece_fn, enc, lane = (
            R.describer_pieces(desc, finder_boxes_fn=finder.boxes),
            desc,
            "describer",
        )
    else:
        piece_fn, enc, lane = (lambda _s, img: finder.box_embeddings(img)), finder, "finder"
    run_kw = {"piece_fn": piece_fn, "encoder": enc, "lane": lane, "use_cache": use_cache}
    hashes_before = {p.name: sha256_file(p) for p in weights_files()}

    default_thr = C.thresholds_doc(C.DEFAULT_MODES)

    def compile_all(words, calib, thr_doc, example=None):
        out = {}
        for w in words:
            entry = {k: x for k, x in calib.get(w, {}).items() if x is not None}
            cc = T.compile_concept(
                T.concept_card(w),
                enc,
                calibration={"version": 1, "concepts": {w: entry}},
                thresholds=thr_doc,
                example_centroid=(example or {}).get(w),
            )
            out[w] = cc
        return out

    embedded = R.embed_set(dev, piece_fn, f"{set_name}-dev-{chosen}", use_cache=use_cache)

    def findings_for(shots, emb, cc, word, mode="balanced"):
        out = {}
        for s, (regions, vecs, _sec) in zip(shots, emb, strict=True):
            out[s.image.name] = J.to_findings(
                s.image.name, regions, J.judge(vecs, cc, mode), word, lane
            )
        return out

    def fit(extras):
        calib = {c: {"butNotExtra": extras.get(c, []), "exampleThreshold": None} for c in concepts}
        base = compile_all(concepts, calib, default_thr)
        for c in concepts:
            mp = {
                s.image.name: max([x["p_raw"] for x in J.judge(vecs, base[c], "balanced")] or [0.0])
                for s, (_r, vecs, _sec) in zip(dev, embedded, strict=True)
            }
            calib[c]["calibrationOffset"] = C.offset_for_concept(labels, mp, c)
        ccs1 = compile_all(concepts, calib, default_thr)
        sweeps = {c: R.sweep(set_name, "dev", c, chosen, ccs1, **run_kw) for c in concepts}
        thr, notes = C.pick_thresholds(sweeps)
        return calib, sweeps, thr, notes

    calib, sweeps, thr, notes = fit({})
    # step 3: butNotExtra from lookalike tags on false-cover dev screens, then re-sweep once
    ccs_p1 = compile_all(concepts, calib, C.thresholds_doc(thr))
    covers = {
        c: {
            img
            for img, fs in findings_for(dev, embedded, ccs_p1[c], c).items()
            if any(f["decision"] == "hide" for f in fs)
        }
        for c in concepts
    }
    extras = C.lookalike_extras(labels, covers)
    if any(extras.values()):
        calib, sweeps, thr, notes = fit(extras)
    thr_doc = C.thresholds_doc(thr)

    # step 4: examples (cats, variant A/C only: the centroid lives in the Describer space)
    ex = {"concept": "cats", "kept": False, "gain": None, "note": ""}
    try:
        if enc is not desc:
            ex["note"] = "Skipped: the chosen variant does not use the Describer space."
        else:
            from PIL import Image

            by_name = {s.image.name: s for s in dev}
            picks = C.pick_example_screens(labels, "cats", 4)
            if len(picks) < 3:
                ex["note"] = f"Skipped: only {len(picks)} usable example crops in dev."
            else:
                crops = [P.crop(Image.open(by_name[n].image).convert("RGB"), r) for n, r in picks]
                cen = C.centroid(desc.embed_images(crops))
                used = {n for n, _ in picks}
                idx = [i for i, s in enumerate(dev) if s.image.name not in used]
                rest = [dev[i] for i in idx]
                rest_emb = [embedded[i] for i in idx]
                base_cc = compile_all(["cats"], calib, thr_doc)["cats"]
                on_cc = compile_all(["cats"], calib, thr_doc, {"cats": cen})["cats"]
                off = R.score_findings(rest, findings_for(rest, rest_emb, base_cc, "cats"), "cats")
                best_t = None
                for t in C.GRID:
                    fb = findings_for(rest, rest_emb, {**on_cc, "exampleThreshold": t}, "cats")
                    if R.score_findings(rest, fb, "cats")["cleanFalseCover"] <= 0.05:
                        best_t = t
                        break
                on = {"recall": off["recall"]}
                if best_t is not None:
                    fb = findings_for(rest, rest_emb, {**on_cc, "exampleThreshold": best_t}, "cats")
                    on = R.score_findings(rest, fb, "cats")
                g = C.example_gain(off["recall"], on["recall"], best_t)
                ex |= g | {
                    "n": len(picks),
                    "exampleThreshold": best_t,
                    "note": "Centroid of dev cat crops; their screens are excluded from this measurement. Indicative only (DV-7).",
                }
                if g["kept"]:
                    calib["cats"]["exampleThreshold"] = best_t
                    import numpy as np

                    np.save(DATA_CH1 / "example-cats.npy", cen)
    except Exception as exc:  # the examples step must never sink the report
        ex["note"] = f"Examples step failed: {type(exc).__name__}: {exc}"

    # final dev scores per mode (no examples; they are a user-side add-on)
    ccs_final = compile_all(concepts, calib, thr_doc)
    dev_scores: dict[str, dict] = {}
    secs = []
    for mode in C.MODES:
        r = R.run_set(
            set_name,
            "dev",
            concepts,
            variant=chosen,
            mode=mode,
            out=DATA_CH1 / "runs" / f"{set_name}-dev-{mode}",
            ccs=ccs_final,
            **run_kw,
        )
        dev_scores[mode] = {c: _scores(r, c) for c in concepts}
        secs.append(r.get("secPerScreen"))
    out_bal = DATA_CH1 / "runs" / f"{set_name}-dev-balanced"
    fbc = {
        c: {
            p.stem + ".png": json.loads(p.read_text(encoding="utf-8"))
            for p in sorted((out_bal / c).glob("*.json"))
        }
        for c in concepts
    }
    succ, fail = C.successes_failures(labels, fbc, hits)
    with contextlib.suppress(Exception):
        from workshop.twin.gallery import build_gallery

        build_gallery(dev, fbc, DATA_CH1 / "gallery" / f"{set_name}-dev-balanced" / "index.html")

    # step 5: a word never used in tuning
    nw = {
        "word": NEW_WORD,
        "cardValid": False,
        "compiledValid": False,
        "endToEnd": False,
        "scores": None,
        "note": "",
    }
    try:
        card = T.concept_card(NEW_WORD)
        validate("Concept", card)
        nw["cardValid"] = True
        ncc = compile_all([NEW_WORD], {}, thr_doc)[NEW_WORD]
        validate("CompiledConcept", ncc)
        nw["compiledValid"] = True
        r = R.run_set(
            set_name,
            "dev",
            [NEW_WORD],
            variant=chosen,
            mode="balanced",
            out=DATA_CH1 / "runs" / f"{set_name}-dev-new",
            ccs={NEW_WORD: ncc},
            **run_kw,
        )
        nw["scores"] = _scores(r, NEW_WORD) | {"covers": (r.get(NEW_WORD) or {}).get("covers", 0)}
        nw["endToEnd"] = True
        nw["note"] = "Tuned global thresholds, calibrationOffset 0 (never calibrated)."
    except Exception as exc:
        nw["note"] = f"Failed: {type(exc).__name__}: {exc}"

    # step 6: list switch (same Describer and Finder instances, same weights) + the 1.3.2 test
    ids_before = (id(desc), id(finder))
    seq = []
    ls = {"result": "FAIL", "note": ""}
    try:
        for w in ("cats", "spiders", NEW_WORD, "bicycles"):
            cc = compile_all([w], {}, thr_doc)[w]
            J.judge(embedded[0][1], cc, "balanced")
            seq.append(w)
        after = {p.name: sha256_file(p) for p in weights_files()}
        same_inst = ids_before == (id(desc), id(finder))
        same_w = after == hashes_before
        ls = {
            "sequence": " -> ".join(seq),
            "sameInstances": same_inst,
            "sameWeights": same_w,
            "result": "PASS" if same_inst and same_w else "FAIL",
            "note": "One Describer and one Finder, no reload, no re-export; weight files unchanged (sha256).",
        }
    except Exception as exc:
        ls["note"] = f"Failed: {type(exc).__name__}: {exc}"
    t_file = REPO / "workshop" / "twin" / "tests" / "test_finder.py"
    if t_file.exists():
        try:
            pr = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "pytest",
                    str(t_file),
                    "-q",
                    "-k",
                    "switch",
                    "-p",
                    "no:cacheprovider",
                ],
                capture_output=True,
                text=True,
                timeout=900,
                cwd=REPO,
            )
            ls["finderTest"] = {
                0: "1.3.2 test_finder list-switch PASS",
                5: "no list-switch test found",
            }.get(pr.returncode, f"1.3.2 test_finder FAIL (exit {pr.returncode})")
        except Exception as exc:
            ls["finderTest"] = f"not run: {type(exc).__name__}"
    else:
        ls["finderTest"] = "test_finder.py not present"

    # test split: one logged run, Balanced only (the gate mode)
    test_block = None
    if test:
        try:
            r = R.run_set(
                set_name,
                "test",
                concepts,
                variant=chosen,
                mode="balanced",
                out=DATA_CH1 / "runs" / f"{set_name}-test-balanced",
                ccs=ccs_final,
                **run_kw,
            )
            test_block = {"balanced": {c: _scores(r, c) for c in concepts}}
        except RuntimeError as exc:  # the 3-run guard
            test_block = {"note": f"refused: {exc}"}

    space_ids = {"describer": DS.SPACE_ID, "finder": getattr(finder, "space_id", "not loaded")}
    res = {
        "set": set_name,
        "generatedUtc": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "variants": v,
        "chosenVariant": chosen,
        "calibration": C.calibration_doc(set_name, chosen, calib),
        "thresholds": thr_doc,
        "thresholdNotes": notes,
        "dev": dev_scores,
        "secPerScreen": [x for x in secs if x is not None],
        "examples": ex,
        "newWord": nw,
        "listSwitch": ls,
        "test": test_block,
        "successes": succ,
        "failures": fail,
        "models": model_info(space_ids),
    }
    return res


def write_outputs(res: dict) -> str:
    s = res["set"]
    C.CALIB_PATH.write_text(json.dumps(res["calibration"], indent=2) + "\n", encoding="utf-8")
    C.THRESH_PATH.write_text(json.dumps(res["thresholds"], indent=2) + "\n", encoding="utf-8")
    DATA_CH1.mkdir(parents=True, exist_ok=True)
    (DATA_CH1 / f"results-{s}.json").write_text(json.dumps(res, indent=2) + "\n", encoding="utf-8")
    others = {}
    for name in ("public", "synthetic", "real"):
        p = DATA_CH1 / f"results-{name}.json"
        if name != s and p.exists():
            with contextlib.suppress(ValueError, KeyError):
                others[name] = json.loads(p.read_text(encoding="utf-8"))
    C.REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    C.REPORT_PATH.write_text(render_report(res, others) + "\n", encoding="utf-8", newline="\n")
    title, body = render_decision(res)
    return C.write_decision_block(
        C.DECISIONS_PATH, title, body, datetime.now(UTC).strftime("%Y-%m-%d")
    )


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="python -m workshop.twin.report")
    p.add_argument("--set", default="synthetic", choices=["synthetic", "public", "real"])
    p.add_argument(
        "--test", action="store_true", help="also score the test split (logged, max 3 runs)"
    )
    p.add_argument("--no-cache", action="store_true")
    p.add_argument("--concepts", default=",".join(CONCEPTS))
    args = p.parse_args(argv)
    t0 = time.time()
    res = build(args.set, args.test, not args.no_cache, args.concepts.split(","))
    did = write_outputs(res)
    print(
        json.dumps(
            {
                "set": args.set,
                "chosenVariant": res["chosenVariant"],
                "decision": did,
                "thresholds": res["thresholds"]["modes"],
                "sec": round(time.time() - t0, 1),
            }
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
