"""pre-commit hook: format Kotlin files under guard/ with the toolchain's ktlint."""

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
    java = Path(java_home) / "bin" / "java.exe"
    jar = Path(toolchain) / "ktlint" / "ktlint.jar"
    for tool in (java, jar):
        if not tool.exists():
            print(HINT.format(path=tool))
            return 2
    return subprocess.call([str(java), "-jar", str(jar), "--format", "--relative", *argv])


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
