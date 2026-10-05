"""Submit compile/quantize/profile per model x precision, collect NPU placement.

uv run python -m workshop.forge.cloud.profile [--live|--fixture] [--out DIR]
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from workshop.forge.cloud import hub, placement

CLOUD = Path(__file__).parent
FORGE = CLOUD.parent
ROOT = FORGE.parent.parent
DETECTORS = ("nudenet", "yoloe")
MODEL_DIRS = ("nudenet", "yoloe", "siglip2", "toxicity")
PRECISIONS = {"float16": None, "w8a16": ("int8", "int16"), "w8a8": ("int8", "int8")}


def manifests() -> list[dict]:
    out = []
    for d in MODEL_DIRS:
        for p in sorted((FORGE / d / "manifests").glob("*.json")):
            out.append(json.loads(p.read_text(encoding="utf-8")))
    return out


def precisions_for(model_id: str) -> list[str]:
    return list(PRECISIONS) if model_id.startswith(DETECTORS) else ["float16", "w8a16"]


def _num(raw: dict, key: str) -> float:
    return float(raw.get("execution_summary", {}).get(key, 0))


def run(live: bool, calib_dir: str = "data/public/set") -> dict:
    client = hub.get_client(live)
    rows = []
    for m in manifests():
        mid = m["modelId"]
        batch = int(m.get("batch", 1))
        model_path = str(ROOT / m["file"]["path"]) if live else mid
        for prec in precisions_for(mid):
            quant = None
            source = model_path
            if PRECISIONS[prec]:
                w, a = PRECISIONS[prec]
                quant = client.quantize(model_path, calib_dir, w, a)
                if live:
                    source = quant["jobId"]
            comp = client.compile(source, prec, batch)
            target = comp["jobId"] if live else f"{mid}/{prec}"
            prof = client.profile(target)
            raw = prof.get("profile", prof)
            rows.append(
                {
                    "modelId": mid,
                    "precision": prec,
                    "batch": batch,
                    "compileJob": comp.get("url", ""),
                    "profileJob": prof.get("url", ""),
                    "quantizeJob": quant.get("url") if quant else None,
                    "latencyMs": _num(raw, "estimated_inference_time") / 1000.0,
                    "peakMemMb": _num(raw, "estimated_inference_peak_memory") / 1e6,
                    **placement.parse(raw),
                }
            )
    return {"source": "live" if live else "fixture", "device": hub.DEVICE, "models": rows}


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="profile")
    g = ap.add_mutually_exclusive_group()
    g.add_argument("--live", action="store_true")
    g.add_argument("--fixture", action="store_true")
    ap.add_argument("--out", default=str(CLOUD / "out"))
    args = ap.parse_args(argv)
    result = run(args.live)
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    (out / "profile.json").write_text(json.dumps(result, indent=2) + "\n", encoding="utf-8")
    print(f"profile: {len(result['models'])} rows -> {out / 'profile.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
