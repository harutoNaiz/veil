"""Every example validates (or is rejected for its indexed reason): AC-1.1-03."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from workshop.contracts import TYPES, example_dir
from workshop.contracts.validate import (
    SCHEMA_DIR,
    error_keywords,
    type_for_path,
    validate,
    validator,
)

EXAMPLES = SCHEMA_DIR / "examples"
INDEX = json.loads((EXAMPLES / "invalid-index.json").read_text(encoding="utf-8"))


def rel(path: Path) -> str:
    return path.relative_to(EXAMPLES).as_posix()


VALID = sorted(EXAMPLES.glob("*/valid-*.json"))
INVALID = sorted(EXAMPLES.glob("*/invalid-*.json"))
ALL = [*VALID, *INVALID]


def load(path: Path) -> object:
    return json.loads(path.read_text(encoding="utf-8"))


def test_example_folders_match_types():
    folders = {p.name for p in EXAMPLES.iterdir() if p.is_dir()}
    assert folders == {example_dir(t) for t in TYPES}


@pytest.mark.parametrize("type_name", TYPES)
def test_counts(type_name):
    folder = EXAMPLES / example_dir(type_name)
    valid = list(folder.glob("valid-*.json"))
    invalid = list(folder.glob("invalid-*.json"))
    print(f"{type_name}: {len(valid)} valid, {len(invalid)} invalid")
    assert len(valid) >= 2
    assert len(invalid) >= 1


@pytest.mark.parametrize("path", VALID, ids=rel)
def test_valid_example(path):
    type_name = type_for_path(path)
    validate(type_name, load(path))
    assert list(validator(type_name).iter_errors(load(path))) == []


@pytest.mark.parametrize("path", INVALID, ids=rel)
def test_invalid_example(path):
    type_name, instance = type_for_path(path), load(path)
    assert list(validator(type_name).iter_errors(instance)), "invalid example was accepted"
    acceptable = set(INDEX[rel(path)])
    found = error_keywords(type_name, instance)
    assert found & acceptable, f"failed on {sorted(found)}, expected one of {sorted(acceptable)}"


def test_invalid_index_complete():
    assert set(INDEX) == {rel(p) for p in INVALID}
    assert all(INDEX[key] for key in INDEX)


@pytest.mark.parametrize("path", ALL, ids=rel)
def test_example_formatting(path):
    """Pretty-printed with a 2-space indent and a trailing newline."""
    text = path.read_text(encoding="utf-8")
    assert text == json.dumps(json.loads(text), indent=2, ensure_ascii=False) + "\n"
