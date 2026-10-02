"""Small helpers shared by the eval tools (JSON loading and the derived image classes)."""

from __future__ import annotations

import json
from pathlib import Path


class BadInput(Exception):
    """The tool was given a file it cannot use (CLI exit code 2)."""


def load_json(path: Path | str) -> object:
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise BadInput(f"cannot read {path}: {exc}") from exc


def load_labels(path: Path | str) -> list[dict]:
    data = load_json(path)
    if not isinstance(data, list) or not all(isinstance(x, dict) and "image" in x for x in data):
        raise BadInput(f"{path} is not a JSON array of ScreenLabel objects")
    return data


def is_cats(label: dict) -> bool:
    return any(b["concept"] == "cats" and b.get("tag") != "cat-text" for b in label["boxes"])


def is_spiders(label: dict) -> bool:
    return any(b["concept"] == "spiders" for b in label["boxes"])


def is_clean(label: dict) -> bool:
    return label.get("clean") is True


def is_hard(label: dict) -> bool:
    return bool(label.get("lookalikes")) or any(b.get("tag") == "cat-text" for b in label["boxes"])


def primary_class(label: dict) -> str:
    """Stratum class: cats, else spiders, else clean."""
    if is_cats(label):
        return "cats"
    if is_spiders(label):
        return "spiders"
    return "clean"


def app_of(label: dict) -> str:
    return str(label.get("meta", {}).get("app", "unknown"))
