"""Download NudeNet v3.4 weights (plain HTTP). Does not install the pip package."""

from __future__ import annotations

import json

import requests

from workshop.forge.common import FORGE_DATA, sha256_file

BASE = "https://github.com/notAI-tech/NudeNet/releases/download/v3.4-weights/"
API = "https://api.github.com/repos/notAI-tech/NudeNet/releases/tags/v3.4-weights"
FILES = ("320n.onnx", "640m.onnx")
SRC = FORGE_DATA.parent / "forge-src" / "nudenet"


def fetch() -> dict:
    SRC.mkdir(parents=True, exist_ok=True)
    rec = {}
    for name in FILES:
        dst = SRC / name
        if not dst.is_file():
            # browser_download_url redirects anonymous clients to a login page; use the API asset.
            rel = requests.get(API, timeout=60)
            rel.raise_for_status()
            asset = next(a for a in rel.json()["assets"] if a["name"] == name)
            r = requests.get(
                asset["url"], headers={"Accept": "application/octet-stream"}, timeout=600
            )
            r.raise_for_status()
            if len(r.content) != asset["size"]:
                raise RuntimeError(f"{name}: got {len(r.content)} bytes, expected {asset['size']}")
            dst.write_bytes(r.content)
        rec[name] = {"url": BASE + name, "sha256": sha256_file(dst), "bytes": dst.stat().st_size}
    (SRC / "sources.json").write_text(json.dumps(rec, indent=1), encoding="utf-8")
    return rec


if __name__ == "__main__":
    print(json.dumps(fetch(), indent=1))
