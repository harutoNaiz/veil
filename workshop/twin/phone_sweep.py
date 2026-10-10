"""Sweep the global auto margin on cached phone_eval embeddings (no model run for pieces)."""

from __future__ import annotations

import copy
import json
import sys
from pathlib import Path

from workshop.twin import phone_eval as pe


def main(folder: str, margins: list[float], modes=("light", "balanced", "strict")) -> None:
    import os

    fl = "flat" in os.environ.get("GUARDS", "")
    co = next((m for m in ("agree", "wins") if m in os.environ.get("GUARDS", "")), None)
    screens = pe.load_screens()
    emb, _ = pe.embed(screens)
    for mg in margins:
        ccs = {}
        for p in sorted(Path(folder).glob("*.json")):
            cc = json.loads(p.read_text(encoding="utf-8"))
            cc = copy.deepcopy(cc)
            cc["auto"]["margin"] = mg
            cc["margin"] = mg
            ccs[cc["conceptId"]] = cc
        print(f"--- margin {mg}")
        print(pe.table(pe.evaluate(screens, emb, ccs, modes, fl, co)))


if __name__ == "__main__":
    main(sys.argv[1], [float(x) for x in sys.argv[2:]])
