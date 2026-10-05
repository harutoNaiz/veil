"""5.1.1 reference: Judge goldens for the Kotlin port (200 seeded vectors per concept, 3 modes)."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np

from workshop.twin import judge

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / "guard" / "brain" / "src" / "test" / "resources" / "judge-golden.json"


def build() -> dict:
    rng = np.random.default_rng(51)
    cases = []
    for path in sorted((ROOT / "contracts" / "examples" / "compiled-concept").glob("valid-*.json")):
        cc = json.loads(path.read_text(encoding="utf-8"))
        dim = cc["looksLike"][0]["dim"]
        vecs = rng.normal(size=(200, dim))
        # bias half of them toward the first looksLike phrase so hide/nearMiss both occur
        base = judge._matrix(cc["looksLike"])[0]
        vecs[::2] = vecs[::2] * 0.35 + base
        vecs /= np.linalg.norm(vecs, axis=1, keepdims=True)
        for mode in judge.MODES:
            cases.append(
                {
                    "concept": cc,
                    "mode": mode,
                    "vecs": vecs.tolist(),
                    "verdicts": judge.judge(vecs, cc, mode),
                }
            )
    return {"cases": cases}


def main() -> None:
    OUT.write_text(json.dumps(build(), indent=0, sort_keys=True) + "\n", encoding="utf-8")
    print(OUT)


if __name__ == "__main__":
    main()
