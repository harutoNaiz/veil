"""Validate JSON documents against the Veil contract schemas.

Command line::

    python -m workshop.contracts.validate FILE [FILE ...] [--type T] [--jsonl]

Prints ``OK <Type> <file>`` or ``INVALID <Type> <file>: <message>`` per document and exits 0
only if every document is valid. Without ``--type`` the type comes from the name of the
``contracts/examples/<type>/`` folder that holds the file.
"""

from __future__ import annotations

import argparse
import functools
import json
from pathlib import Path

import jsonschema
from jsonschema.exceptions import ValidationError, best_match
from referencing import Registry, Resource
from referencing.jsonschema import DRAFT202012

from workshop.contracts import TYPE_FILES, TYPES, example_dir

REPO_ROOT: Path = Path(__file__).resolve().parents[2]
SCHEMA_DIR: Path = REPO_ROOT / "contracts"


def load_schema(type_name: str) -> dict:
    """Read the schema file of a type from ``contracts/``."""
    if type_name not in TYPE_FILES:
        raise KeyError(f"unknown contract type: {type_name}")
    path = SCHEMA_DIR / TYPE_FILES[type_name]
    return json.loads(path.read_text(encoding="utf-8"))


@functools.cache
def registry() -> Registry:
    """Every schema registered under its file name, so relative ``$ref``s resolve."""
    resources = [
        (
            file_name,
            Resource.from_contents(load_schema(type_name), default_specification=DRAFT202012),
        )
        for type_name, file_name in TYPE_FILES.items()
    ]
    return Registry().with_resources(resources)


@functools.cache
def validator(type_name: str) -> jsonschema.Draft202012Validator:
    """A validator for one type; relative references resolve by file name."""
    return jsonschema.Draft202012Validator({"$ref": TYPE_FILES[type_name]}, registry=registry())


def validate(type_name: str, instance: object) -> None:
    """Raise ``jsonschema.ValidationError`` (the best match) if the instance is invalid."""
    error = best_match(validator(type_name).iter_errors(instance))
    if error is not None:
        raise error


def error_keywords(type_name: str, instance: object) -> set[str]:
    """Every failing keyword, recursing into the context of oneOf/anyOf errors."""
    found: set[str] = set()

    def walk(errors: object) -> None:
        for error in errors:  # type: ignore[attr-defined]
            if error.validator is not None:
                found.add(str(error.validator))
            if error.context:
                walk(error.context)

    walk(validator(type_name).iter_errors(instance))
    return found


def type_for_path(path: Path) -> str:
    """The type of an example file, from the name of its ``examples/<type>/`` folder."""
    folder = Path(path).resolve().parent.name
    for type_name in TYPES:
        if example_dir(type_name) == folder:
            return type_name
    raise ValueError(f"cannot tell the contract type of {path}; pass --type")


def _documents(path: Path, jsonl: bool) -> list[tuple[str, object]]:
    text = path.read_text(encoding="utf-8")
    if not jsonl:
        return [(str(path), json.loads(text))]
    docs: list[tuple[str, object]] = []
    for number, line in enumerate(text.splitlines(), start=1):
        if line.strip():
            docs.append((f"{path}:{number}", json.loads(line)))
    return docs


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m workshop.contracts.validate",
        description="Validate JSON files against the Veil contract schemas.",
    )
    parser.add_argument("files", nargs="+", type=Path, help="JSON files to validate")
    parser.add_argument(
        "--type", dest="type_name", choices=TYPES, help="contract type of every file"
    )
    parser.add_argument(
        "--jsonl", action="store_true", help="each line of each file is one document"
    )
    args = parser.parse_args(argv)

    ok = True
    for path in args.files:
        try:
            type_name = args.type_name or type_for_path(path)
        except ValueError as exc:
            print(f"INVALID ? {path}: {exc}")
            ok = False
            continue
        try:
            documents = _documents(path, args.jsonl)
        except (OSError, ValueError) as exc:
            print(f"INVALID {type_name} {path}: {exc}")
            ok = False
            continue
        for label, instance in documents:
            try:
                validate(type_name, instance)
            except ValidationError as exc:
                where = "/".join(str(part) for part in exc.absolute_path) or "(root)"
                detail = f"{exc.message} [at {where}, keyword {exc.validator}]"
                print(f"INVALID {type_name} {label}: {detail}")
                ok = False
            else:
                print(f"OK {type_name} {label}")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
