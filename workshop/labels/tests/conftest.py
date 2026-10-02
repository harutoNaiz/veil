"""Shared helpers: a tiny screens folder (PNGs plus sidecars) built in a temp dir."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from PIL import Image

META = {
    "app": "instagram",
    "surface": "explore",
    "mode": "dark",
    "orientation": "portrait",
    "source": "synth",
    "capturedAt": "2026-10-02T10:00:00Z",
}


@pytest.fixture
def make_screens(tmp_path):
    def make(names: list[str], size: tuple[int, int] = (360, 780)) -> Path:
        folder = tmp_path / "screens"
        folder.mkdir(exist_ok=True)
        for name in names:
            Image.new("RGB", size, (30, 30, 30)).save(folder / name)
            (folder / name).with_suffix(".json").write_text(json.dumps(META), encoding="utf-8")
        return folder

    return make
