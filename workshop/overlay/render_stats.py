"""Print p95 of (tDrawnMs - tRecvMs) against the vsync period from a render.jsonl."""

import json
import sys
from pathlib import Path


def p95(values: list[float]) -> float:
    s = sorted(values)
    return s[min(len(s) - 1, int(0.95 * len(s)))]


def main(path: str) -> int:
    rows = [json.loads(x) for x in Path(path).read_text().splitlines() if x.strip()]
    if not rows:
        print("no render rows")
        return 1
    lat = [r["tDrawnMs"] - r["tRecvMs"] for r in rows]
    vsync = rows[0]["vsyncPeriodMs"]
    ok = p95(lat) <= vsync
    print(f"n={len(rows)} p95={p95(lat):.1f}ms vsync={vsync:.1f}ms {'PASS' if ok else 'FAIL'}")
    return 0 if ok else 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1]))
