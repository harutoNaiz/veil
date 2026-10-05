"""Janky-frame % from dumpsys gfxinfo, service off vs on (phone)."""

from __future__ import annotations

import argparse
import re
import subprocess
import sys

_RE = re.compile(r"Janky frames:\s*\d+\s*\(([\d.]+)%\)")
SERVICE = "com.veil.guard/com.veil.guard.signals.GuardAccessibilityService"


def parse_janky(text: str) -> float | None:
    m = _RE.search(text)
    return float(m[1]) if m else None


def _adb(*args: str) -> str:
    return subprocess.run(["adb", *args], capture_output=True, text=True, check=False).stdout


def measure(pkg: str, n: int) -> float | None:
    _adb("shell", "dumpsys", "gfxinfo", pkg, "reset")
    for _ in range(n):
        _adb("shell", "input", "swipe", "540", "1700", "540", "600", "300")
    return parse_janky(_adb("shell", "dumpsys", "gfxinfo", pkg))


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--package", default="com.instagram.android")
    ap.add_argument("--scrolls", type=int, default=30)
    a = ap.parse_args(argv)
    _adb("shell", "settings", "put", "secure", "enabled_accessibility_services", "")
    off = measure(a.package, a.scrolls)
    _adb("shell", "settings", "put", "secure", "enabled_accessibility_services", SERVICE)
    on = measure(a.package, a.scrolls)
    if off is None or on is None:
        print("FRAMES: FAIL (no gfxinfo data)")
        return 1
    diff = on - off
    print(f"janky off={off:.2f}% on={on:.2f}% diff={diff:+.2f} pp")
    print(f"FRAMES: {'PASS' if diff <= 1 else 'FAIL'}")
    return 0 if diff <= 1 else 1


if __name__ == "__main__":
    sys.exit(main())
