from __future__ import annotations

import json
import subprocess
from pathlib import Path

from workshop.screens import meta_check, synth


def _set(tmp_path: Path) -> Path:
    synth.generate(tmp_path, n=6, near_dupes=1, seed=5)
    return tmp_path


def test_clean_synthetic_set_has_no_problems(tmp_path: Path) -> None:
    assert meta_check.check(_set(tmp_path), git=False) == []


def test_flags_missing_sidecar_and_unlisted_source(tmp_path: Path) -> None:
    screens = _set(tmp_path)
    first, second = sorted(p for p in screens.glob("*.png") if "-dup" not in p.name)[:2]
    first.with_suffix(".json").unlink()
    side = json.loads(second.with_suffix(".json").read_text(encoding="utf-8"))
    side["source"] = "personal-account"
    second.with_suffix(".json").write_text(json.dumps(side), encoding="utf-8")
    problems = meta_check.check(screens, git=False)
    assert any(first.name in p and "missing sidecar" in p for p in problems)
    assert any(
        second.name in p and "personal-account" in p and "sources.txt" in p for p in problems
    )


def test_flags_orientation_mismatch_and_orphan_sidecar(tmp_path: Path) -> None:
    screens = _set(tmp_path)
    png = screens / "youtube-feed-0002.png"  # a portrait image
    side = json.loads(png.with_suffix(".json").read_text(encoding="utf-8"))
    side["orientation"] = "landscape"
    png.with_suffix(".json").write_text(json.dumps(side), encoding="utf-8")
    (screens / "ghost-feed-0099.json").write_text("{}", encoding="utf-8")
    problems = meta_check.check(screens, git=False)
    assert any("orientation" in p for p in problems)
    assert any("ghost-feed-0099.json" in p and "without a PNG" in p for p in problems)


def test_flags_data_files_tracked_by_git(tmp_path: Path) -> None:
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    (tmp_path / "data").mkdir()
    (tmp_path / "data" / "README.md").write_text("ok", encoding="utf-8")
    (tmp_path / "data" / "shot.png").write_bytes(b"x")
    subprocess.run(["git", "add", "-f", "data"], cwd=tmp_path, check=True)
    assert meta_check.tracked_data_files(tmp_path) == ["data/shot.png"]
