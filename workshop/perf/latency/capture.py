"""PHONE: capture a perfetto trace + Guard debug.jsonl + Test Feed feedlog.jsonl.

python -m workshop.perf.latency.capture --minutes 5      (exit 2 "NO DEVICE" without a phone)
"""

from __future__ import annotations

import argparse
import sys
import time
from datetime import datetime
from pathlib import Path

from workshop.bench import adb
from workshop.bench.drive import scroll
from workshop.perf.schema import FEED_PKG, GUARD_PKG

TRACE = "/data/misc/perfetto-traces/veil-latency.pftrace"


def _config(minutes: int) -> str:
    return (
        f"duration_ms: {minutes * 60000} "
        "buffers { size_kb: 65536 } "
        'data_sources { config { name: "linux.ftrace" ftrace_config { '
        'ftrace_events: "sched/sched_switch" atrace_categories: "gfx" '
        'atrace_categories: "view" atrace_categories: "am" '
        f'atrace_apps: "{GUARD_PKG}" }} }} }}'
    )


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="workshop.perf.latency.capture")
    ap.add_argument("--minutes", type=int, default=5)
    ap.add_argument("--serial")
    a = ap.parse_args(argv)
    try:
        serial = a.serial or adb.single_device()
    except adb.AdbError:
        serial = None
    if serial is None:
        print("NO DEVICE")
        return 2
    out = Path("data/ch5/perf") / datetime.now().strftime("%Y%m%d-%H%M%S")
    out.mkdir(parents=True, exist_ok=True)
    cfg = _config(a.minutes)
    adb.shell(
        serial,
        f"nohup sh -c \"echo '{cfg}' | perfetto -c - --txt -o {TRACE}\" >/dev/null 2>&1 &",
    )
    end = time.time() + a.minutes * 60
    while time.time() < end:
        scroll(serial, times=3)
    time.sleep(5)
    for pkg, rel, name in (
        (GUARD_PKG, "files/debug.jsonl", "debug.jsonl"),
        (FEED_PKG, "files/feedlog.jsonl", "feedlog.jsonl"),
    ):
        (out / name).write_bytes(adb.run_as_cat(serial, pkg, rel))
    adb.run(["pull", TRACE, str(out / "trace.pftrace")], serial, timeout=120)
    print(f"captured -> {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
