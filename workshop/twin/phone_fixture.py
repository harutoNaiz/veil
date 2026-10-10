"""Write the Kotlin parity fixture for an auto concept: workshop/twin/tests/fixtures/phone/.

    python -m workshop.twin.phone_fixture data/phone-kit/concepts/cats.json

expected.json = real piece vectors with the twin's verdicts per mode, plus guard cases
(regions, hide flags, flat flags, outputs for each guard mode) taken from two real screens.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

from workshop.twin import guards
from workshop.twin import phone_eval as pe
from workshop.twin.judge import judge

OUT = Path(__file__).resolve().parent / "tests" / "fixtures" / "phone"


def main(path: str) -> None:
    cc = json.loads(Path(path).read_text(encoding="utf-8"))
    screens = pe.load_screens()
    emb, _ = pe.embed(screens)
    rng = np.random.default_rng(7)
    pool = []
    for regions, vecs, _t in emb:
        for r, v in zip(regions, vecs, strict=True):
            pool.append((r, v))
    allv = np.stack([v for _, v in pool])
    score = {m: np.array([x["score"] for x in judge(allv, cc, m)]) for m in ("balanced",)}
    order = np.argsort(-score["balanced"])
    pick = (
        list(order[:6])
        + list(order[len(order) // 2 : len(order) // 2 + 3])
        + [int(i) for i in rng.choice(len(pool), 5, replace=False)]
    )
    vectors = allv[pick]
    verdicts = {m: judge(vectors, cc, m) for m in ("light", "balanced", "strict")}
    cases = []
    for regions, vecs, _t in emb:
        if len(cases) == 3:
            break
        hide = [x["decision"] == "hide" for x in judge(vecs, cc, "strict")]
        if sum(hide) < 3 or not any(r["source"] == "finder" for r in regions):
            continue
        flat = [bool(rng.random() < 0.1) for _ in regions]
        cases.append(
            {
                "pieces": [{"source": r["source"], "rect": r["rect"]} for r in regions],
                "hide": hide,
                "flat": flat,
                "none": guards.apply(regions, hide, None, None),
                "flatOnly": guards.apply(regions, hide, flat, None),
                "agree": guards.apply(regions, hide, flat, "agree"),
                "wins": guards.apply(regions, hide, flat, "wins"),
            }
        )
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "concept.json").write_text(json.dumps(cc), encoding="utf-8")
    exp = {"vectors": vectors.astype(float).tolist(), "verdicts": verdicts, "guardCases": cases}
    (OUT / "expected.json").write_text(json.dumps(exp), encoding="utf-8")
    print(
        len(pick),
        "vectors;",
        sum(len([1 for h in c["hide"] if h]) for c in cases),
        "hides in guard cases",
    )


if __name__ == "__main__":
    main(sys.argv[1])
