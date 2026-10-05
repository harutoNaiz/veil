"""Write the five topic ConceptPacks (contract 1.0) and schema-validate them.

python -m workshop.packs.build_packs

Gore and needles are text only: plain descriptive prompts and keyword rules, no images anywhere.
A pack that failed its image bar is written to packs/rejected/ (outside the server's *.json glob).
"""

from __future__ import annotations

import json
from pathlib import Path

from workshop.contracts.validate import validate

HERE = Path(__file__).resolve().parent
REPORTS = HERE / "reports"
REJECTED = HERE / "rejected"
VERSION = "1.0.0"

PACKS: dict[str, dict] = {
    "spiders": {
        "name": "Spiders",
        "sensitive": False,
        "about": "Hides spiders and spider webs, including cartoons.",
        "concept": {
            "conceptId": "spiders",
            "displayName": "Spiders",
            "scope": "object",
            "looksLike": [
                "a photo of a spider",
                "a close-up of a tarantula",
                "a spider on its web",
                "a cartoon spider",
                "a drawing of a spider",
                "a spider emoji",
                "a large hairy spider",
                "a spider crawling on a wall",
            ],
            "butNot": ["a crab", "an ant", "a toy for cats", "a beetle", "a dog", "a cat"],
            "keywords": [
                "spider",
                "spiders",
                "tarantula",
                "arachnid",
                "arachnophobia",
                "cobweb",
                "spiderweb",
                "huntsman",
                "daddy longlegs",
                "wolf spider",
                "jumping spider",
            ],
        },
    },
    "needles": {
        "name": "Needles and injections",
        "sensitive": True,
        "about": "Text-only rules for posts about needles and injections.",
        "concept": {
            "conceptId": "needles",
            "displayName": "Needles and injections",
            "scope": "wholeElement",
            "looksLike": [
                "a syringe with a needle",
                "a person receiving an injection",
                "a needle going into an arm",
                "a nurse holding a syringe",
                "a blood draw with a needle",
                "a vaccine shot being given",
            ],
            "butNot": [
                "a ballpoint pen",
                "knitting needles and yarn",
                "a thermometer",
                "a sewing needle and thread",
                "a pine tree branch",
            ],
            "keywords": [
                "needle",
                "needles",
                "syringe",
                "injection",
                "injections",
                "blood draw",
                "vaccine shot",
                "jab",
                "iv drip",
                "intravenous",
                "needle phobia",
            ],
        },
    },
    "gore": {
        "name": "Graphic injury",
        "sensitive": True,
        "about": "Text-only rules for posts describing graphic injury or gore.",
        "concept": {
            "conceptId": "gore",
            "displayName": "Graphic injury",
            "scope": "wholeElement",
            "looksLike": [
                "a graphic scene of a bloody injury",
                "a gory horror movie scene",
                "a person with a severe wound",
                "a pool of blood on the ground",
                "a gruesome accident scene",
            ],
            "butNot": [
                "tomato sauce on a plate",
                "red paint on a canvas",
                "ketchup on fries",
                "a red rose",
                "strawberry jam",
            ],
            "keywords": [
                "gore",
                "gory",
                "gruesome",
                "bloodbath",
                "mutilated",
                "mutilation",
                "dismembered",
                "graphic injury",
                "severed",
                "bloody wound",
                "entrails",
            ],
        },
    },
    "alcohol": {
        "name": "Alcohol",
        "sensitive": True,
        "about": "Hides drinks and posts about alcohol.",
        "concept": {
            "conceptId": "alcohol",
            "displayName": "Alcohol",
            "scope": "wholeElement",
            "looksLike": [
                "a bottle of beer",
                "a glass of wine",
                "a cocktail in a glass",
                "a shot of whisky",
                "bottles of liquor on a shelf",
                "people drinking beer at a bar",
            ],
            "butNot": [
                "a glass of orange juice",
                "a can of soda",
                "a cup of tea",
                "a glass of water",
                "a cup of coffee",
            ],
            "keywords": [
                "beer",
                "wine",
                "vodka",
                "whisky",
                "whiskey",
                "cocktail",
                "tequila",
                "booze",
                "drunk",
                "hangover",
                "happy hour",
                "shots",
            ],
        },
    },
    "spoiler-breaking-bad": {
        "name": "Spoilers: Breaking Bad",
        "sensitive": False,
        "about": "Covers posts that give away how Breaking Bad plays out. Names and keywords only.",
        "concept": {
            "conceptId": "spoiler-breaking-bad",
            "displayName": "Breaking Bad spoilers",
            "scope": "wholeElement",
            "looksLike": [
                "a post that reveals the ending of a tv series",
                "a spoiler about who dies in breaking bad",
                "a text post about the breaking bad finale",
                "a meme spoiling the end of breaking bad",
            ],
            "butNot": [
                "a poster for a tv show",
                "a cooking show",
                "a chemistry classroom",
                "a movie trailer without plot details",
            ],
            "keywords": [
                "walter dies",
                "walt dies",
                "walter white dies",
                "hank dies",
                "gus dies",
                "jesse escapes",
                "the finale reveals",
                "ending of breaking bad",
                "breaking bad spoiler",
                "breaking bad ending",
                "who dies in breaking bad",
                "felina",
            ],
        },
    },
}


def concept_doc(spec: dict) -> dict:
    return {
        "contractVersion": "1.0",
        "layer": 2,
        "enabled": True,
        "coverStyle": "solid",
        "showLabel": False,
        "sensitive": bool(spec["sensitive"]),
        **spec["concept"],
    }


def pack_doc(pack_id: str, report: dict | None = None) -> dict:
    spec = PACKS[pack_id]
    doc = {
        "contractVersion": "1.0",
        "packId": pack_id,
        "name": spec["name"],
        "version": VERSION,
        "description": spec["about"],
        "sensitive": spec["sensitive"],
        "concepts": [concept_doc(spec)],
        "licence": "CC0-1.0",
    }
    if report:
        doc["accuracy"] = {
            k: report[k] for k in ("recall", "cleanFalseCoverRate", "testImages", "testSet")
        }
        extra = f" Result ({report['status']}): {report['line']}"
        doc["description"] = (doc["description"] + extra)[:2000]
    validate("ConceptPack", doc)
    return doc


def write_pack(pack_id: str, report: dict | None = None) -> Path:
    """Write the pack in packs/ (the catalogue) or packs/rejected/ when its image bar failed."""
    if report is None:
        rp = REPORTS / f"{pack_id}.json"
        report = json.loads(rp.read_text("utf-8")) if rp.is_file() else None
    doc = pack_doc(pack_id, report)
    rejected = bool(report) and report["status"] == "FAIL"
    target = (REJECTED if rejected else HERE) / f"{pack_id}.json"
    other = (HERE if rejected else REJECTED) / f"{pack_id}.json"
    target.parent.mkdir(exist_ok=True)
    target.write_text(json.dumps(doc, indent=2) + "\n", encoding="utf-8")
    other.unlink(missing_ok=True)
    return target


def main() -> int:
    for pid in PACKS:
        print("wrote", write_pack(pid))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
