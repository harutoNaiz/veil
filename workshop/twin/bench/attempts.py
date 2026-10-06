"""Attempts log for TEST runs (at most 5). Dev runs are never logged."""

from __future__ import annotations

import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path

HERE = Path(__file__).resolve().parent
LOG = HERE / "attempts.jsonl"
MAX_ATTEMPTS = 5


class Exhausted(Exception):
    """More than five test attempts."""


class DryRefused(Exception):
    """--dry is only for non-v1 benches."""


def read(path: Path | None = None) -> list[dict]:
    p = Path(path) if path else LOG
    if not p.exists():
        return []
    return [json.loads(ln) for ln in p.read_text(encoding="utf-8").splitlines() if ln.strip()]


def params_sha(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def check_dry(bench_name: str, dry: bool) -> None:
    if dry and bench_name == "v1":
        raise DryRefused("--dry is refused on the v1 bench")


def start(
    manifest_sha: str, bank_id: str, params_sha256: str, note: str, path: Path | None = None
) -> int:
    """Append the attempt line BEFORE scoring; returns n. Raises Exhausted when n > 5."""
    path = Path(path) if path else LOG
    n = sum(1 for r in read(path) if "at" in r) + 1
    if n > MAX_ATTEMPTS:
        raise Exhausted("ATTEMPTS EXHAUSTED")
    row = {
        "n": n,
        "at": datetime.now(UTC).isoformat(timespec="seconds"),
        "manifestSha256": manifest_sha,
        "bankId": bank_id,
        "paramsSha256": params_sha256,
        "note": note,
    }
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(row, sort_keys=True) + "\n")
    return n


def finish(n: int, gate_share: float, passing: int, path: Path | None = None) -> None:
    path = Path(path) if path else LOG
    with open(path, "a", encoding="utf-8") as f:
        row = {"n": n, "gateShare": gate_share, "passing": passing}
        f.write(json.dumps(row, sort_keys=True) + "\n")
