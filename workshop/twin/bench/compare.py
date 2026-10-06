"""Twin (or phone) replay results vs direct eval on the stored vectors, per word."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from workshop.eval.score_screens import score
from workshop.twin import judge
from workshop.twin.bench import fmt

MAX_DELTA = 2.0
XYWH = ("x", "y", "w", "h")


def _stats(labels: list[dict], covers: list[tuple[int, dict]], word: str) -> tuple[float, float]:
    fs = [
        {"image": fmt.screen_name(i), "decision": "hide", "conceptId": word, "rect": r}
        for i, r in covers
    ]
    res = score(labels, fs)
    c = res["concepts"].get(word, {})
    return (c.get("recall") or 0.0), res["cleanFalseCover"]


def tape_covers(tape_out: Path, truth: dict) -> dict[str, list[tuple[int, dict]]]:
    out: dict[str, list[tuple[int, dict]]] = {}
    for line in Path(tape_out).read_text(encoding="utf-8").splitlines():
        rec = json.loads(line) if line.strip() else {}
        if rec.get("kind") != "maskPlan":
            continue
        plan = rec["plan"]
        i = truth["frames"][str(rec["frameId"])]
        k = 360 / plan["screenWidth"]
        for m in plan["masks"]:
            r = {n: int(round(m["rect"][n] * k)) for n in XYWH}
            for w in m["conceptIds"]:
                out.setdefault(w, []).append((i, r))
    return out


def direct_covers(b: fmt.Bench, ccs: dict, mode: str, screens: list[int]):
    out: dict[str, list[tuple[int, dict]]] = {}
    for w, cc in ccs.items():
        for i in screens:
            verdicts = judge.judge(fmt.screen_vecs(b, i), cc, mode)
            for r, v in zip(b.regions, verdicts, strict=True):
                if v["decision"] == "hide":
                    out.setdefault(w, []).append((i, {n: int(round(r["rect"][n])) for n in XYWH}))
    return out


def compare(b: fmt.Bench, tape_out: Path, ccs: dict, truth: dict, mode: str = "balanced") -> float:
    """Print one COMPARE line per word; return the largest delta in points."""
    screens = sorted(set(truth["frames"].values()))
    tape = tape_covers(tape_out, truth)
    direct = direct_covers(b, ccs, mode, screens)
    worst = 0.0
    for w in ccs:
        names = {fmt.screen_name(i) for i in screens}
        labels = [x for x in fmt.labels_for(b, w) if x["image"] in names]
        rt, ft = _stats(labels, tape.get(w, []), w)
        rd, fd = _stats(labels, direct.get(w, []), w)
        dr, df = abs(rt - rd) * 100, abs(ft - fd) * 100
        print(f"COMPARE word={w} dRecall={dr:.2f} dFC={df:.2f}")
        worst = max(worst, dr, df)
    return worst


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="python -m workshop.twin.bench.compare")
    p.add_argument("--bench", required=True)
    p.add_argument("--tape-out", required=True)
    p.add_argument("--ccs", required=True, help="JSON {word: CompiledConcept}")
    p.add_argument("--mode", default="balanced")
    p.add_argument("--direct", action="store_true", help="accepted; direct eval always runs")
    a = p.parse_args(argv)
    b = fmt.load_bench(Path(a.bench))
    truth = json.loads((Path(a.bench) / "replay" / "replay-truth.json").read_text("utf-8"))
    ccs = json.loads(Path(a.ccs).read_text("utf-8"))
    ccs = {w: ccs[w] for w in truth["phone10"] if w in ccs}
    worst = compare(b, Path(a.tape_out), ccs, truth, a.mode)
    ok = worst <= MAX_DELTA
    print(f"COMPARE maxDelta={worst:.2f} {'PASS' if ok else 'FAIL'}")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
