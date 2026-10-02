"""Check a screenshots folder: every PNG has a valid sidecar from an allowed source.

python -m workshop.screens.meta_check --screens DIR
Also fails if anything but data/README.md under `data/` is tracked by git (AC-1.2-07).
Exit 0 ok, 1 problems found, 2 bad input.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path

from PIL import Image
from pydantic import ValidationError

from workshop.contracts.models import ScreenLabelMeta
from workshop.screens.capture import read_sources

REPO_ROOT = Path(__file__).resolve().parents[2]
NAME_RE = re.compile(r"^[a-z0-9-]+-\d{4}(-dup)?\.png$")
META_KEYS = ("app", "surface", "mode", "orientation", "source")
SIDECAR_KEYS = {*META_KEYS, "capturedAt"}


def tracked_data_files(repo_root: Path) -> list[str]:
    """Files under `data/` that git tracks, other than data/README.md ([] if git is absent)."""
    try:
        done = subprocess.run(
            ["git", "-C", str(repo_root), "ls-files", "data"],
            capture_output=True,
            text=True,
            timeout=30,
        )
    except (OSError, subprocess.TimeoutExpired):
        return []
    if done.returncode != 0:
        return []
    return [line for line in done.stdout.splitlines() if line and line != "data/README.md"]


def _check_sidecar(png: Path, allowed: list[str]) -> list[str]:
    name = png.name
    sidecar = png.with_suffix(".json")
    if not sidecar.is_file():
        return [f"{name}: missing sidecar {sidecar.name}"]
    try:
        data = json.loads(sidecar.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        return [f"{name}: sidecar unreadable ({exc})"]
    if not isinstance(data, dict):
        return [f"{name}: sidecar is not a JSON object"]
    problems = []
    missing = sorted(SIDECAR_KEYS - data.keys())
    extra = sorted(data.keys() - SIDECAR_KEYS)
    if missing:
        problems.append(f"{name}: sidecar lacks {', '.join(missing)}")
    if extra:
        problems.append(f"{name}: sidecar has unknown keys {', '.join(extra)}")
    try:
        meta = ScreenLabelMeta(**{k: data[k] for k in META_KEYS if k in data})
    except (ValidationError, TypeError) as exc:
        return [*problems, f"{name}: invalid sidecar ({str(exc).splitlines()[0]})"]
    if meta.source not in allowed:
        problems.append(f"{name}: source {meta.source!r} is not in sources.txt")
    stamp = data.get("capturedAt")
    if stamp is not None:
        try:
            datetime.fromisoformat(str(stamp).replace("Z", "+00:00"))
        except ValueError:
            problems.append(f"{name}: capturedAt {stamp!r} is not an ISO time")
    try:
        with Image.open(png) as image:
            width, height = image.size
    except OSError:
        return [*problems, f"{name}: not a readable image"]
    if meta.orientation != ("landscape" if width > height else "portrait"):
        problems.append(f"{name}: orientation {meta.orientation} does not match {width}x{height}")
    return problems


def check(screens: Path, git: bool = True) -> list[str]:
    """Problems found in `screens` (empty list = ok)."""
    if not screens.is_dir():
        return [f"{screens}: not a folder"]
    pngs = sorted(screens.glob("*.png"))
    problems: list[str] = []
    allowed = read_sources(screens / "sources.txt")
    if pngs and not allowed:
        problems.append("sources.txt is missing or lists no source")
    for png in pngs:
        if not NAME_RE.match(png.name):
            problems.append(f"{png.name}: name does not match <app>-<surface>-NNNN.png")
        problems.extend(_check_sidecar(png, allowed))
    for sidecar in sorted(screens.glob("*.json")):
        if sidecar.name != "truth.json" and not sidecar.with_suffix(".png").is_file():
            problems.append(f"{sidecar.name}: sidecar without a PNG")
    if git:
        problems.extend(f"tracked by git: {path}" for path in tracked_data_files(REPO_ROOT))
    return problems


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="workshop.screens.meta_check", description=__doc__)
    parser.add_argument("--screens", type=Path, required=True)
    args = parser.parse_args(argv)
    if not args.screens.is_dir():
        print(f"not a folder: {args.screens}", file=sys.stderr)
        return 2
    problems = check(args.screens)
    for line in problems:
        print(line)
    if problems:
        return 1
    print(f"META OK {len(list(args.screens.glob('*.png')))}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
