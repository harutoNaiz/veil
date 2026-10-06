"""Compose benchmark feed screens (360x780, 3 cards) deterministically."""

from __future__ import annotations

import random

from PIL import Image, ImageDraw

from workshop.twin.public_set import APPS, SIZE, _bars, _split_heights

SEED = 72


def render_feed(
    rng: random.Random, photos: list[Image.Image], dark: bool
) -> tuple[Image.Image, list[dict], list[dict]]:
    """A 3-card feed. Returns (image, photo_rects, card_rects), rects as {x, y, w, h}."""
    width, height = SIZE
    image = Image.new("RGB", SIZE, (70, 70, 74) if dark else (190, 190, 193))
    draw = ImageDraw.Draw(image)
    gap, edge = 8, 3
    heights = _split_heights(rng, height - 2 * edge - gap * (len(photos) - 1), len(photos), 210)
    prects, crects = [], []
    y = edge
    for photo, h in zip(photos, heights, strict=True):
        card = {"x": edge, "y": y, "w": width - 2 * edge, "h": h}
        base = (105 if dark else 225) + rng.randint(-6, 6)
        draw.rectangle([card["x"], y, card["x"] + card["w"] - 1, y + h - 1], fill=(base,) * 3)
        ink = _bars(draw, card["x"], y, card["w"], dark, rng)
        by = y + h - 18
        draw.rectangle([card["x"] + 8, by, card["x"] + 8 + rng.randint(80, 200), by + 5], fill=ink)
        room_w, room_h = card["w"] - 12, h - 24 - 26
        scale = min(room_w / photo.width, room_h / photo.height, 1.0)
        pw, ph = max(8, int(photo.width * scale)), max(8, int(photo.height * scale))
        px = card["x"] + 6 + rng.randint(0, max(0, room_w - pw))
        py = y + 24 + rng.randint(0, max(0, room_h - ph))
        image.paste(photo.convert("RGB").resize((pw, ph), Image.LANCZOS), (px, py))
        prects.append({"x": px, "y": py, "w": pw, "h": ph})
        crects.append(card)
        y += h + gap
    return image, prects, crects


def plan_screens(
    image_ids: list[str], seed: int = SEED, pool: list[str] | None = None
) -> list[dict]:
    """Sorted ids, shuffled with Random(seed), chunked in threes (last padded from pool)."""
    ids = sorted(image_ids)
    random.Random(seed).shuffle(ids)
    pad = [p for p in sorted(pool or ids)]
    screens = []
    for i, start in enumerate(range(0, len(ids), 3)):
        cards = ids[start : start + 3]
        k = 0
        while len(cards) < 3:
            cards.append(pad[(i + k) % len(pad)])
            k += 1
        screens.append({"i": i, "app": APPS[i % 5], "dark": i % 3 == 0, "cards": cards})
    return screens


def screen_rng(i: int, seed: int = SEED) -> random.Random:
    return random.Random(seed * 100003 + i)
