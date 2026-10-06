"""Open Images V7 helpers: CSV download (resumable), streaming filters, hierarchy."""

from __future__ import annotations

import csv
import http.client
import json
from pathlib import Path
from urllib.parse import urlsplit

BASE = "https://storage.googleapis.com/openimages/"
SUBSETS = {"validation": "val", "test": "test"}
ROOT = Path(__file__).resolve().parents[3]
SRC = ROOT / "data" / "bench" / "src"
CC_OK = {
    "creativecommons.org/licenses/by/2.0/",
    "creativecommons.org/licenses/by-sa/2.0/",
}


def urls(subsets: list[str]) -> dict[str, str]:
    out = {
        "classes": "v7/oidv7-class-descriptions.csv",
        "hierarchy": "2018_04/bbox_labels_600_hierarchy.json",
    }
    for s in subsets:
        out[f"labels-{s}"] = f"v7/oidv7-{SUBSETS[s]}-annotations-human-imagelabels.csv"
        out[f"images-{s}"] = f"2018_04/{s}/{s}-images-with-rotation.csv"
    return out


def download(rel: str, dest_dir: Path = SRC, tries: int = 6) -> Path:
    """Resumable, size-checked download of BASE+rel (http.client, Range resume)."""
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest = dest_dir / Path(rel).name
    u = urlsplit(BASE + rel)
    for _ in range(tries):
        try:
            c = http.client.HTTPSConnection(u.netloc, timeout=60)
            c.request("HEAD", u.path)
            r = c.getresponse()
            r.read()
            size = int(r.getheader("Content-Length") or 0)
            c.close()
            have = dest.stat().st_size if dest.exists() else 0
            if size and have == size:
                return dest
            if have > size:
                dest.unlink()
                have = 0
            c = http.client.HTTPSConnection(u.netloc, timeout=60)
            c.request("GET", u.path, headers={"Range": f"bytes={have}-"} if have else {})
            r = c.getresponse()
            if r.status not in (200, 206):
                raise OSError(f"HTTP {r.status}")
            if r.status == 200:
                have = 0
            with dest.open("ab" if have else "wb") as f:
                while chunk := r.read(1 << 20):
                    f.write(chunk)
            c.close()
        except OSError:
            continue
        if not size or dest.stat().st_size == size:
            return dest
    raise RuntimeError(f"cannot download {rel}")


def read_classes(path: Path) -> dict[str, list[str]]:
    """lowercase DisplayName -> [MID, ...] (more than one = ambiguous)."""
    out: dict[str, list[str]] = {}
    with Path(path).open(encoding="utf-8", newline="") as f:
        for row in csv.reader(f):
            if len(row) >= 2 and row[0].startswith("/"):
                out.setdefault(row[1].lower(), []).append(row[0])
    return out


def class_names(path: Path) -> dict[str, str]:
    with Path(path).open(encoding="utf-8", newline="") as f:
        return {r[0]: r[1] for r in csv.reader(f) if len(r) >= 2}


def descendants(hier: dict) -> dict[str, set[str]]:
    """MID -> itself + all Subcategory descendants."""
    out: dict[str, set[str]] = {}

    def walk(n: dict) -> set[str]:
        s = {n["LabelName"]}
        for ch in n.get("Subcategory", []):
            s |= walk(ch)
        out.setdefault(n["LabelName"], set()).update(s)
        return s

    walk(hier)
    return out


def load_hierarchy(path: Path) -> dict[str, set[str]]:
    return descendants(json.loads(Path(path).read_text(encoding="utf-8")))


def stream_labels(path: Path, keep: set[str]):
    """Yield (ImageID, MID, confidence) for verification rows; caller filters on `keep`."""
    with Path(path).open(encoding="utf-8", newline="") as f:
        rd = csv.reader(f)
        next(rd, None)
        for row in rd:
            if len(row) >= 4 and row[1] == "verification":
                yield row[0], row[2], float(row[3]) >= 0.5, row[2] in keep


def stream_images(path: Path, ids: set[str]):
    """Yield metadata dicts for ImageIDs in `ids`."""
    with Path(path).open(encoding="utf-8", newline="") as f:
        for r in csv.DictReader(f):
            if r["ImageID"] in ids:
                yield {
                    "id": r["ImageID"],
                    "subset": r["Subset"],
                    "url": r["OriginalURL"],
                    "landing": r["OriginalLandingURL"],
                    "license": r["License"],
                    "author": r["Author"],
                    "rotation": int(float(r.get("Rotation") or 0)),
                }


def flickr_id(url: str) -> str:
    """Digits before the first '_' of the URL basename ('' when not a Flickr-style name)."""
    base = url.rsplit("/", 1)[-1]
    head = base.split("_", 1)[0]
    return head if head.isdigit() and "_" in base else ""


def licence_ok(url: str) -> bool:
    return url.replace("https://", "").replace("http://", "") in CC_OK
