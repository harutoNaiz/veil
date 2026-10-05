"""Lint final.md: every number is a labelled, sourced table row."""

from __future__ import annotations

import re
import sys
from pathlib import Path

HEAD = ["id", "claim", "value", "status", "conditions", "source"]


def lint(text: str, root: Path) -> list[str]:
    errs: list[str] = []
    seen: set[str] = set()
    for n, line in enumerate(text.splitlines(), 1):
        s = line.strip()
        if s.startswith("|"):
            cells = [c.strip() for c in s.strip("|").split("|")]
            if cells == HEAD or set("".join(cells)) <= set("-: "):
                continue
            if len(cells) != 6:
                errs.append(f"line {n}: row does not have 6 cells")
                continue
            rid, _, value, status, cond, src = cells
            if rid in seen:
                errs.append(f"line {n}: duplicate id {rid}")
            seen.add(rid)
            if re.search(r"\d", value) and status != "measured":
                errs.append(f"line {n}: {rid} has a number but status is {status}")
            if status == "measured":
                if not cond:
                    errs.append(f"line {n}: {rid} measured with empty conditions")
                if not src or not (root / src).exists():
                    errs.append(f"line {n}: {rid} source path missing: {src}")
        elif re.search(r"\d", s) and not s.startswith(("Build:", "Date:")):
            errs.append(f"line {n}: number outside a table row")
    return errs


def main(argv=None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    root = Path(".")
    if "--root" in args:
        i = args.index("--root")
        root = Path(args[i + 1])
        del args[i : i + 2]
    errs = lint(Path(args[0]).read_text(encoding="utf-8"), root)
    for e in errs:
        print(e)
    print("LINT FAIL" if errs else "LINT OK")
    return 1 if errs else 0


if __name__ == "__main__":
    raise SystemExit(main())
