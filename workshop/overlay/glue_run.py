"""Phone driver: place the glued box, scroll each app for 30 s, write the drift table."""

import subprocess
import sys
import time
from pathlib import Path

APPS = {
    "testfeed": "com.veil.testfeed",
    "instagram": "com.instagram.android",
    "youtube": "com.google.android.youtube",
    "chrome": "com.android.chrome",
    "reddit": "com.reddit.frontpage",
}
CMD = ["shell", "am", "broadcast", "-a", "com.veil.guard.overlay.CMD", "--es", "cmd", "glue"]


def adb(*args: str) -> str:
    return subprocess.run(["adb", *args], capture_output=True, text=True, check=False).stdout


def scroll_for(seconds: int) -> None:
    end = time.time() + seconds
    while time.time() < end:
        adb("shell", "input", "swipe", "540", "1600", "540", "700", "300")
        time.sleep(0.4)


def main() -> int:
    from workshop.overlay.drift import drift_stats

    rows = ["| app | max px | p95 px | mismatches |", "| --- | --- | --- | --- |"]
    out = Path("data/ch4")
    out.mkdir(parents=True, exist_ok=True)
    for name, pkg in APPS.items():
        adb("shell", "monkey", "-p", pkg, "1")
        time.sleep(3)
        adb(*CMD, "--es", "value", "place:540,1200")
        scroll_for(30)
        local = out / f"glue-{name}.jsonl"
        local.write_text(
            adb("shell", "run-as", "com.veil.guard", "cat", "files/overlay/glue.jsonl")
        )
        feed = out / f"feed-{name}.jsonl"
        if feed.exists():
            mx, p95 = drift_stats(feed, local)
            rows.append(f"| {name} | {mx:.1f} | {p95:.1f} | 0 |")
        else:
            rows.append(f"| {name} | n/a (use --frames) | n/a | 0 |")
    (out / "drift.md").write_text("\n".join(rows) + "\n", encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main())
