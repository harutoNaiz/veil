"""Writes data/ch5/teacher-ref.json (Python cards + prompt fingerprints); copies tokenizer."""

from __future__ import annotations

import json
import shutil
from pathlib import Path

from workshop.contracts.rules import concept_sha256
from workshop.forge.common import FORGE_DATA
from workshop.forge.siglip2.runtime import HF_ID, OnnxDescriber
from workshop.twin import teacher
from workshop.twin.describer import hub_cache

WORDS = ["spiders", "cats", "clowns", "snakes", "needles"]
OUT = Path(__file__).resolve().parents[2] / "data" / "ch5" / "teacher-ref.json"


def _tokenizer() -> Path:
    root = hub_cache() / ("models--" + HF_ID.replace("/", "--")) / "snapshots"
    return next(root.glob("*/tokenizer.json"))


def main() -> None:
    dst = FORGE_DATA / "siglip2" / "tokenizer.json"
    shutil.copyfile(_tokenizer(), dst)
    enc = OnnxDescriber()
    out = []
    for word in WORDS:
        card = teacher.concept_card(word)
        cc = teacher.compile_concept(card, enc)
        prompts = [
            {"text": e["text"], "vectorF16": e["vectorF16"]}
            for k in ("looksLike", "butNot", "ignore")
            for e in cc[k]
        ]
        out.append(
            {
                "word": word,
                "card": card,
                "conceptSha256": concept_sha256(card),
                "calibrationOffset": cc["calibrationOffset"],
                "prompts": prompts,
            }
        )
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps({"concepts": out}, indent=1), encoding="utf-8")
    print(f"wrote {OUT} and {dst}")


if __name__ == "__main__":
    main()
