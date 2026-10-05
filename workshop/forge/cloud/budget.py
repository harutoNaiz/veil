"""Latency budget for one look, per mode, from chosen-precision profile latencies."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

HERE = Path(__file__).parent
LIMIT_MS = 45.0


def _lookup(profile: dict, precision: dict, model_id: str) -> tuple[float, str | None]:
    chosen = next(
        (m["chosen"] for m in precision.get("models", []) if m["modelId"] == model_id), "float16"
    )
    rows = [m for m in profile.get("models", []) if m["modelId"] == model_id]
    row = next((m for m in rows if m["precision"] == chosen), rows[0] if rows else None)
    if row is None:
        raise KeyError(f"no profile for {model_id}")
    return float(row["latencyMs"]), row.get("profileJob")


def _mode(profile: dict, precision: dict, steps: list[dict], limit: float) -> dict:
    rows = []
    for s in steps:
        if "const" in s:
            rows.append({"step": s["step"], "ms": float(s["const"]), "job": None})
        else:
            ms, job = _lookup(profile, precision, s["modelId"])
            rows.append({"step": s["step"], "ms": ms, "job": job})
    total = round(sum(r["ms"] for r in rows), 3)
    return {"rows": rows, "totalMs": total, "limitMs": limit, "pass": total <= limit}


def compute(profile: dict, precision: dict, cfg: dict) -> dict:
    limit = float(cfg.get("limitMs", LIMIT_MS))
    modes = {n: _mode(profile, precision, s, limit) for n, s in cfg["modes"].items()}
    main = modes[cfg.get("mode", "Balanced")]
    return {
        "source": profile.get("source", "fixture"),
        "mode": cfg.get("mode", "Balanced"),
        "rows": main["rows"],
        "totalMs": main["totalMs"],
        "limitMs": limit,
        "pass": main["pass"],
        "modes": modes,
    }


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--live", action="store_true")
    ap.add_argument("--fixture", action="store_true")
    ap.add_argument("--out", default=str(HERE / "out"))
    a = ap.parse_args(argv)
    out = Path(a.out)
    src = out if a.live else HERE / "fixtures" / "3"
    profile = json.loads((src / "profile.json").read_text())
    precision = json.loads((src / "precision.json").read_text())
    cfg = json.loads((HERE / "budget_config.json").read_text())
    res = compute(profile, precision, cfg)
    out.mkdir(parents=True, exist_ok=True)
    (out / "budget.json").write_text(json.dumps(res, indent=1))
    print(f"budget {res['source']}: {res['totalMs']} ms pass={res['pass']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
