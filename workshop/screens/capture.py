"""Capture scroll-by-scroll screenshots of one app surface, with a sidecar per PNG.

python -m workshop.screens.capture --app instagram --surface explore --mode dark \
    --source test-acct-A [--count 10] [--scroll-fraction 0.6] [--pause 1200] \
    [--out data/screens] [--serial S]

Files: `<out>/<app>-<surface>-NNNN.png` + `<same stem>.json`. The source id must be listed in
`<out>/sources.txt` (created with the given id when absent). Exit 0 ok, 2 bad input, 3 no device.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from datetime import UTC, datetime
from pathlib import Path

from PIL import Image

from workshop.bench import adb, drive

NAME_RE = re.compile(r"^[a-z0-9-]+$")
SOURCE_RE = re.compile(r"^[A-Za-z0-9._-]{1,40}$")
MODES = ("dark", "light")
DEFAULT_OUT = Path("data/screens")


def read_sources(path: Path) -> list[str]:
    """Allowed source ids: one per line, `#` starts a comment line."""
    if not path.is_file():
        return []
    lines = (line.strip() for line in path.read_text(encoding="utf-8").splitlines())
    return [line for line in lines if line and not line.startswith("#")]


def validate_args(app: str, surface: str, mode: str, source: str, count: int) -> None:
    """Raise ValueError for a bad app/surface/mode/source/count (pure; touches no files)."""
    if not NAME_RE.match(app):
        raise ValueError(f"bad app {app!r}: use lower-case letters, digits and '-'")
    if not NAME_RE.match(surface) or len(surface) > 40:
        raise ValueError(f"bad surface {surface!r}: use lower-case letters, digits and '-' (<= 40)")
    if mode not in MODES:
        raise ValueError(f"bad mode {mode!r}: use dark or light")
    if not SOURCE_RE.match(source):
        raise ValueError(f"bad source {source!r}")
    if count < 1:
        raise ValueError("count must be at least 1")


def _next_index(out: Path, app: str, surface: str) -> int:
    pattern = re.compile(rf"^{re.escape(app)}-{re.escape(surface)}-(\d{{4}})\.png$")
    used = [int(m.group(1)) for p in out.glob("*.png") if (m := pattern.match(p.name))]
    return max(used, default=0) + 1


def capture(
    serial: str,
    out: Path,
    app: str,
    surface: str,
    mode: str,
    source: str,
    count: int,
    scroll_fraction: float,
    pause_ms: int,
) -> list[Path]:
    """Take `count` screenshots, scrolling after each; return the PNG paths written."""
    validate_args(app, surface, mode, source, count)
    out.mkdir(parents=True, exist_ok=True)
    sources_file = out / "sources.txt"
    if not sources_file.is_file():
        sources_file.write_text(f"{source}\n", encoding="utf-8")
        print(f"notice: created {sources_file} with source {source!r}")
    elif source not in read_sources(sources_file):
        raise ValueError(f"source {source!r} is not listed in {sources_file}")
    written: list[Path] = []
    index = _next_index(out, app, surface)
    for _ in range(count):
        png = out / f"{app}-{surface}-{index:04d}.png"
        adb.screencap(serial, png)
        with Image.open(png) as image:
            width, height = image.size
        sidecar = {
            "app": app,
            "surface": surface,
            "mode": mode,
            "orientation": "landscape" if width > height else "portrait",
            "source": source,
            "capturedAt": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        }
        png.with_suffix(".json").write_text(json.dumps(sidecar, indent=2) + "\n", encoding="utf-8")
        written.append(png)
        drive.scroll(serial, times=1, fraction=scroll_fraction, pause_ms=pause_ms)
        index += 1
    return written


def _parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="workshop.screens.capture", description="Capture scroll-by-scroll screenshots."
    )
    parser.add_argument("--app", required=True)
    parser.add_argument("--surface", required=True)
    parser.add_argument("--mode", required=True, choices=MODES)
    parser.add_argument("--source", required=True, help="test account id listed in sources.txt")
    parser.add_argument("--count", type=int, default=10)
    parser.add_argument("--scroll-fraction", type=float, default=0.6)
    parser.add_argument("--pause", type=int, default=1200, help="wait after each scroll in ms")
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--serial", help="adb serial (only needed when several devices)")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    try:
        validate_args(args.app, args.surface, args.mode, args.source, args.count)
    except ValueError as exc:
        print(f"bad input: {exc}", file=sys.stderr)
        return 2
    try:
        serial = args.serial or adb.single_device()
        if serial is None:
            print("no adb device (connect the phone: HC-002)")
            return 3
        paths = capture(
            serial,
            args.out,
            args.app,
            args.surface,
            args.mode,
            args.source,
            args.count,
            args.scroll_fraction,
            args.pause,
        )
    except ValueError as exc:
        print(f"bad input: {exc}", file=sys.stderr)
        return 2
    except adb.MultipleDevicesError as exc:
        print(str(exc))
        return 4
    except adb.AdbError as exc:
        print(f"adb error: {exc}", file=sys.stderr)
        return 1
    print(f"captured {len(paths)} screenshots into {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
