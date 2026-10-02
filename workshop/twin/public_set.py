"""Real-photo "public" set (amendment A1): small harmless public photos composed into feeds.

python -m workshop.twin.public_set --fetch      # download ~55 small photos into data/public/photos
python -m workshop.twin.public_set --compose    # build data/public/set (60 screens, truth, split)
python -m workshop.twin.public_set               # both

1.2's synthetic "cats" are drawn circles, so model numbers on them mean nothing. This set puts REAL
cat, spider, dog, fox and neutral photos inside cards of a 360x780 feed screenshot with known boxes.
Photos come from public datasets through the Hugging Face datasets-server rows API (no heavy
download); each is resized to at most 320 px and 150 KB. Sources and licences go to
data/public/LICENSES.md. Everything under data/ is git-ignored.
"""

from __future__ import annotations

import argparse
import io
import json
import random
import sys
import time
import urllib.parse
import urllib.request
from datetime import datetime, timedelta
from pathlib import Path

from PIL import Image, ImageDraw

from workshop.contracts.validate import validate

REPO = Path(__file__).resolve().parents[2]
PUBLIC = REPO / "data" / "public"
PHOTOS = PUBLIC / "photos"
SET_DIR = PUBLIC / "set"
API = "https://datasets-server.huggingface.co/rows"
MAX_SIDE = 320
MAX_BYTES = 150_000
APPS = ["instagram", "youtube", "chrome", "whatsapp", "x"]
SIZE = (360, 780)
SOURCE = "public"

# group -> photos wanted; `from` rows are picked by label name, `rows` are fixed row indexes.
SOURCES = [
    {
        "id": "timm/oxford-iiit-pet",
        "split": "train",
        "licence": "CC-BY-SA-4.0",
        "label_field": "label_cat_dog",
        "picks": {"cat": ("cat", 18), "dog": ("dog", 10)},
    },
    {
        "id": "Rapidata/Animals-10",
        "split": "train",
        "licence": "GPL-2.0 (dataset card)",
        "label_field": "label",
        "picks": {
            "spider": ("spider", 8),
            "horse": ("neutral", 3),
            "butterfly": ("neutral", 3),
            "elephant": ("neutral", 2),
            "cow": ("neutral", 2),
            "sheep": ("neutral", 2),
            "chicken": ("neutral", 3),
            "squirrel": ("neutral", 3),
        },
    },
    {
        "id": "JetsonZoologist/humans_cats_dogs_foxes",
        "split": "train",
        "licence": "not stated on the dataset card (trail-camera photos)",
        "rows": {400: "fox", 800: "fox", 2000: "fox"},
    },
]


def _get(url: str, tries: int = 3) -> bytes:
    last: Exception | None = None
    for k in range(tries):
        try:
            with urllib.request.urlopen(url, timeout=90) as resp:
                return resp.read()
        except Exception as exc:  # network flakiness: retry a little
            last = exc
            time.sleep(2 * (k + 1))
    raise RuntimeError(f"cannot fetch {url[:80]}: {last}")


def _rows(dataset: str, split: str, offset: int, length: int) -> dict:
    query = urllib.parse.urlencode(
        {
            "dataset": dataset,
            "config": "default",
            "split": split,
            "offset": offset,
            "length": length,
        }
    )
    return json.loads(_get(f"{API}?{query}"))


def _names(features: list[dict], field: str) -> list[str] | None:
    for f in features:
        if f["name"] == field:
            return [n.lower() for n in f["type"].get("names", [])] or None
    return None


def _shrink(data: bytes) -> bytes:
    """Resize to at most MAX_SIDE and re-encode as JPEG, keeping it under MAX_BYTES."""
    with Image.open(io.BytesIO(data)) as im:
        im = im.convert("RGB")
        im.thumbnail((MAX_SIDE, MAX_SIDE), Image.LANCZOS)
        for quality in (88, 80, 70, 60, 50):
            buf = io.BytesIO()
            im.save(buf, "JPEG", quality=quality)
            if buf.tell() <= MAX_BYTES:
                break
        return buf.getvalue()


