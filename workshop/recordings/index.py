"""Index a folder of sessions and report AC-2.1-01 / AC-2.1-02."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

SITUATIONS = (
    "slowScroll",
    "fling",
    "reelsSwipe",
    "exploreGrid",
    "videoSceneCut",
    "appSwitch",
    "lockUnlock",
)


def build(folder: Path) -> dict:
    sessions = []
    for p in sorted(Path(folder).glob("*.session.json")):
        s = json.loads(p.read_text(encoding="utf-8"))
        sessions.append(
            {
                "sessionId": s["sessionId"],
                "seconds": s["frameCount"] / s["fps"],
                "scroll": s["scroll"],
                "source": s["source"],
                "situations": s.get("situations", {}),
            }
        )
    total = sum(x["seconds"] for x in sessions)
    sit = {k: sum(x["situations"].get(k, 0) for x in sessions) for k in SITUATIONS}
    logged = sum(1 for x in sessions if x["scroll"] == "logged")
    return {
        "sessions": sessions,
        "totalSeconds": total,
        "situations": sit,
        "loggedSessions": logged,
        "ac_2_1_01": total >= 600 and all(v >= 2 for v in sit.values()),
        "ac_2_1_02": logged >= 3,
    }


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="python -m workshop.recordings.index")
    p.add_argument("folder", type=Path)
    a = p.parse_args(argv)
    idx = build(a.folder)
    (a.folder / "index.json").write_bytes(json.dumps(idx, indent=1).encode("utf-8"))
    sit = " ".join(f"{k}={v}" for k, v in idx["situations"].items())
    ac1 = "PASS" if idx["ac_2_1_01"] else "FAIL"
    print(f"AC-2.1-01: {ac1} total={idx['totalSeconds']:.0f}s {sit}")
    print(f"AC-2.1-02: {'PASS' if idx['ac_2_1_02'] else 'FAIL'} logged={idx['loggedSessions']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
