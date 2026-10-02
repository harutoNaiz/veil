"""Dataset access for the twin. The ONLY module that knows 1.2's folder layout.

Sets:
- "synthetic": 1.2's procedural set, generated on first use into data/synth/1.3
  (seed 7, split seed 12).
- "public":    real harmless photos composed into feed screenshots (workshop.twin.public_set).
- "real":      the team's labelled screenshots: data/screens, data/labels/{screens,splits}.json.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
DATA = REPO / "data"
CH1 = DATA / "ch1"
TEST_RUNS_LOG = CH1 / "test-runs.jsonl"
MAX_TEST_RUNS = 3
SYNTH_DIR = DATA / "synth" / "1.3"
SETS = ("synthetic", "public", "real")
SPLITS = ("dev", "test")
IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg"}


@dataclass(frozen=True)
class Screen:
    image: Path
    label: dict | None  # ScreenLabel dict, None for unlabelled folders


def _read_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def _folders(set_name: str) -> tuple[Path, Path, Path]:
    """(screens folder, labels file, splits file) of a set; creates synthetic/public on demand."""
    if set_name == "real":
        return DATA / "screens", DATA / "labels" / "screens.json", DATA / "labels" / "splits.json"
    if set_name == "synthetic":
        if not (SYNTH_DIR / "truth.json").is_file() or not (SYNTH_DIR / "splits.json").is_file():
            _make_synthetic()
        return SYNTH_DIR, SYNTH_DIR / "truth.json", SYNTH_DIR / "splits.json"
    if set_name == "public":
        from workshop.twin import public_set

        folder = public_set.ensure_set()
        return folder, folder / "truth.json", folder / "splits.json"
    raise ValueError(f"unknown set {set_name!r}; use one of {SETS}")


def _make_synthetic() -> None:
    from workshop.eval import split as split_mod
    from workshop.screens import synth

    labels = synth.generate(SYNTH_DIR, n=75, near_dupes=2, seed=7)
    splits = split_mod.split(labels, SYNTH_DIR, 12)
    (SYNTH_DIR / "splits.json").write_text(json.dumps(splits, indent=1) + "\n", encoding="utf-8")


def load_split(set_name: str, split: str) -> list[Screen]:
    """Screens of one split, sorted by file name, each with its ScreenLabel."""
    if split not in SPLITS:
        raise ValueError(f"split must be one of {SPLITS}, got {split!r}")
    screens_dir, labels_file, splits_file = _folders(set_name)
    if not labels_file.is_file() or not splits_file.is_file():
        raise FileNotFoundError(
            f"set {set_name!r} is not ready: need {labels_file} and {splits_file}"
        )
    by_name = {lab["image"]: lab for lab in _read_json(labels_file)}
    names = sorted(_read_json(splits_file)[split])
    return [Screen(screens_dir / name, by_name.get(name)) for name in names]


def load_folder(folder: Path) -> list[Screen]:
    """Every png/jpg in a folder, unlabelled (used for the fresh-screenshot proof test)."""
    paths = sorted(p for p in Path(folder).iterdir() if p.suffix.lower() in IMAGE_SUFFIXES)
    return [Screen(p, None) for p in paths]


def log_test_run(set_name: str, note: str, path: Path | None = None) -> int:
    """Append a test-split run to the log; refuse a 4th run of one set. Returns the run number."""
    log = Path(path) if path is not None else TEST_RUNS_LOG
    rows = []
    if log.is_file():
        rows = [json.loads(x) for x in log.read_text(encoding="utf-8").splitlines() if x.strip()]
    used = sum(1 for r in rows if r.get("set") == set_name)
    if used >= MAX_TEST_RUNS:
        raise RuntimeError(
            f"set {set_name!r} already has {used} test runs; the limit is {MAX_TEST_RUNS}"
        )
    entry = {
        "set": set_name,
        "n": used + 1,
        "utc": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "note": note,
    }
    log.parent.mkdir(parents=True, exist_ok=True)
    with log.open("a", encoding="utf-8") as fh:
        fh.write(json.dumps(entry) + "\n")
    return used + 1
