"""Category packs: words of the same family stop competing with each other.

python -m workshop.twin.bank.family guard/app/src/main/assets/packs

A word learned alone keeps its lookalikes as competitors ("gore" vs "blood"), so a picture
is hidden only when it looks more like the word than like any neighbour. Inside a category
pack that veto is wrong: a gory frame that looks a bit more like "blood" than "gore" is still
violence & gore. Each pack folder lists its family here; every concept in the pack drops
competitors that belong to the family. Harmless lookalikes (meat, bandage, tattoo, building,
document) stay competitors so ordinary pictures are not hidden.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

FAMILY = {
    "violence": {
        "blood",
        "gash",
        "corpse",
        "flesh",
        "guts",
        "monstrosity",
        "carcass",
        "killer",
        "victim",
        "cut",
        "wound",
        "remains",
        "bones",
        "skeleton",
        "suicide",
        "zombie",
        "monster",
        "mutant",
        "perpetrator",
        "weapon",
        "shooter",
        "shoot",
        "shot",
        "bang",
        "rumble",
        "fighter",
        "warrior",
        "pain",
        "scratch",
        "rip",
        "tore",
        "emergency",
        "villain",
        "gore",
        "violence",
        "organs",
        "wreck",
        "demon",
        "survivor",
        "prey",
        "lunatic",
        "smear",
        "hole",
        "crack",
        "lump",
        "stitch",
        "surgery",
        "death",
        "dead",
        "injury",
        "murder",
    },
    "politics": {
        "politician",
        "president",
        "dictator",
        "mp",
        "pm",
        "trump",
        "republican",
        "polls",
        "poll",
        "pol",
        "delegate",
        "representative",
        "leaders",
        "leader",
        "protester",
        "demonstrator",
        "supporter",
        "picket",
        "movement",
        "capitol",
        "parliament",
        "ballot",
        "election",
        "mayor",
        "official",
        "executive",
        "authority",
        "fundraiser",
        "anti",
        "resistance",
        "blockade",
        "party",
        "primary",
        "federal",
        "national",
        "assembly",
        "courthouse",
        "court",
        "dignitary",
        "gathering",
        "union",
        "establishment",
        "institution",
        "palace",
        "protest",
        "rally",
        "vote",
        "campaign",
        "senator",
        "minister",
        "governor",
        "judge",
        "judges",
        "dais",
    },
}

# Generic "it is a picture" words: a video frame looks like "footage" or "a scene" first,
# which vetoed every category word on video. Dropping them costs no measurable false hides
# on the reference bank.
GENERIC = {
    "image",
    "picture",
    "pic",
    "photo",
    "photograph",
    "snapshot",
    "scene",
    "footage",
    "depiction",
    "representation",
    "art",
    "arts",
    "work",
    "works",
    "oeuvre",
    "copy",
    "reference",
    "piece",
    "thing",
    "story",
    "subject",
    "creation",
    "composition",
    "movie",
    "episode",
    "production",
    "output",
    "source",
    "feature",
    "sample",
    "reproduction",
    "variation",
    "imitation",
    "impression",
    "motif",
    "material",
    "memory",
    "likeness",
    "portrait",
    "exposure",
    "closeup",
    "graphic",
    "graphics",
    "illustration",
    "drawing",
    "presentation",
    "pictorial",
    "recording",
    "release",
}


def prune(pack_dir: Path) -> dict[str, int]:
    fam = FAMILY.get(pack_dir.name)
    if not fam:
        return {}
    fam = fam | GENERIC
    out = {}
    for f in sorted(pack_dir.glob("*.json")):
        j = json.loads(f.read_text(encoding="utf-8"))
        a = j.get("auto")
        if not a:
            continue
        before = len(a["competitors"])
        a["competitors"] = [c for c in a["competitors"] if c["term"].lower() not in fam]
        a["chips"] = [c for c in a.get("chips", []) if c.lower() not in fam]
        f.write_text(json.dumps(j, separators=(",", ":")), encoding="utf-8")
        out[f.name] = before - len(a["competitors"])
    return out


def main(argv: list[str] | None = None) -> int:
    root = Path((argv or sys.argv[1:])[0])
    for d in sorted(p for p in root.iterdir() if p.is_dir()):
        print(d.name, prune(d))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
