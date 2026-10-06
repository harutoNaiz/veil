"""AC-7.2-03: no word-specific parameter in the 7.1/7.2 method code (not the Chapter 1 calibration).

Scope: autocal.py, judge.py, bench/*.py, bench/params.json and the Kotlin AutoCal/Judge files.
"""

from __future__ import annotations

import importlib
import json
import re
import sys
from pathlib import Path

from workshop.contracts.validate import REPO_ROOT

HERE = Path(__file__).resolve().parent
CAND = HERE / "candidates.json"
DEV = ["snake", "buffalo", "umbrella", "pizza", "motorcycle", "giraffe", "kite", "broccoli"]
DEV += ["surfboard", "clock", "cat", "spider"]
KT_AUTOCAL = "guard/teacher/src/main/kotlin/com/veil/teacher/autocal"
KT_JUDGE = "guard/brain/src/main/kotlin/com/veil/brain/judge/Judge.kt"
# "bench" is both a candidate word and this package/CLI name; only params.json is checked for it.
HOMOGRAPHS = {"bench"}
QUOTED = re.compile(r"""["']([^"'\n]{1,40})["']""")


def words() -> set[str]:
    out = set(DEV)
    if CAND.exists():
        c = json.loads(CAND.read_text(encoding="utf-8"))
        out |= set(c.get("dev", []))
        for lst in c.get("categories", {}).values():
            out |= {x["word"] for x in lst}
    return {w.lower() for w in out}


def files() -> list[Path]:
    fs = [REPO_ROOT / "workshop/twin/autocal.py", REPO_ROOT / "workshop/twin/judge.py"]
    fs += sorted(HERE.glob("*.py")) + [HERE / "params.json"]
    fs += sorted((REPO_ROOT / KT_AUTOCAL).glob("*.kt")) + [REPO_ROOT / KT_JUDGE]
    return [f for f in fs if f.exists() and f.name != "word_params_check.py"]


def literal_hits(ws: set[str]) -> list[str]:
    hits = []
    for f in files():
        for n, line in enumerate(f.read_text(encoding="utf-8", errors="replace").splitlines(), 1):
            for m in QUOTED.finditer(line):
                w = m.group(1).strip().lower()
                if w in ws and not (w in HOMOGRAPHS and f.suffix == ".py"):
                    hits.append(f"{f.name}:{n}: {m.group(0)}")
    return hits


def module_hits(ws: set[str]) -> list[str]:
    mod = importlib.import_module("workshop.twin.autocal")
    hits = []
    for name, val in vars(mod).items():
        if name.startswith("__"):
            continue
        items = []
        if isinstance(val, dict):
            items = list(val.keys())
        elif isinstance(val, (list, tuple, set, frozenset)):
            items = list(val)
        hits += [f"autocal.{name}: {x!r}" for x in items if isinstance(x, str) and x.lower() in ws]
    return hits


def main() -> int:
    ws = words()
    hits = literal_hits(ws) + module_hits(ws)
    for h in hits:
        print("HIT", h)
    print(f"NO_WORD_PARAMS hits={len(hits)}")
    return 0 if not hits else 1


if __name__ == "__main__":
    sys.exit(main())
