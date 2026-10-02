"""Tape v1: writer and validator.  ``python -m workshop.replay.tape validate FILE...``"""

from __future__ import annotations

import functools
import json
import sys
from pathlib import Path

import jsonschema
from jsonschema.exceptions import best_match
from referencing import Resource
from referencing.jsonschema import DRAFT202012

from workshop.contracts.validate import SCHEMA_DIR, registry

TAPE_SCHEMA = "tape.schema.json"


def dumps(obj: dict) -> bytes:
    return (
        json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False) + "\n"
    ).encode("utf-8")


class TapeWriter:
    def __init__(self, path: Path, header: dict) -> None:
        self.path = Path(path)
        self._f = open(self.path, "wb")  # binary: always "\n"
        self._seq = 0
        self.write({"kind": "header", "tMs": header.get("t0Ms", 0), **header})

    def write(self, record: dict) -> None:
        rec = dict(record)
        rec["seq"] = self._seq
        self._seq += 1
        self._f.write(dumps(rec))

    def close(self) -> None:
        self._f.close()


@functools.cache
def validator() -> jsonschema.Draft202012Validator:
    schema = json.loads((SCHEMA_DIR / TAPE_SCHEMA).read_text(encoding="utf-8"))
    reg = registry().with_resource(
        TAPE_SCHEMA, Resource.from_contents(schema, default_specification=DRAFT202012)
    )
    return jsonschema.Draft202012Validator({"$ref": TAPE_SCHEMA}, registry=reg)


def check_line(obj: object) -> str | None:
    err = best_match(validator().iter_errors(obj))
    return None if err is None else err.message[:200]


def validate_file(path: Path) -> list[str]:
    errors: list[str] = []
    n = 0
    with open(path, "rb") as f:
        for i, raw in enumerate(f, 1):
            n += 1
            try:
                msg = check_line(json.loads(raw.decode("utf-8")))
            except ValueError as e:
                msg = f"bad json: {e}"
            if msg:
                errors.append(f"INVALID {path}:{i}: {msg}")
    if not errors:
        print(f"OK {path} {n} lines")
    return errors


def main(argv: list[str]) -> int:
    if len(argv) < 2 or argv[0] != "validate":
        print("usage: python -m workshop.replay.tape validate FILE...")
        return 2
    bad = 0
    for p in argv[1:]:
        for e in validate_file(Path(p)):
            print(e)
            bad += 1
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
