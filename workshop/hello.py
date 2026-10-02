"""Laptop "hello world": prints the Python version and the pinned main dependencies."""

from __future__ import annotations

import importlib.metadata
import importlib.util
import platform
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def _main_dependency_names() -> list[str]:
    """Names of [project].dependencies in pyproject.toml, in file order."""
    pyproject = tomllib.loads((ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    return [dep.split("==")[0].strip() for dep in pyproject["project"]["dependencies"]]


def main() -> int:
    print(f"Python {platform.python_version()}")
    for name in _main_dependency_names():
        print(f"{name}=={importlib.metadata.version(name)}")
    if importlib.util.find_spec("torch") is None:
        print("ml group: not installed (installed from Phase 1.3)")
    else:
        print("ml group: installed")
    print("Veil workshop OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
