"""Kill-recovery test for com.veil.guard only (PHONE)."""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

from workshop.perf.schema import GUARD_PKG
from workshop.perf.smooth.sample import adb, has_device


def judge(rows: list[dict]) -> bool:
    return len(rows) >= 5 and all(
        r.get("recoveredMs") is not None and r["recoveredMs"] <= 5000 for r in rows
    )


def _pid(serial: str) -> str:
    return adb(serial, "shell", "pidof", GUARD_PKG).strip()


def run(serial: str, times: int = 5, out: Path = Path("kills.jsonl")) -> list[dict]:
    rows = []
    for i in range(times):
        old = _pid(serial)
        if old:
            adb(serial, "shell", "run-as", GUARD_PKG, "kill", "-9", old.split()[0])
        t0 = time.monotonic()
        rec, how = None, None
        while (el := (time.monotonic() - t0) * 1000) <= 5000:
            pid = _pid(serial)
            svc = adb(serial, "shell", "dumpsys", "activity", "services", GUARD_PKG)
            if pid and pid != old and "ServiceRecord" in svc:
                rec, how = int(el), "service"
                break
            if "Resume Veil" in adb(serial, "shell", "dumpsys", "notification", "--noredact"):
                rec, how = int(el), "notification"
                break
            time.sleep(0.25)
        rows.append({"i": i, "recoveredMs": rec, "how": how})
        with out.open("a", encoding="utf-8") as f:
            f.write(json.dumps(rows[-1]) + "\n")
        time.sleep(3)
    return rows


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--serial")
    ap.add_argument("--times", type=int, default=5)
    ap.add_argument("--out", type=Path, default=Path("kills.jsonl"))
    a = ap.parse_args()
    if not has_device(a.serial):
        print("NO DEVICE")
        return 2
    rows = run(a.serial or "", a.times, a.out)
    return 0 if judge(rows) else 1


if __name__ == "__main__":
    sys.exit(main())
