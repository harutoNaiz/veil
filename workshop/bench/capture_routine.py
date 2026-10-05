"""Phase 4.1 driver routine ("Watch the watcher"): drives the phone, then pulls the logs.

python -m workshop.bench.capture_routine --dry-run          # print the plan only
python -m workshop.bench.capture_routine --minutes 5        # PHONE: needs APK + consent
"""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import threading
import time
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from workshop.bench import adb

REPO = Path(__file__).resolve().parents[2]
PKG = "com.veil.guard"
LOG_FILES = ("frames.jsonl", "state.jsonl")


@dataclass
class Step:
    name: str
    weight: float  # share of the total duration
    marker: str = ""  # event written to markers.jsonl at the start
    manual: str = ""  # prompt for a human step


PLAN = [
    Step("idle 30 s on the home screen (static)", 0.10, "idleStart"),
    Step("end idle, open Instagram and scroll", 0.15, "idleEnd"),
    Step("open YouTube and play a video", 0.15),
    Step("rotate to landscape then back", 0.10),
    Step(
        "lock and unlock (keyevents)",
        0.10,
        "lock",
        "Tap 'Resume Veil' / accept consent if prompted",
    ),
    Step(
        "tap the capture status-bar chip once",
        0.05,
        manual="Tap the capture chip in the status bar",
    ),
    Step(
        "force-stop com.veil.guard",
        0.10,
        "kill",
        "Tap 'Resume Veil' / accept consent when prompted",
    ),
    Step("open Netflix (expect black frames)", 0.15),
    Step("end", 0.10),
]
LAUNCH = {
    "Instagram": "com.instagram.android",
    "YouTube": "com.google.android.youtube",
    "Netflix": "com.netflix.mediaclient",
}


def print_plan(minutes: float) -> None:
    total = minutes * 60
    print(f"capture routine plan, {minutes:g} min (scrcpy record, meminfo/10 s, pull logs)")
    for i, s in enumerate(PLAN, 1):
        extra = f"  [marker {s.marker}]" if s.marker else ""
        extra += f"  [MANUAL: {s.manual}]" if s.manual else ""
        print(f"  {i}. {s.name}: {s.weight * total:.0f} s{extra}")


def uptime_ms(serial: str) -> int:
    return int(float(adb.shell(serial, "cat /proc/uptime").split()[0]) * 1000)


def open_app(serial: str, package: str) -> None:
    adb.shell(serial, f"monkey -p {package} -c android.intent.category.LAUNCHER 1")


def sample_meminfo(serial: str, out: list[dict], stop: threading.Event) -> None:
    while not stop.is_set():
        text = adb.shell(serial, f"dumpsys meminfo {PKG}")
        for line in text.splitlines():
            if line.strip().startswith("TOTAL PSS:") or line.strip().startswith("TOTAL "):
                parts = line.split()
                digits = [p for p in parts if p.isdigit()]
                if digits:
                    out.append({"tMs": uptime_ms(serial), "pssKb": int(digits[0])})
                    break
        stop.wait(10)


def run_step(serial: str, step: Step) -> None:
    n = step.name
    if n.startswith("end idle"):
        open_app(serial, LAUNCH["Instagram"])
        time.sleep(3)
        for _ in range(6):
            adb.swipe(serial, 700, 2400, 700, 900, 300)
            time.sleep(1.5)
    elif n.startswith("open YouTube"):
        open_app(serial, LAUNCH["YouTube"])
    elif n.startswith("rotate"):
        adb.shell(serial, "settings put system accelerometer_rotation 0")
        adb.shell(serial, "settings put system user_rotation 1")
        time.sleep(5)
        adb.shell(serial, "settings put system user_rotation 0")
    elif n.startswith("lock"):
        adb.keyevent(serial, "KEYCODE_POWER")
        time.sleep(2)
        adb.keyevent(serial, "KEYCODE_POWER")
        time.sleep(1)
        adb.keyevent(serial, "KEYCODE_MENU")
    elif n.startswith("force-stop"):
        adb.force_stop(serial, PKG)
    elif n.startswith("open Netflix"):
        open_app(serial, LAUNCH["Netflix"])


def run(minutes: float, serial: str | None) -> Path:
    serial = serial or adb.single_device()
    if not serial:
        raise SystemExit("no single phone connected")
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    out = REPO / "data" / "capture" / stamp
    out.mkdir(parents=True, exist_ok=True)
    scrcpy = shutil.which("scrcpy")
    rec = (
        subprocess.Popen(
            [scrcpy, f"--serial={serial}", f"--record={out / 'screen.mp4'}", "--no-playback"]
        )
        if scrcpy
        else None
    )
    mem: list[dict] = []
    stop = threading.Event()
    sampler = threading.Thread(target=sample_meminfo, args=(serial, mem, stop), daemon=True)
    sampler.start()
    markers: list[dict] = []
    for step in PLAN:
        if step.marker:
            markers.append({"tMs": uptime_ms(serial), "event": step.marker})
        print("->", step.name)
        if step.manual:
            input(f"   MANUAL: {step.manual} - press Enter when done ")
        run_step(serial, step)
        time.sleep(max(0.0, step.weight * minutes * 60))
    stop.set()
    sampler.join(timeout=15)
    if rec:
        rec.terminate()
    for name in LOG_FILES:
        try:
            (out / name).write_bytes(adb.run_as_cat(serial, PKG, f"files/capture/{name}"))
        except adb.AdbError as e:
            print(f"could not pull {name}: {e}", file=sys.stderr)
    (out / "meminfo.jsonl").write_text("".join(json.dumps(r) + "\n" for r in mem), encoding="utf-8")
    (out / "markers.jsonl").write_text(
        "".join(json.dumps(r) + "\n" for r in markers), encoding="utf-8"
    )
    print("logs in", out)
    return out


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--minutes", type=float, default=5)
    ap.add_argument("--dry-run", action="store_true")
    ap.add_argument("--serial", default=None)
    args = ap.parse_args(argv)
    if args.dry_run:
        print_plan(args.minutes)
        return 0
    run(args.minutes, args.serial)
    return 0


if __name__ == "__main__":
    sys.exit(main())
