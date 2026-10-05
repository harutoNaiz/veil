"""Final v1 manifests (onnxruntime-qnn) and their validator."""

from __future__ import annotations

import argparse
import copy
import json
from pathlib import Path

from workshop.contracts.validate import validate
from workshop.forge.common import sha256_file

HERE = Path(__file__).parent
FORGE = HERE.parent
REPO = FORGE.parent.parent


def build(base_manifest: dict, chosen: str, file_path: Path, rel_path: str | None = None) -> dict:
    m = copy.deepcopy(base_manifest)
    m["precision"] = chosen
    m["runtime"] = "onnxruntime-qnn"
    m["file"] = {
        "path": rel_path or str(file_path).replace("\\", "/"),
        "sha256": sha256_file(file_path),
        "bytes": file_path.stat().st_size,
    }
    return m


def validate_dir(d: Path) -> list[str]:
    d = Path(d)
    errs: list[str] = []
    files = sorted(d.glob("*.json"))
    if not files:
        errs.append(f"{d}: no manifests")
    for f in files:
        m = json.loads(f.read_text())
        try:
            validate("ModelManifest", m)
        except Exception as e:  # jsonschema.ValidationError
            errs.append(f"{f.name}: schema: {getattr(e, 'message', e)}")
        rel = m.get("file", {}).get("path", "")
        p = next((c for c in (d / rel, REPO / rel) if c.is_file()), None)
        if p is None:
            errs.append(f"{f.name}: file missing: {rel}")
        elif sha256_file(p) != m["file"]["sha256"] or p.stat().st_size != m["file"]["bytes"]:
            errs.append(f"{f.name}: checksum mismatch")
        fp = m.get("fingerprint")
        if fp is not None:
            for k in ("spaceId", "pairedWith"):
                if not fp.get(k):
                    errs.append(f"{f.name}: fingerprint missing {k}")
    return errs


def _bases() -> list[dict]:
    return [json.loads(p.read_text()) for p in sorted(FORGE.glob("*/manifests/*.json"))]


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--live", action="store_true")
    ap.add_argument("--fixture", action="store_true")
    ap.add_argument("--out")
    ap.add_argument("--check")
    a = ap.parse_args(argv)
    if a.check:
        errs = validate_dir(Path(a.check))
        for e in errs:
            print(e)
        print("manifests check:", "FAIL" if errs else "ok")
        return 1 if errs else 0
    src = HERE / ("out" if a.live else "fixtures/3") / "precision.json"
    chosen = {m["modelId"]: m["chosen"] for m in json.loads(src.read_text())["models"]}
    if a.live:
        out = FORGE / "manifests"
        files_dir = REPO / "data" / "forge" / "cloud"
    else:
        out = Path(a.out or HERE / "out" / "manifests_fixture")
        files_dir = out / "files"
    out.mkdir(parents=True, exist_ok=True)
    files_dir.mkdir(parents=True, exist_ok=True)
    for base in _bases():
        mid = base["modelId"]
        f = files_dir / f"{mid}.bin"
        if not a.live:
            f.write_bytes((mid.encode() * 1024)[:1024])
        rel = f"data/forge/cloud/{mid}.bin" if a.live else f"files/{mid}.bin"
        m = build(base, chosen.get(mid, "float16"), f, rel)
        (out / f"{mid}.json").write_text(json.dumps(m, indent=2))
    print(f"manifests written to {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
