"""COCO 2017 train captions: licence + blocklist filter, in-memory image fetch."""

from __future__ import annotations

import json
import re
import zipfile
from concurrent.futures import ThreadPoolExecutor
from io import BytesIO
from pathlib import Path

import numpy as np
from PIL import Image

ZIP_URL = "http://images.cocodataset.org/annotations/annotations_trainval2017.zip"
IMG_URL = "http://images.cocodataset.org/train2017/{file_name}"
LICENCES = {4: "CC BY 2.0", 5: "CC BY-SA 2.0", 7: "No known copyright", 8: "US Gov"}
BLOCKLIST = {"nude", "naked", "lingerie", "underwear", "bikini", "shirtless", "topless"}
SEED = 71


def captions_path(src: Path) -> Path:
    """Download the annotations zip once, extract only the train captions, delete the zip."""
    import requests

    out = src / "captions_train2017.json"
    if out.exists():
        return out
    src.mkdir(parents=True, exist_ok=True)
    zp = src / "annotations_trainval2017.zip"
    with requests.get(ZIP_URL, stream=True, timeout=60) as r:
        r.raise_for_status()
        with open(zp, "wb") as f:
            for chunk in r.iter_content(1 << 20):
                f.write(chunk)
    with zipfile.ZipFile(zp) as z:
        out.write_bytes(z.read("annotations/captions_train2017.json"))
    zp.unlink()
    return out


def filter_items(data: dict) -> list[dict]:
    """Licence-allowed, blocklist-clean images, sorted by id, shuffled with rng(71)."""
    caps: dict[int, list[str]] = {}
    for a in data["annotations"]:
        caps.setdefault(a["image_id"], []).append(a["caption"])
    items = []
    for im in data["images"]:
        if im["license"] not in LICENCES:
            continue
        cs = caps.get(im["id"], [])
        words = {w for c in cs for w in re.findall(r"[a-z]+", c.lower())}
        if words & BLOCKLIST:
            continue
        items.append(
            {
                "id": int(im["id"]),
                "file_name": im["file_name"],
                "licenseId": int(im["license"]),
                "captions": cs,
            }
        )
    items.sort(key=lambda x: x["id"])
    order = np.random.default_rng(SEED).permutation(len(items))
    return [items[i] for i in order]


def item_url(file_name: str) -> str:
    return IMG_URL.format(file_name=file_name)


def fetch_image(url: str) -> Image.Image | None:
    import requests

    for _ in range(3):
        try:
            r = requests.get(url, timeout=30)
            r.raise_for_status()
            return Image.open(BytesIO(r.content)).convert("RGB")
        except Exception:  # noqa: BLE001
            continue
    return None


def fetch_many(urls: list[str], threads: int = 8) -> list[Image.Image | None]:
    with ThreadPoolExecutor(threads) as ex:
        return list(ex.map(fetch_image, urls))


def load_captions(src: Path) -> dict:
    return json.loads(captions_path(src).read_text(encoding="utf-8"))
