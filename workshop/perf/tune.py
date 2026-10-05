"""Twin params sync: python -m workshop.perf.tune [--set mode.group.key=value ...] --check."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
TWIN = ROOT / "workshop" / "twin" / "params.json"
ANDROID = ROOT / "guard" / "app" / "src" / "androidTest" / "assets" / "params.json"


def apply(sets: list[str], twin: Path = TWIN, android: Path = ANDROID) -> None:
    if sets:
        data = json.loads(twin.read_text(encoding="utf-8"))
        for s in sets:
            path, _, raw = s.partition("=")
            keys = path.split(".")
            node = data["modes"]
            for k in keys[:-1]:
                node = node[k]
            if keys[-1] not in node:
                raise KeyError(path)
            try:
                node[keys[-1]] = json.loads(raw)
            except json.JSONDecodeError:
                node[keys[-1]] = raw
        twin.write_text(json.dumps(data, indent=1) + "\n", encoding="utf-8")
    android.write_bytes(twin.read_bytes())


def in_sync(twin: Path = TWIN, android: Path = ANDROID) -> bool:
    return android.exists() and twin.read_bytes() == android.read_bytes()


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="workshop.perf.tune")
    p.add_argument("--set", action="append", default=[])
    p.add_argument("--check", action="store_true")
    a = p.parse_args(argv)
    if a.set:
        apply(a.set)
    if a.check and not in_sync():
        print("params differ")
        return 1
    print("params in sync")
    return 0


if __name__ == "__main__":
    sys.exit(main())
