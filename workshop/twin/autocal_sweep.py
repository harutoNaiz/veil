"""Sweep competitor count K and margin for auto concepts on the phone-like eval (cached embeddings).

python -m workshop.twin.autocal_sweep 8,32,128 0,0.02,0.04 [flat,agree]
"""

from __future__ import annotations

import sys
from pathlib import Path

from workshop.forge.siglip2.runtime import OnnxDescriber
from workshop.twin import autocal
from workshop.twin import phone_eval as pe
from workshop.twin.bank import bankio

WORDS = ["cats", "fox", "spiders"]


def animal_only(screens):
    return [
        i
        for i, s in enumerate(screens)
        if (s.label or {}).get("clean") and not s.image.name.startswith("clean-")
    ]


def main(ks, margins, guards="") -> None:
    bank_dir = Path("data/bank/v1")
    bank = bankio.read_bank(bank_dir / "bank.bin")
    vocab = bankio.read_vocab(bank_dir)
    enc = OnnxDescriber()
    screens = pe.load_screens()
    emb, _ = pe.embed(screens)
    fl = "flat" in guards
    co = next((m for m in ("agree", "wins") if m in guards), None)
    for k in ks:
        autocal.K_COMPETITORS = k
        for mg in margins:
            ccs = {w: autocal.compile_auto(w, enc, bank, vocab, margin=mg) for w in WORDS}
            res = pe.evaluate(screens, emb, ccs, ("light", "balanced"), fl, co)
            print(f"--- K={k} margin={mg}")
            print(pe.table(res), flush=True)


if __name__ == "__main__":
    main(
        [int(x) for x in sys.argv[1].split(",")],
        [float(x) for x in sys.argv[2].split(",")],
        sys.argv[3] if len(sys.argv) > 3 else "",
    )
