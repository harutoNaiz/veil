"""Phone recording (human-run): adb screenrecord in segments, pull, concat, downscale, events."""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
from pathlib import Path

from workshop.recordings.downscale import downscale
from workshop.recordings.estimate import estimate_scroll

SEGMENT_S = 180
PACKAGE = "com.veil.testfeed"


def _run(cmd: list[str], **kw):
    return subprocess.run(cmd, capture_output=True, text=True, **kw)


def plan(name: str, seconds: int, out: Path) -> list[list[str]]:
    """The adb / ffmpeg commands (uptime and wm size are queried first, not listed)."""
    cmds, left, k = [], seconds, 0
    segs = []
    while left > 0:
        n = min(SEGMENT_S, left)
        remote = f"/sdcard/veil_{name}_{k}.mp4"
        local = out / f"{name}.seg{k}.mp4"
        cmds.append(
            [
                "adb",
                "shell",
                "screenrecord",
                "--bit-rate",
                "8000000",
                "--time-limit",
                str(n),
                remote,
            ]
        )
        cmds.append(["adb", "pull", remote, str(local)])
        cmds.append(["adb", "shell", "rm", remote])
        segs.append(local)
        left -= n
        k += 1
    lst = out / f"{name}.concat.txt"
    cmds.append(
        [
            "ffmpeg",
            "-y",
            "-f",
            "concat",
            "-safe",
            "0",
            "-i",
            str(lst),
            "-c",
            "copy",
            str(out / f"{name}.orig.mp4"),
        ]
    )
    cmds.append(
        [
            "ffmpeg",
            "-y",
            "-i",
            str(out / f"{name}.orig.mp4"),
            "...downscale to 360x800",
            str(out / f"{name}.mp4"),
        ]
    )
    return cmds


def record(
    name: str,
    seconds: int,
    out: Path,
    situations: list[str] | None = None,
    events: Path | None = None,
    runner=_run,
) -> Path:
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    up = runner(["adb", "shell", "cat", "/proc/uptime"]).stdout.split()[0]
    t0 = int(float(up) * 1000)
    wm = runner(["adb", "shell", "wm", "size"]).stdout
    m = re.search(r"(\d+)x(\d+)", wm)
    sw, sh = (int(m.group(1)), int(m.group(2))) if m else (1080, 2400)
    cmds = plan(name, seconds, out)
    segs = []
    for c in cmds:
        if c[0] == "adb":
            runner(c)
            if c[1] == "pull":
                segs.append(Path(c[3]))
    lst = out / f"{name}.concat.txt"
    lst.write_text("".join(f"file '{p.resolve().as_posix()}'\n" for p in segs), encoding="utf-8")
    orig = out / f"{name}.orig.mp4"
    runner(cmds[-2])
    work = out / f"{name}.mp4"
    downscale(orig, work)
    cap = __import__("cv2").VideoCapture(str(work))
    frames, fps = int(cap.get(7)), cap.get(5) or 30.0
    cap.release()
    ev_path = out / f"{name}.events.jsonl"
    if events:
        shutil.copyfile(events, ev_path)
        scroll = "logged"
    else:
        est = estimate_scroll(work, sw, PACKAGE, fps=fps, t0_ms=t0)
        ev_path.write_bytes(
            "".join(json.dumps(e, sort_keys=True) + "\n" for e in est).encode("utf-8")
        )
        scroll = "estimated"
    session = {
        "sessionVersion": "1",
        "sessionId": name,
        "video": work.name,
        "fps": int(round(fps)),
        "frameCount": frames,
        "t0Ms": t0,
        "width": 360,
        "height": 800,
        "screenWidth": sw,
        "screenHeight": sh,
        "scroll": scroll,
        "source": "phone",
        "packageName": PACKAGE,
        "situations": {s: 1 for s in (situations or [])},
    }
    path = out / f"{name}.session.json"
    path.write_bytes(json.dumps(session, indent=1).encode("utf-8"))
    for p in segs:
        p.unlink(missing_ok=True)
    return path


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="python -m workshop.recordings.record")
    p.add_argument("--name", required=True)
    p.add_argument("--seconds", type=int, required=True)
    p.add_argument("--situations", default="")
    p.add_argument("--events", type=Path)
    p.add_argument("--out", type=Path, default=Path("data/recordings"))
    p.add_argument("--dry-run", action="store_true")
    a = p.parse_args(argv)
    if a.dry_run:
        print("adb shell cat /proc/uptime   # t0Ms = uptime * 1000 at start")
        for c in plan(a.name, a.seconds, a.out):
            print(" ".join(c))
        return 0
    sits = [s for s in a.situations.split(",") if s]
    print(record(a.name, a.seconds, a.out, sits, a.events))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
