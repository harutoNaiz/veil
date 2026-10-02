"""Gallery: an index.html of 360-px thumbnails with the labelled boxes (green), covers (red) and
near misses (orange) drawn on, and a TP / FP / FN line per screen and concept.

Images are written next to index.html (git-ignored under data/ch1/gallery). Nothing is uploaded.
"""

from __future__ import annotations

import html
from pathlib import Path

from PIL import Image, ImageDraw

from workshop.eval.score_screens import hits
from workshop.twin.data import Screen

GREEN, RED, ORANGE = (40, 170, 70), (220, 40, 40), (240, 150, 20)
THUMB = 360


def _findings(by_image: dict[str, list[dict]], name: str) -> list[dict]:
    return by_image.get(name) or by_image.get(Path(name).stem + ".png") or []


def _tally(label: dict | None, concept: str, found: list[dict]) -> str:
    covers = [f for f in found if f["decision"] == "hide"]
    if label is None:
        return f"{concept}: {len(covers)} cover(s), unlabelled"
    boxes = [b["rect"] for b in label["boxes"] if b["concept"] == concept]
    tp = sum(1 for b in boxes if any(hits(f["rect"], b) for f in covers))
    fn = len(boxes) - tp
    fp = sum(1 for f in covers if not any(hits(f["rect"], b) for b in boxes))
    return f"{concept}: TP {tp} FP {fp} FN {fn}" + (" (clean screen)" if label.get("clean") else "")


def _draw(img: Image.Image, rect: dict, scale: float, colour, width: int) -> None:
    x0, y0 = rect["x"] * scale, rect["y"] * scale
    x1, y1 = (rect["x"] + rect["w"]) * scale, (rect["y"] + rect["h"]) * scale
    ImageDraw.Draw(img).rectangle([x0, y0, x1, y1], outline=colour, width=width)


def build_gallery(
    screens: list[Screen], findings_by_concept: dict[str, dict[str, list[dict]]], out_html: Path
) -> Path:
    """Write index.html and the thumbnails; returns the index path."""
    out_html = Path(out_html)
    thumbs = out_html.parent / "thumbs"
    thumbs.mkdir(parents=True, exist_ok=True)
    cards = []
    for screen in screens:
        img = Image.open(screen.image).convert("RGB")
        scale = THUMB / max(img.size) if max(img.size) > THUMB else 1.0
        img = img.resize((max(1, round(img.width * scale)), max(1, round(img.height * scale))))
        if screen.label is not None:
            for box in screen.label["boxes"]:
                _draw(img, box["rect"], scale, GREEN, 2)
        lines = []
        for concept, by_image in findings_by_concept.items():
            found = _findings(by_image, screen.image.name)
            for f in found:
                _draw(img, f["rect"], scale, RED if f["decision"] == "hide" else ORANGE, 2)
            lines.append(_tally(screen.label, concept, found))
        thumb = f"{screen.image.stem}.jpg"
        img.save(thumbs / thumb, "JPEG", quality=82)
        notes = ""
        if screen.label is not None:
            notes = ", ".join(screen.label.get("lookalikes", []))
            notes = f"lookalikes: {html.escape(notes)}" if notes else ""
        body = "<br>".join(html.escape(x) for x in lines)
        cards.append(
            f'<figure><img src="thumbs/{html.escape(thumb)}" '
            f'alt="{html.escape(screen.image.name)}">'
            f"<figcaption><b>{html.escape(screen.image.name)}</b><br>{body}<br>{notes}"
            "</figcaption></figure>"
        )
    legend = (
        '<span style="color:#28aa46">green = labelled box</span> · '
        '<span style="color:#dc2828">red = hide</span> · '
        '<span style="color:#f09614">orange = near miss</span>'
    )
    page = (
        '<!doctype html><html><head><meta charset="utf-8"><title>Veil gallery</title><style>'
        "body{font:13px system-ui,sans-serif;margin:16px;background:#fafafa;color:#222}"
        ".grid{display:flex;flex-wrap:wrap;gap:12px}figure{margin:0;width:360px}"
        "img{max-width:100%;border:1px solid #ccc}figcaption{padding:4px 0}"
        f"</style></head><body><h1>Veil gallery</h1><p>{legend}</p>"
        f'<div class="grid">{"".join(cards)}</div></body></html>\n'
    )
    out_html.write_text(page, encoding="utf-8")
    return out_html