def _save(group: str, key: str, data: bytes, index: dict, meta: dict) -> None:
    folder = PHOTOS / group
    folder.mkdir(parents=True, exist_ok=True)
    name = f"{key}.jpg"
    (folder / name).write_bytes(_shrink(data))
    index[f"{group}/{name}"] = meta


def fetch(max_pages: int = 8) -> dict:
    """Download the photos listed in SOURCES (skips groups that are already complete)."""
    PHOTOS.mkdir(parents=True, exist_ok=True)
    index_path = PHOTOS / "index.json"
    index: dict = json.loads(index_path.read_text("utf-8")) if index_path.is_file() else {}
    for src in SOURCES:
        ds, licence = src["id"], src["licence"]
        if "rows" in src:
            for row, group in src["rows"].items():
                key = f"{ds.split('/')[-1]}-{row}"
                if f"{group}/{key}.jpg" in index:
                    continue
                page = _rows(ds, src["split"], row, 1)
                url = page["rows"][0]["row"]["image"]["src"]
                meta = {"dataset": ds, "split": src["split"], "row": row, "licence": licence}
                _save(group, key, _get(url), index, meta)
            continue
        need = {
            label: [
                group,
                n - sum(1 for k in index if k.startswith(f"{group}/{ds.split('/')[-1]}-{label}-")),
            ]
            for label, (group, n) in src["picks"].items()
        }
        probe = _rows(ds, src["split"], 0, 1)
        total = probe.get("num_rows_total", 1000)
        names = _names(probe["features"], src["label_field"])
        step = max(100, total // max_pages)
        for page_no in range(max_pages):
            if all(n <= 0 for _, n in need.values()):
                break
            offset = min(page_no * step, max(0, total - 100))
            page = _rows(ds, src["split"], offset, 100)
            for item in page["rows"]:
                value = item["row"][src["label_field"]]
                label = names[value] if names else str(value)
                want = need.get(label) or need.get("*")
                if want is None or want[1] <= 0:
                    continue
                key = f"{ds.split('/')[-1]}-{label}-{item['row_idx']}"
                url = item["row"]["image"]["src"]
                meta = {
                    "dataset": ds,
                    "split": src["split"],
                    "row": item["row_idx"],
                    "label": label,
                    "licence": licence,
                }
                _save(want[0], key, _get(url), index, meta)
                want[1] -= 1
            index_path.write_text(json.dumps(index, indent=1) + "\n", encoding="utf-8")
        short = {k: v[1] for k, v in need.items() if v[1] > 0}
        if short:
            print(f"warning: {ds}: still missing {short}", file=sys.stderr)
    index_path.write_text(json.dumps(index, indent=1) + "\n", encoding="utf-8")
    _write_licences(index)
    return index


def _write_licences(index: dict) -> None:
    by_ds: dict[str, dict] = {}
    for meta in index.values():
        d = by_ds.setdefault(meta["dataset"], {"licence": meta["licence"], "n": 0})
        d["n"] += 1
    total = sum(p.stat().st_size for p in PHOTOS.rglob("*.jpg"))
    lines = [
        "# Public photo set: sources and licences",
        "",
        "Small public photos (resized to <= 320 px) fetched with the Hugging Face datasets-server",
        "rows API. They are only a local test set (git-ignored); nothing here is redistributed.",
        "",
        "| Dataset | Photos used | Licence |",
        "| --- | --- | --- |",
    ]
    for ds, d in sorted(by_ds.items()):
        lines.append(f"| https://huggingface.co/datasets/{ds} | {d['n']} | {d['licence']} |")
    lines += ["", f"Photos: {len(index)}, total {total / 1e6:.2f} MB.", ""]
    (PUBLIC / "LICENSES.md").write_text("\n".join(lines), encoding="utf-8")


# ---------------------------------------------------------------- composing screens


def _split_heights(rng: random.Random, total: int, n: int, low: int) -> list[int]:
    extra = total - n * low
    cuts = sorted(rng.uniform(0, extra) for _ in range(n - 1))
    parts = [b - a for a, b in zip([0.0, *cuts], [*cuts, extra], strict=True)]
    return [int(low + p) for p in parts]


def _bars(draw: ImageDraw.ImageDraw, x: int, y: int, w: int, dark: bool, rng: random.Random):
    ink = (
        tuple(rng.randint(130, 165) for _ in range(3))
        if dark
        else tuple(rng.randint(95, 125) for _ in range(3))
    )
    draw.ellipse([x + 4, y + 4, x + 20, y + 20], fill=ink)
    draw.rectangle([x + 26, y + 8, x + 26 + rng.randint(40, 120), y + 14], fill=ink)
    return ink


def _render(
    rng: random.Random, photos: list[Path | None], dark: bool, target: int | None
) -> tuple[Image.Image, list[tuple[int, dict, dict]]]:
    """A 3-card feed. photos[i] is the photo of card i (None = text only). Returns image + boxes."""
    width, height = SIZE
    image = Image.new("RGB", SIZE, (70, 70, 74) if dark else (190, 190, 193))
    draw = ImageDraw.Draw(image)
    gap, edge = 8, 3
    heights = _split_heights(rng, height - 2 * edge - gap * (len(photos) - 1), len(photos), 210)
    placed: list[tuple[int, dict, dict]] = []
    y = edge
    for k, (path, h) in enumerate(zip(photos, heights, strict=True)):
        card = {"x": edge, "y": y, "w": width - 2 * edge, "h": h}
        base = (105 if dark else 225) + rng.randint(-6, 6)
        draw.rectangle([card["x"], y, card["x"] + card["w"] - 1, y + h - 1], fill=(base,) * 3)
        ink = _bars(draw, card["x"], y, card["w"], dark, rng)
        by = y + h - 18
        draw.rectangle([card["x"] + 8, by, card["x"] + 8 + rng.randint(80, 200), by + 5], fill=ink)
        if path is not None:
            with Image.open(path) as im:
                photo = im.convert("RGB")
            room_w, room_h = card["w"] - 12, h - 24 - 26
            scale = min(room_w / photo.width, room_h / photo.height, 1.0)
            pw, ph = max(8, int(photo.width * scale)), max(8, int(photo.height * scale))
            photo = photo.resize((pw, ph), Image.LANCZOS)
            px = card["x"] + 6 + rng.randint(0, max(0, room_w - pw))
            py = y + 24 + rng.randint(0, max(0, room_h - ph))
            image.paste(photo, (px, py))
            if k == target:
                placed.append((k, {"x": px, "y": py, "w": pw, "h": ph}, card))
        y += h + gap
    return image, placed


def _group(name: str) -> str:
    return name.split("/")[0]


def compose(
    photos_dir: Path = PHOTOS, out: Path = SET_DIR, n: int = 60, seed: int = 7
) -> list[dict]:
    """Build the public screens; returns the ScreenLabel list (also written to truth.json)."""
    files = {
        g: sorted((photos_dir / g).glob("*.jpg"))
        for g in ("cat", "spider", "dog", "fox", "neutral")
    }
    if not files["cat"] or not files["neutral"]:
        raise FileNotFoundError(
            f"no photos in {photos_dir}: run python -m workshop.twin.public_set --fetch"
        )
    out.mkdir(parents=True, exist_ok=True)
    for old in [*out.glob("*.png"), *out.glob("*.json")]:
        old.unlink()
    rng = random.Random(seed)
    # one screen per target photo (cats, spiders, dogs, foxes); the rest are neutral-only screens
    jobs: list[tuple[str, Path | None]] = []
    for g in ("cat", "spider", "dog", "fox"):
        jobs += [(g, p) for p in files[g]]
    jobs = jobs[:n]
    jobs += [("neutral", None)] * (n - len(jobs))
    rng.shuffle(jobs)
    labels: list[dict] = []
    provenance: dict[str, list[str]] = {}
    base_time = datetime(2026, 10, 2, 11, 0, 0)
    for i, (group, target_photo) in enumerate(jobs):
        dark = i % 3 == 0
        app = APPS[i % len(APPS)]
        cards: list[Path | None] = [rng.choice(files["neutral"]) for _ in range(3)]
        target = None
        if target_photo is not None:
            target = rng.randrange(3)
            cards[target] = target_photo
        image, placed = _render(rng, cards, dark, target)
        boxes = []
        for _, rect, card in placed:
            if group not in ("cat", "spider"):
                continue
            box = {
                "rect": rect,
                "concept": "cats" if group == "cat" else "spiders",
                "kind": "photo",
                "scope": "object" if i % 2 == 0 else "wholeElement",
            }
            if box["scope"] == "wholeElement":
                box["postRect"] = card
            boxes.append(box)
        stem = f"{app}-feed-{i + 1:04d}"
        meta = {
            "app": app,
            "surface": "feed",
            "mode": "dark" if dark else "light",
            "orientation": "portrait",
            "source": SOURCE,
        }
        label = {
            "contractVersion": "1.0",
            "image": f"{stem}.png",
            "width": SIZE[0],
            "height": SIZE[1],
            "clean": not boxes,
            "boxes": boxes,
            "meta": meta,
            "labeller": SOURCE,
        }
        if group in ("dog", "fox"):
            label["lookalikes"] = [group]
        validate("ScreenLabel", label)
        image.save(out / f"{stem}.png")
        stamp = (base_time + timedelta(seconds=7 * i)).strftime("%Y-%m-%dT%H:%M:%SZ")
        (out / f"{stem}.json").write_text(
            json.dumps({**meta, "capturedAt": stamp}, indent=2) + "\n", encoding="utf-8"
        )
        provenance[f"{stem}.png"] = [p.name if p else "-" for p in cards]
        labels.append(label)
    splits = split_labels(labels, seed)
    (out / "sources.txt").write_text(f"# public photo set\n{SOURCE}\n", encoding="utf-8")
    (out / "truth.json").write_text(json.dumps(labels, indent=1) + "\n", encoding="utf-8")
    (out / "splits.json").write_text(json.dumps(splits, indent=1) + "\n", encoding="utf-8")
    (out / "provenance.json").write_text(json.dumps(provenance, indent=1) + "\n", encoding="utf-8")
    return labels


def split_labels(labels: list[dict], seed: int = 7) -> dict:
    """60/40 dev/test, stratified by class (cats, spiders, clean), seeded."""
    rng = random.Random(seed)
    classes: dict[str, list[str]] = {}
    for lab in labels:
        cls = (
            "cats"
            if any(b["concept"] == "cats" for b in lab["boxes"])
            else ("spiders" if lab["boxes"] else "clean")
        )
        classes.setdefault(cls, []).append(lab["image"])
    test: set[str] = set()
    for cls in sorted(classes):
        names = sorted(classes[cls])
        rng.shuffle(names)
        test.update(names[: round(0.4 * len(names))])
    names = sorted(lab["image"] for lab in labels)
    return {
        "seed": seed,
        "dev": [x for x in names if x not in test],
        "test": [x for x in names if x in test],
    }


def ensure_set() -> Path:
    """Return the composed set folder, composing it from the photos if needed."""
    if not (SET_DIR / "truth.json").is_file():
        compose()
    return SET_DIR


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="workshop.twin.public_set")
    parser.add_argument("--fetch", action="store_true")
    parser.add_argument("--compose", action="store_true")
    args = parser.parse_args(argv)
    both = not (args.fetch or args.compose)
    if args.fetch or both:
        index = fetch()
        groups: dict[str, int] = {}
        for key in index:
            groups[_group(key)] = groups.get(_group(key), 0) + 1
        print("photos:", json.dumps(groups))
    if args.compose or both:
        labels = compose()
        print(f"composed {len(labels)} screens in {SET_DIR}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
