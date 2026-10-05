"""PHONE: one timed battery session (background-friendly). Exit 2 `NO DEVICE` without a phone."""

from __future__ import annotations

import argparse
import json
import random
import sys
import time
from pathlib import Path

from workshop.bench import adb, drive
from workshop.perf.battery import stats
from workshop.perf.schema import GUARD_PKG, IG_PKG


def run(serial: str, label: str, mode: str, minutes: int, brightness: int, runs_path: Path) -> dict:
    adb.shell(serial, "dumpsys batterystats --reset")
    adb.shell(serial, "settings put system screen_brightness_mode 0")
    adb.shell(serial, f"settings put system screen_brightness {brightness}")
    start = stats.parse_level(adb.shell(serial, "dumpsys battery"))
    if mode != "off":
        # Receiver (CaptureCommandReceiver): --es cmd <cmd> [--es value <v>]; "mode" cmd assumed.
        adb.shell(
            serial,
            f"am broadcast -a com.veil.guard.capture.CMD --es cmd mode --es value {mode}",
        )
    adb.shell(serial, f"monkey -p {IG_PKG} -c android.intent.category.LAUNCHER 1")
    rng = random.Random(53)
    end_t = time.monotonic() + minutes * 60
    while time.monotonic() < end_t:
        drive.scroll(serial, times=1)
        time.sleep(rng.uniform(3, 8))
    end = stats.parse_level(adb.shell(serial, "dumpsys battery"))
    dump = adb.shell(serial, "dumpsys batterystats --charged", timeout=120)
    uid = stats.parse_uid(adb.shell(serial, f"dumpsys package {GUARD_PKG}"))
    rec = {
        "label": label,
        "mode": mode,
        "minutes": minutes,
        "brightness": brightness,
        "startLevel": start,
        "endLevel": end,
        "network": adb.shell(serial, "settings get global wifi_on").strip() or "unknown",
        "guardMah": stats.parse_uid_mah(dump, GUARD_PKG, uid),
    }
    prev = json.loads(runs_path.read_text("utf-8")) if runs_path.exists() else []
    runs_path.parent.mkdir(parents=True, exist_ok=True)
    runs_path.write_text(json.dumps(prev + [rec], indent=1), encoding="utf-8")
    return rec


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="workshop.perf.battery.session")
    p.add_argument("--label", default="A-on")
    p.add_argument("--mode", default="balanced", choices=["off", "light", "balanced", "strict"])
    p.add_argument("--minutes", type=int, default=30)
    p.add_argument("--brightness", type=int, default=128)
    p.add_argument("--runs", default="data/ch5/perf/runs.json")
    p.add_argument("--serial")
    a = p.parse_args(argv)
    try:
        serial = a.serial or adb.single_device()
    except adb.AdbError as exc:
        print(f"NO DEVICE ({exc})")
        return 2
    if not serial:
        print("NO DEVICE")
        return 2
    print(run(serial, a.label, a.mode, a.minutes, a.brightness, Path(a.runs)))
    return 0


if __name__ == "__main__":
    sys.exit(main())
