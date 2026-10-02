"""Calibration, thresholds and decision-record maths for the SEE prototype (sub-phase 1.3.3).

Pure functions (numpy only): they never load a model, so they are testable on stub data.
`workshop.twin.report` wires them to the real pipeline.

Command line (used by tools/verify/1.3.3.ps1)::

    python -m workshop.twin.calibrate check --set S
    python -m workshop.twin.calibrate compare A.json B.json [--tol 0.005]
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

import numpy as np

REPO = Path(__file__).resolve().parents[2]
CALIB_PATH = REPO / "workshop" / "twin" / "calibration.json"
THRESH_PATH = REPO / "workshop" / "twin" / "thresholds.json"
DECISIONS_PATH = REPO / "docs" / "decisions.md"
REPORT_PATH = REPO / "docs" / "reports" / "ch1-see.md"
DATA_CH1 = REPO / "data" / "ch1"
TEST_RUNS = DATA_CH1 / "test-runs.jsonl"

BEGIN = "<!-- ch1-see:begin -->"
END = "<!-- ch1-see:end -->"
GRID = [round(0.05 * i, 2) for i in range(1, 20)]  # 0.05 .. 0.95
MODES = ("light", "balanced", "strict")
BOUNDS = {"light": 0.01, "balanced": 0.05, "strict": 0.15}  # clean false-cover per mode
DEFAULT_MODES = {"light": 0.7, "balanced": 0.5, "strict": 0.3}
DEFAULT_MARGIN = 0.01
REPORT_HEADINGS = [
    "Score table",
    "Variants",
    "Calibration and thresholds",
    "Examples gain",
    "Unseen concept",
    "List switch",
    "Successes",
    "Failures",
    "Chosen models",
    "Gate",
]


# --- step 1: offset ---------------------------------------------------------------------------
def q95(values: list[float]) -> float | None:
    """95th percentile (linear interpolation); None when there are no values."""
    return float(np.percentile(np.asarray(values, dtype=np.float64), 95)) if len(values) else None


def offset_from_q95(q: float | None) -> float:
    """offset_c = clip(0.5 - q95_c, -1, 1); 0 when there were no clean screens to learn from."""
    if q is None:
        return 0.0
    return round(float(np.clip(0.5 - q, -1.0, 1.0)), 6)


def offset_for_concept(labels: list[dict], max_praw: dict[str, float], concept: str) -> float:
    """Offset from the dev screens with no box of `concept` (max p_raw per screen by image name)."""
    vals = [
        max_praw[lab["image"]]
        for lab in labels
        if lab["image"] in max_praw and not any(b["concept"] == concept for b in lab["boxes"])
    ]
    return offset_from_q95(q95(vals))


# --- step 2: thresholds -----------------------------------------------------------------------
def smallest_t(rows: list[dict], bound: float) -> float | None:
    """Smallest grid t whose cleanFalseCover is <= bound; None if none is."""
    ok = [
        r["t"] for r in sorted(rows, key=lambda r: r["t"]) if r["cleanFalseCover"] <= bound + 1e-12
    ]
    return ok[0] if ok else None


def pick_thresholds(
    sweeps: dict[str, list[dict]], bounds: dict[str, float] | None = None
) -> tuple[dict[str, float], list[str]]:
    """Per mode: smallest t meeting the bound for EVERY concept, then Strict <= Balanced <= Light.

    Returns (thresholds, notes). A bound that no grid point meets falls back to the top of the grid.
    """
    bounds = bounds or BOUNDS
    notes: list[str] = []
    out: dict[str, float] = {}
    for mode in MODES:
        per = []
        for concept, rows in sweeps.items():
            t = smallest_t(rows, bounds[mode])
            if t is None:
                notes.append(f"{mode}: {concept} never reaches clean false-cover <= {bounds[mode]}")
                t = GRID[-1]
            per.append(t)
        out[mode] = max(per) if per else DEFAULT_MODES[mode]
    out["balanced"] = max(out["balanced"], out["strict"])
    out["light"] = max(out["light"], out["balanced"])
    return {m: round(out[m], 2) for m in MODES}, notes


def thresholds_doc(modes: dict[str, float], margin: float = DEFAULT_MARGIN) -> dict:
    return {"version": 1, "modes": {m: modes[m] for m in MODES}, "margin": margin}


def calibration_doc(set_name: str, variant: str, concepts: dict[str, dict]) -> dict:
    full = {
        c: {
            "calibrationOffset": v.get("calibrationOffset", 0.0),
            "butNotExtra": list(v.get("butNotExtra", [])),
            "exampleThreshold": v.get("exampleThreshold"),
        }
        for c, v in concepts.items()
    }
    return {"version": 1, "set": set_name, "variant": variant, "concepts": full}


# --- step 3: butNotExtra ----------------------------------------------------------------------
def lookalike_extras(
    labels: list[dict], covers_by_concept: dict[str, set[str]], min_screens: int = 2
) -> dict[str, list[str]]:
    """Lookalike tags found on >= min_screens false-cover dev screens become `"a <tag>"` phrases.

    A false-cover screen is one with a hide for the concept but no label of that concept.
    """
    by_image = {lab["image"]: lab for lab in labels}
    out: dict[str, list[str]] = {}
    for concept, images in covers_by_concept.items():
        counts: dict[str, int] = {}
        for img in images:
            lab = by_image.get(img)
            if lab is None or any(b["concept"] == concept for b in lab["boxes"]):
                continue
            for tag in set(lab.get("lookalikes", [])):
                counts[tag] = counts.get(tag, 0) + 1
        out[concept] = [f"a {t}" for t, n in sorted(counts.items()) if n >= min_screens]
    return out


# --- step 4: examples -------------------------------------------------------------------------
def pick_example_screens(labels: list[dict], concept: str, n: int = 4) -> list[tuple[str, dict]]:
    """First n (image, rect) pairs of `concept` boxes, one per screen, by image name.

    Text boxes and cat-text tags are skipped: examples are real depictions.
    """
    out = []
    for lab in sorted(labels, key=lambda x: x["image"]):
        for b in lab["boxes"]:
            if b["concept"] == concept and b.get("kind") != "text" and b.get("tag") != "cat-text":
                out.append((lab["image"], b["rect"]))
                break
        if len(out) >= n:
            break
    return out


def centroid(vecs: np.ndarray) -> np.ndarray:
    c = np.asarray(vecs, dtype=np.float32).mean(axis=0)
    return (c / max(float(np.linalg.norm(c)), 1e-12)).astype(np.float32)


def example_gain(
    recall_off: float | None, recall_on: float | None, threshold: float | None
) -> dict:
    """Gain = change in Balanced recall on the remaining dev screens; kept only if gain > 0."""
    off = recall_off or 0.0
    on = recall_on or 0.0
    gain = round(on - off, 6)
    kept = bool(gain > 0 and threshold is not None)
    return {"recallOff": off, "recallOn": on, "gain": gain, "kept": kept, "indicative": True}


# --- successes and failures -------------------------------------------------------------------
def _stride(items: list, n: int) -> list:
    if len(items) <= n:
        return list(items)
    return [items[int(i * len(items) / n)] for i in range(n)]


def successes_failures(
    labels: list[dict],
    findings: dict[str, dict[str, list[dict]]],
    hits,
    n: int = 10,
) -> tuple[list[dict], list[dict]]:
    """findings = {concept: {image: [Finding]}}; hits(cover_rect, label_rect) -> bool.

    Success = labelled box covered. Failure = labelled box missed, or a hide on a screen that has no
    such label (wrong cover). Each entry is {image, concept, reason}.
    """
    succ: list[dict] = []
    missed: list[dict] = []
    wrong: list[dict] = []
    for lab in sorted(labels, key=lambda x: x["image"]):
        img = lab["image"]
        for concept, by_img in findings.items():
            hides = [f for f in by_img.get(img, []) if f.get("decision") == "hide"]
            boxes = [b for b in lab["boxes"] if b["concept"] == concept]
            for b in boxes:
                what = " ".join(x for x in (b.get("kind"), b.get("tag")) if x) or "box"
                if any(hits(f["rect"], b["rect"]) for f in hides):
                    succ.append({"image": img, "concept": concept, "reason": f"covered ({what})"})
                else:
                    missed.append({"image": img, "concept": concept, "reason": f"missed ({what})"})
            stray = [f for f in hides if not any(hits(f["rect"], b["rect"]) for b in boxes)]
            if stray:
                if lab.get("clean"):
                    why = "wrong cover on a clean screen"
                else:
                    why = "cover not on any labelled " + concept
                if lab.get("lookalikes"):
                    why += " (lookalikes: " + ", ".join(lab["lookalikes"]) + ")"
                wrong.append({"image": img, "concept": concept, "reason": why})
    fails = _stride(wrong, 5) + _stride(missed, 5)
    rest = [x for x in wrong + missed if x not in fails]
    fails += rest[: max(0, n - len(fails))]
    return _stride(succ, n), fails[:n]


# --- decision block ---------------------------------------------------------------------------
def write_decision_block(
    path: Path, title: str, body: str, date: str, begin: str = BEGIN, end: str = END
) -> str:
    """Insert or replace the block between the markers; returns its id, e.g. "D-004".

    The id is kept when the block already exists (so a re-run never renumbers), otherwise it is the
    next number after every other entry in the file. Nothing outside the markers is touched.
    """
    text = path.read_text(encoding="utf-8") if path.exists() else ""
    b = text.find(begin)
    e = text.find(end, b + len(begin)) if b >= 0 else -1
    inner = text[b + len(begin) : e] if (b >= 0 and e >= 0) else ""
    outside = text[:b] + text[e + len(end) :] if (b >= 0 and e >= 0) else text
    old = re.search(r"^## D-(\d+)", inner, re.M)
    if old:
        num = int(old.group(1))
    else:
        nums = [int(x) for x in re.findall(r"^## D-(\d+)", outside, re.M)]
        num = max(nums, default=0) + 1
    did = f"D-{num:03d}"
    block = f"{begin}\n## {did} · {title}\n\n{date} · Phase 1.3\n\n{body.strip()}\n{end}"
    if b >= 0 and e >= 0:
        new = text[:b] + block + text[e + len(end) :]
    else:
        new = text.rstrip("\n") + "\n\n" + block + "\n"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(new, encoding="utf-8", newline="\n")
    return did


# --- test-run log -----------------------------------------------------------------------------
def count_test_runs(set_name: str, path: Path = TEST_RUNS) -> int:
    if not path.exists():
        return 0
    n = 0
    for line in path.read_text(encoding="utf-8").splitlines():
        try:
            if json.loads(line).get("set") == set_name:
                n += 1
        except ValueError:
            continue
    return n


# --- checks used by the verify script ---------------------------------------------------------
def _num(x: float | None) -> float:
    return -1.0 if x is None else float(x)


def check_ordering(dev: dict) -> list[str]:
    """AC-1.3-04: recall and cleanFalseCover ordered Light <= Balanced <= Strict, per concept."""
    problems = []
    for concept in dev["balanced"]:
        for metric in ("recall", "cleanFalseCover"):
            v = [_num(dev[m][concept].get(metric)) for m in MODES]
            if not (v[0] <= v[1] + 1e-9 and v[1] <= v[2] + 1e-9):
                problems.append(f"{concept} {metric} not ordered light<=balanced<=strict: {v}")
    return problems


def check_outputs(
    set_name: str,
    results_path: Path | None = None,
    calib_path: Path = CALIB_PATH,
    thresh_path: Path = THRESH_PATH,
    report_path: Path = REPORT_PATH,
    decisions_path: Path = DECISIONS_PATH,
    test_runs: Path = TEST_RUNS,
) -> list[str]:
    results_path = results_path or DATA_CH1 / f"results-{set_name}.json"
    problems: list[str] = []
    try:
        json.loads(calib_path.read_text(encoding="utf-8"))
        modes = json.loads(thresh_path.read_text(encoding="utf-8"))["modes"]
        if not (modes["light"] >= modes["balanced"] >= modes["strict"]):
            problems.append(f"thresholds not Light>=Balanced>=Strict: {modes}")
    except (OSError, ValueError, KeyError) as exc:
        problems.append(f"calibration/thresholds unreadable: {exc}")
    try:
        res = json.loads(results_path.read_text(encoding="utf-8"))
        for k in (
            "variants",
            "chosenVariant",
            "calibration",
            "thresholds",
            "dev",
            "examples",
            "newWord",
            "listSwitch",
            "test",
        ):
            if k not in res:
                problems.append(f"results missing key {k}")
        problems += check_ordering(res["dev"])
    except (OSError, ValueError, KeyError) as exc:
        problems.append(f"results unreadable: {exc}")
    try:
        rep = report_path.read_text(encoding="utf-8")
        for h in REPORT_HEADINGS:
            if not re.search(rf"^#+ .*{re.escape(h)}", rep, re.M):
                problems.append(f"report missing heading: {h}")
    except OSError as exc:
        problems.append(f"report unreadable: {exc}")
    try:
        dec = decisions_path.read_text(encoding="utf-8")
        b, e = dec.find(BEGIN), dec.find(END)
        if b < 0 or e < b or dec.count(BEGIN) != 1:
            problems.append("decision block markers missing or duplicated")
        else:
            block = dec[b:e].lower()
            need = [
                "torch",
                "transformers",
                "ultralytics",
                "siglip2-base-p16-224",
                "apache-2.0",
                "agpl-3.0",
                "thresholds",
                "calibration",
                "pending-human",
                "spaceid",
                "sha256",
            ]
            problems += [f"decision block lacks '{w}'" for w in need if w not in block]
    except OSError as exc:
        problems.append(f"decisions unreadable: {exc}")
    n = count_test_runs(set_name, test_runs)
    if n > 3:
        problems.append(f"{n} test runs logged for {set_name} (max 3)")
    return problems


def _numbers(obj, path: str = "") -> dict[str, float]:
    out: dict[str, float] = {}
    if isinstance(obj, dict):
        for k, v in obj.items():
            if str(k).startswith("sec") or k in ("generatedUtc", "test"):
                continue
            out.update(_numbers(v, f"{path}/{k}"))
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            out.update(_numbers(v, f"{path}[{i}]"))
    elif isinstance(obj, (int, float)) and not isinstance(obj, bool):
        out[path] = float(obj)
    return out


def compare_results(a: dict, b: dict, tol: float = 0.005) -> list[str]:
    """Numbers present in both results (timings, test block excluded) must agree within tol."""
    na, nb = _numbers(a), _numbers(b)
    bad = [f"{k}: {na[k]} vs {nb[k]}" for k in na if k in nb and abs(na[k] - nb[k]) > tol]
    if a.get("chosenVariant") != b.get("chosenVariant"):
        bad.append(f"chosenVariant: {a.get('chosenVariant')} vs {b.get('chosenVariant')}")
    if not set(na) & set(nb):
        bad.append("no numbers in common")
    return bad


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="python -m workshop.twin.calibrate")
    sub = p.add_subparsers(dest="cmd", required=True)
    c = sub.add_parser("check")
    c.add_argument("--set", default="synthetic")
    k = sub.add_parser("compare")
    k.add_argument("a")
    k.add_argument("b")
    k.add_argument("--tol", type=float, default=0.005)
    args = p.parse_args(argv)
    if args.cmd == "check":
        problems = check_outputs(args.set)
    else:
        problems = compare_results(
            json.loads(Path(args.a).read_text(encoding="utf-8")),
            json.loads(Path(args.b).read_text(encoding="utf-8")),
            args.tol,
        )
    for line in problems:
        print("PROBLEM:", line, file=sys.stderr)
    print("ok" if not problems else f"{len(problems)} problem(s)")
    return 1 if problems else 0


if __name__ == "__main__":
    raise SystemExit(main())
