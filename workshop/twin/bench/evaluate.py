"""7.2.2 benchmark evaluation (HEAVY when run for real: loads the text encoder; run it alone).

python -m workshop.twin.bench.evaluate --bench DIR --bank DIR --split dev|test
    [--params F] [--note S] [--dry] [--words a,b]
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

from workshop.contracts.validate import REPO_ROOT
from workshop.eval import score_screens
from workshop.twin import autocal, judge
from workshop.twin.bench import attempts, fmt

HERE = Path(__file__).resolve().parent
MODES = ("light", "balanced", "strict")
SCREEN_AREA = 360 * 780
SMALL_FRAC = 0.12
DRAWING_TAGS = {"Drawing", "Cartoon", "Illustration", "Painting", "Toy", "Art"}
RECALL_MIN = 0.90
CLEAN_FC_MAX = 0.05
GATE_LINE = "at least 90% of benchmark words reach recall >= 90% at clean false-cover <= 5%"


def apply_params(path: Path) -> None:
    p = json.loads(Path(path).read_text(encoding="utf-8"))
    autocal.TEMPLATES[:] = p["templates"]
    autocal.Q_PER_MILLE.update(p["quantilesPerMille"])
    autocal.K_COMPETITORS = int(p["k"])
    autocal.AUTO_MARGIN = float(p["margin"])


def classify(missed: list[dict], fcs: list[dict], recall_ok: bool, fc_ok: bool) -> list[str]:
    """Failure classes of a failing word. missed: {small, drawing}; fcs: {lookalike}."""
    out: list[str] = []
    if not recall_ok and missed:
        if sum(m["small"] for m in missed) * 2 >= len(missed):
            out.append("small")
        if sum(m["drawing"] for m in missed) * 2 >= len(missed):
            out.append("drawing")
    if not fc_ok and fcs:
        if sum(f["lookalike"] for f in fcs) * 2 > len(fcs):
            out.append("lookalike")
        else:
            out.append("labels?")
    if not out and not (recall_ok and fc_ok):
        out.append("other")
    return out


def eval_word(b: fmt.Bench, word: str, cc: dict, judge_fn=judge.judge) -> dict:
    man = b.manifest
    imgs = {im["id"]: im for im in man["images"]}
    cid = cc["conceptId"]
    labels = []
    for lb in fmt.labels_for(b, word):
        boxes = [{**bx, "concept": cid} for bx in lb["boxes"]]
        labels.append({**lb, "boxes": boxes})
    res: dict = {"word": word, "modes": {}}
    per: dict[int, list[dict]] = {}
    for mode in MODES:
        findings = []
        for s in man["screens"]:
            i = s["i"]
            verdicts = judge_fn(fmt.screen_vecs(b, i), cc, mode)
            fs = [
                f
                for f in judge.to_findings(
                    fmt.screen_name(i), b.regions, verdicts, cid, "describer"
                )
                if f["decision"] == "hide"
            ]
            findings += fs
            if mode == "balanced":
                per[i] = fs
        sc = score_screens.score(labels, findings)
        c = sc["concepts"].get(cid, {})
        res["modes"][mode] = {
            "recall": c.get("recall"),
            "precision": c.get("precision"),
            "cleanFalseCover": sc["cleanFalseCover"],
        }
    look = look_hit = npos = 0
    missed: list[dict] = []
    fcs: list[dict] = []
    for s in man["screens"]:
        i = s["i"]
        for cardid, r in zip(s["cards"], s["photoRects"], strict=True):
            im = imgs[cardid]
            covered = any(score_screens._inter(f["rect"], r) > 0 for f in per[i])
            if word in im.get("pos", []):
                npos += 1
                if not any(score_screens.hits(f["rect"], r) for f in per[i]):
                    missed.append(
                        {
                            "small": r["w"] * r["h"] / SCREEN_AREA < SMALL_FRAC,
                            "drawing": bool(DRAWING_TAGS & set(im.get("tags", []))),
                        }
                    )
                continue
            is_look = word in im.get("neg", []) or f"look:{word}" in im.get("roles", [])
            if is_look:
                look += 1
                look_hit += covered
            if covered:
                fcs.append({"lookalike": is_look})
    bal = res["modes"]["balanced"]
    recall_ok = bal["recall"] is not None and bal["recall"] >= RECALL_MIN
    fc_ok = bal["cleanFalseCover"] <= CLEAN_FC_MAX
    res["nPos"] = npos
    res["lookalikeFC"] = look_hit / look if look else None
    res["passes"] = recall_ok and fc_ok
    res["classes"] = [] if res["passes"] else classify(missed, fcs, recall_ok, fc_ok)
    return res


def evaluate_bench(b: fmt.Bench, words: list[dict], compile_fn, judge_fn=judge.judge) -> dict:
    rows = []
    for w in words:
        t0 = time.perf_counter()
        cc = compile_fn(w["word"])
        ms = (time.perf_counter() - t0) * 1000
        r = eval_word(b, w["word"], cc, judge_fn)
        r.update(category=w.get("category", ""), split=w.get("split", ""), compileMs=round(ms, 1))
        rows.append(r)
    passing = sum(r["passes"] for r in rows)
    cats: dict[str, list[int]] = {}
    for r in rows:
        c = cats.setdefault(r["category"], [0, 0])
        c[0] += r["passes"]
        c[1] += 1
    return {
        "words": rows,
        "passing": passing,
        "n": len(rows),
        "gateShare": passing / len(rows) if rows else 0.0,
        "categories": {k: v[0] / v[1] for k, v in cats.items()},
    }


def _f(x) -> str:
    return "n/a" if x is None else f"{x:.2f}"


def write_report(path: Path, b: fmt.Bench, res: dict, log: list[dict]) -> None:
    share = res["gateShare"]
    man = b.manifest
    lines = [
        "# Chapter 7 benchmark: name anything",
        "",
        f"Dataset: {man.get('dataset', '')}; label licence {man.get('labelLicence', '')}; "
        "images CC BY 2.0 (author and landing page per image in licences-v1.csv).",
        f"Manifest sha256: `{b.lock['manifestSha256']}`",
        "",
        f"## Gate: {'PASS' if share >= 0.90 else 'FAIL'}",
        "",
        f"Threshold (verbatim): {GATE_LINE}.",
        f"gateShare = {share:.3f} ({res['passing']}/{res['n']} words).",
        "",
        "## Per word (cells are recall/precision/cleanFC)",
        "",
        "| word | category | nPos | light | balanced | strict | lookalikeFC | compile ms | pass |",
        "|---|---|---|---|---|---|---|---|---|",
    ]
    for r in res["words"]:
        cells = [
            "/".join(_f(r["modes"][m][k]) for k in ("recall", "precision", "cleanFalseCover"))
            for m in MODES
        ]
        lines.append(
            f"| {r['word']} | {r['category']} | {r['nPos']} | {' | '.join(cells)} | "
            f"{_f(r['lookalikeFC'])} | {r['compileMs']} | {'yes' if r['passes'] else 'no'} |"
        )
    lines += ["", "## Per category share", ""]
    lines += [f"- {k}: {v:.2f}" for k, v in sorted(res["categories"].items())]
    lines += ["", "## Failure classes", ""]
    fails = [r for r in res["words"] if not r["passes"]]
    lines += [f"- {r['word']}: {', '.join(r['classes'])}" for r in fails] or ["- none"]
    lines += ["", "## Attempts", "", "| n | note | params sha | gateShare | passing |"]
    lines.append("|---|---|---|---|---|")
    results = {r["n"]: r for r in log if "gateShare" in r}
    for r in log:
        if "at" in r:
            g = results.get(r["n"], {})
            lines.append(
                f"| {r['n']} | {r['note']} | {r['paramsSha256'][:12]} | "
                f"{g.get('gateShare', '')} | {g.get('passing', '')} |"
            )
    if share < 0.90:
        lines += [
            "",
            "## Gate missed: fallback options (human decision)",
            "",
            "- (a) YOLOE second opinion",
            "- (b) a larger phone image model",
            "- (c) narrow the promise to the passing word classes",
        ]
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text("\n".join(lines) + "\n", encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="python -m workshop.twin.bench.evaluate")
    ap.add_argument("--bench", type=Path, required=True)
    ap.add_argument("--bank", type=Path, required=True)
    ap.add_argument("--split", choices=("dev", "test"), required=True)
    ap.add_argument("--params", type=Path, default=HERE / "params.json")
    ap.add_argument("--note", default="")
    ap.add_argument("--dry", action="store_true")
    ap.add_argument("--words", default="")
    a = ap.parse_args(argv)
    try:
        b = fmt.load_bench(a.bench)
        attempts.check_dry(b.manifest.get("name", ""), a.dry)
    except (ValueError, OSError, KeyError, attempts.DryRefused) as exc:
        print(f"REFUSED {exc}")
        return 2
    name = b.manifest.get("name", "")
    apply_params(a.params)
    words = [w for w in b.manifest["words"] if w.get("split") == a.split]
    if a.words:
        keep = {x.strip() for x in a.words.split(",") if x.strip()}
        words = [w for w in words if w["word"] in keep]
    from workshop.twin.bank import bankio

    bank = bankio.read_bank(a.bank / "bank.bin")
    vocab = bankio.read_vocab(a.bank)
    logged = a.split == "test" and not a.dry
    n = 0
    if logged:
        try:
            sha = attempts.params_sha(a.params)
            n = attempts.start(b.lock["manifestSha256"], bank.bank_id, sha, a.note)
        except attempts.Exhausted:
            print("ATTEMPTS EXHAUSTED")
            return 2
    from workshop.forge.siglip2.runtime import OnnxDescriber

    enc = OnnxDescriber()
    res = evaluate_bench(b, words, lambda w: autocal.compile_auto(w, enc, bank, vocab))
    out = REPO_ROOT / "data" / "bench" / f"eval-{name}-{a.split}-{n}.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(res, indent=1), encoding="utf-8")
    if logged:
        attempts.finish(n, res["gateShare"], res["passing"])
    if a.split == "test":
        rep = out.with_suffix(".md")
        if not a.dry:
            rep = REPO_ROOT / "docs" / "reports" / "ch7-name-anything.md"
        write_report(rep, b, res, attempts.read())
    print(f"BENCH gateShare={res['gateShare']:.3f} passing={res['passing']}/{res['n']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
