"""Driver scripts: drive the phone from the laptop with adb (scroll, fling, tap, home).

python -m workshop.bench.drive scroll [--times 3] [--fraction 0.45] [--duration 250] [--pause 600]
python -m workshop.bench.drive fling | tap X Y | home          (add --serial S when several devices)
"""

from __future__ import annotations

import argparse
import sys
import time

from workshop.bench import adb


def scroll(
    serial: str,
    times: int = 3,
    fraction: float = 0.45,
    duration_ms: int = 250,
    pause_ms: int = 600,
) -> None:
    """Swipe up `times` times, each from (w/2, 0.75h) to (w/2, (0.75 - fraction)h)."""
    width, height = adb.screen_size(serial)
    x = width // 2
    y_from = int(0.75 * height)
    y_to = int((0.75 - fraction) * height)
    for _ in range(times):
        adb.swipe(serial, x, y_from, x, y_to, duration_ms)
        time.sleep(pause_ms / 1000)


def _parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="workshop.bench.drive", description=__doc__.split("\n")[0]
    )
    parser.add_argument(
        "--serial", help="adb serial (only needed when several devices are attached)"
    )
    sub = parser.add_subparsers(dest="command", required=True)
    p_scroll = sub.add_parser("scroll", help="slow swipes up")
    p_scroll.add_argument("--times", type=int, default=3)
    p_scroll.add_argument("--fraction", type=float, default=0.45)
    p_scroll.add_argument("--duration", type=int, default=250, help="swipe time in ms")
    p_scroll.add_argument("--pause", type=int, default=600, help="wait after each swipe in ms")
    sub.add_parser("fling", help="one fast, long swipe up")
    p_tap = sub.add_parser("tap", help="tap a screen position in px")
    p_tap.add_argument("x", type=int)
    p_tap.add_argument("y", type=int)
    sub.add_parser("home", help="press the Home key")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    try:
        serial = args.serial or adb.single_device()
        if serial is None:
            print("no adb device (connect the phone: HC-002)")
            return 3
        if args.command == "scroll":
            scroll(serial, args.times, args.fraction, args.duration, args.pause)
        elif args.command == "fling":
            width, height = adb.screen_size(serial)
            adb.swipe(serial, width // 2, int(0.85 * height), width // 2, int(0.15 * height), 80)
        elif args.command == "tap":
            adb.tap(serial, args.x, args.y)
        elif args.command == "home":
            adb.keyevent(serial, "KEYCODE_HOME")
    except adb.MultipleDevicesError as exc:
        print(str(exc))
        return 4
    except adb.AdbError as exc:
        print(f"adb error: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
