"""The generated pydantic models accept every valid example and dump it back to a valid one."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from workshop.contracts import model_class
from workshop.contracts.validate import SCHEMA_DIR, type_for_path, validate

EXAMPLES = SCHEMA_DIR / "examples"
VALID = sorted(EXAMPLES.glob("*/valid-*.json"))


def rel(path: Path) -> str:
    return path.relative_to(EXAMPLES).as_posix()


@pytest.mark.parametrize("path", VALID, ids=rel)
def test_model_parses_valid_example(path):
    obj = json.loads(path.read_text(encoding="utf-8"))
    model_class(type_for_path(path)).model_validate(obj)


@pytest.mark.parametrize("path", VALID, ids=rel)
def test_model_dump_revalidates(path):
    type_name = type_for_path(path)
    obj = json.loads(path.read_text(encoding="utf-8"))
    dumped = model_class(type_name).model_validate(obj).model_dump(mode="json", exclude_none=True)
    validate(type_name, dumped)
