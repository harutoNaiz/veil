"""7.1.2 eval of the auto rule on a built bank (HEAVY: loads the ONNX describer; run it alone).

    python -m workshop.twin.autocal_eval --bank data/bank/v1 [--set synthetic] [--words a,b]

Clean false-cover comes from the cached synthetic dev A run (as in Chapter 1). Recall = the share of
bank rows labelled with excl(word) that the auto judge hides at Balanced (full image = one piece).
Writes data/bank/eval-<dir>.json and docs/reports/ch7-autocal.md; exits 1 if the snakes clean
false-cover is above 0.05.
"""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path

import numpy as np

from workshop.contracts.validate import REPO_ROOT
from workshop.twin import autocal, judge
from workshop.twin.bank import bankio

WORDS = [
    "snakes",
    "buffalo",
    "umbrella",
    "pizza",
    "motorcycle",
    "giraffe",
    "kite",
    "broccoli",
    "surfboard",
    "clock",
]
LIMIT = 0.05


def _recall(cc: dict, bank: bankio.Bank, vocab: bankio.Vocab, word: str) -> tuple[object, int]:
    idx = autocal.lookup(vocab, word)
    if idx is None:
        return "n/a", 0
    pos = bankio.excluded_rows(bank, set(vocab.meta["entries"][idx]["excl"]))
    n = int(pos.sum())
    if n < 5:
        return "n/a", n
    hidden = [v["decision"] == "hide" for v in judge.judge(bank.rows[pos], cc, "balanced")]
    return float(np.mean(hidden)), n


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="python -m workshop.twin.autocal_eval")
    ap.add_argument("--bank", type=Path, required=True)
    ap.add_argument("--set", dest="set_name", default="synthetic")
    ap.add_argument("--words", default=",".join(WORDS))
    a = ap.parse_args(argv)
    words = [w.strip() for w in a.words.split(",") if w.strip()]

    from workshop.forge.siglip2.runtime import OnnxDescriber
    from workshop.twin import run

    bank = bankio.read_bank(a.bank / "bank.bin")
    vocab = bankio.read_vocab(a.bank)
    desc = OnnxDescriber()
    ccs, secs = {}, {}
    for w in words:
        t0 = time.perf_counter()
        ccs[w] = autocal.compile_auto(w, desc, bank, vocab)
        secs[w] = time.perf_counter() - t0
    res = run.run_set(
        a.set_name,
        "dev",
        words,
        variant="A",
        mode="balanced",
        ccs=ccs,
        piece_fn=run.describer_pieces(desc),
        encoder=desc,
        lane="describer",
    )
    rows = {}
    for w in words:
        recall, n_pos = _recall(ccs[w], bank, vocab, w)
        s = res.get(w) or {}
        rows[w] = {
            "cleanFalseCover": s.get("cleanFalseCover"),
            "screenRecall": s.get("recall"),
            "bankRecall": recall,
            "nPos": n_pos,
            "excluded": ccs[w]["auto"]["excluded"],
            "chips": ccs[w]["auto"]["chips"],
            "compileSec": round(secs[w], 3),
        }
        print(f"AUTOCAL {w} cleanFalseCover={rows[w]['cleanFalseCover']}")
    out = {"bank": a.bank.name, "bankId": bank.bank_id, "set": a.set_name, "words": rows}
    (REPO_ROOT / "data" / "bank").mkdir(parents=True, exist_ok=True)
    (REPO_ROOT / "data" / "bank" / f"eval-{a.bank.name}.json").write_text(
        json.dumps(out, indent=1), encoding="utf-8"
    )
    lines = [
        "# Chapter 7.1 auto calibration eval",
        "",
        f"Bank `{a.bank.name}` (id `{bank.bank_id}`), set `{a.set_name}` dev, variant A, Balanced.",
        "",
        "| word | clean false-cover | screen recall | bank recall | nPos | excluded | compile s |",
        "|---|---|---|---|---|---|---|",
    ]
    for w, r in rows.items():
        lines.append(
            f"| {w} | {r['cleanFalseCover']} | {r['screenRecall']} | {r['bankRecall']} "
            f"| {r['nPos']} | {r['excluded']} | {r['compileSec']} |"
        )
    report = REPO_ROOT / "docs" / "reports" / "ch7-autocal.md"
    report.parent.mkdir(parents=True, exist_ok=True)
    report.write_text("\n".join(lines) + "\n", encoding="utf-8")
    snakes = rows.get("snakes", {}).get("cleanFalseCover")
    return 1 if snakes is not None and snakes > LIMIT else 0


if __name__ == "__main__":
    raise SystemExit(main())
