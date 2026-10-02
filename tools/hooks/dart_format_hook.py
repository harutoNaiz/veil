"""pre-commit hook: format Dart files under console/ with the toolchain's Dart SDK."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

HINT = "run '. .\\tools\\env.ps1' (or 'source tools/env.sh') first; toolchain not found: {path}"


def main(argv: list[str]) -> int:
    toolchain = os.environ.get("VEIL_TOOLCHAIN")
    java_home = os.environ.get("JAVA_HOME")
    if not toolchain or not java_home:
        print(HINT.format(path=toolchain or "(VEIL_TOOLCHAIN is not set)"))
        return 2
    dart = Path(toolchain) / "flutter" / "bin" / "cache" / "dart-sdk" / "bin" / "dart.exe"
    if not dart.exists():
        print(HINT.format(path=dart))
        return 2
    return subprocess.call([str(dart), "format", *argv])


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
