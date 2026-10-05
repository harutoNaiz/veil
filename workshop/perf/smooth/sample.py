"""PSS and thermal samplers (PHONE) plus dumpsys parsers."""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
import time
from pathlib import Path

from workshop.perf.schema import GUARD_PKG


def parse_meminfo_pss_kb(text: str) -> int:
    m = re.search(r"TOTAL PSS:\s*(\d+)", text) or re.search(r"^\s*TOTAL\s+(\d+)", text, re.M)
    if not m:
        raise ValueError("no TOTAL PSS in meminfo")
    return int(m.group(1))


def parse_thermal_status(text: str) -> int:
    m = re.search(r"Thermal Status:\s*(\d+)", text)
    if not m:
        raise ValueError("no Thermal Status")
    return int(m.group(1))


def throttle_cycle(stats: list[dict]) -> bool:
    seen = False
    for s in stats:
        if s.get("kind") != "stats":
            continue
        if s.get("phase") == "throttled":
            seen = True
        elif seen:
            return True
    return False


def adb(serial: str, *args: str) -> str:
    cmd = ["adb", *(["-s", serial] if serial else []), *args]
    return subprocess.run(cmd, capture_output=True, text=True, timeout=30).stdout


def has_device(serial: str | None) -> bool:
    try:
        out = subprocess.run(["adb", "devices"], capture_output=True, text=True, timeout=15).stdout
    except (OSError, subprocess.SubprocessError):
        return False
    devs = [ln.split()[0] for ln in out.splitlines()[1:] if ln.strip().endswith("device")]
    return bool(devs) and (not serial or serial in devs)


def run(serial: str, minutes: float, every_s: int = 10, out_dir: Path = Path(".")) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    pss = ["t_s,pss_kb"]
    th = ["t_s,thermal_status"]
    t0 = time.monotonic()
    while (t := time.monotonic() - t0) < minutes * 60:
        try:
            mem = parse_meminfo_pss_kb(adb(serial, "shell", "dumpsys", "meminfo", GUARD_PKG))
            pss.append(f"{t:.0f},{mem}")
            tst = parse_thermal_status(adb(serial, "shell", "dumpsys", "thermalservice"))
            th.append(f"{t:.0f},{tst}")
        except ValueError:
            pass
        time.sleep(every_s)
    (out_dir / "pss.csv").write_text("\n".join(pss) + "\n", encoding="utf-8")
    (out_dir / "thermal.csv").write_text("\n".join(th) + "\n", encoding="utf-8")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--serial")
    ap.add_argument("--minutes", type=float, default=30)
    ap.add_argument("--out", type=Path, default=Path("."))
    a = ap.parse_args()
    if not has_device(a.serial):
        print("NO DEVICE")
        return 2
    run(a.serial or "", a.minutes, out_dir=a.out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
