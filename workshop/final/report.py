"""Generate docs/reports/final.md from measured result files."""

from __future__ import annotations

import argparse
import datetime
import subprocess
from pathlib import Path

from workshop.final.sources import AREAS

HEADER = "| id | claim | value | status | conditions | source |"
LIMITS = """## Limits

- Protected video (for example Netflix) cannot be seen, so it is not covered.
- A short delay passes before a cover appears on new content.
- Laptop numbers are not phone numbers; only the Phone table is from the phone.
"""


def build_id(root: Path) -> str:
    try:
        r = subprocess.run(
            ["git", "rev-parse", "--short", "HEAD"], cwd=root, capture_output=True, text=True
        )
        return r.stdout.strip() or "unknown"
    except OSError:
        return "unknown"


def render(root: Path, build: str | None = None, date: str | None = None) -> str:
    build = build or build_id(root)
    date = date or datetime.date.today().isoformat()
    lines = [
        "# Veil final evaluation",
        "",
        f"Build: {build} | Date: {date}",
        "",
        "## How to read",
        "",
        "measured means the value came from a result file. PENDING-HUMAN means it is not",
        "measured yet. Nothing here is estimated or carried forward from older runs.",
        "",
    ]
    for title, loader in AREAS:
        lines += [f"## {title}", "", HEADER, "| --- | --- | --- | --- | --- | --- |"]
        for r in loader(root):
            lines.append("| " + " | ".join(x.replace("|", "/") for x in r) + " |")
        lines.append("")
    lines.append(LIMITS)
    return "\n".join(lines)


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="docs/reports/final.md")
    ap.add_argument("--root", default=".")
    a = ap.parse_args(argv)
    root = Path(a.root)
    out = root / a.out
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(render(root), encoding="utf-8")
    print(f"wrote {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
