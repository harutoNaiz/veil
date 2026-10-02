from __future__ import annotations

import json
from pathlib import Path

import pytest
from PIL import Image

from workshop.bench import adb
from workshop.contracts.models import ScreenLabelMeta
from workshop.screens import capture


class FakePhone:
    """Stands in for adb: records swipes, writes PNGs of the given sizes one after another."""

    def __init__(self, monkeypatch: pytest.MonkeyPatch, sizes: list[tuple[int, int]]) -> None:
        self.sizes = sizes
        self.shots = 0
        self.swipes: list[tuple] = []
        monkeypatch.setattr(adb, "screencap", self.screencap)
        monkeypatch.setattr(adb, "screen_size", lambda serial: (1080, 2400))
        monkeypatch.setattr(adb, "swipe", lambda *args: self.swipes.append(args))
        monkeypatch.setattr(adb, "single_device", lambda: None)

    def screencap(self, serial: str, dest: Path) -> None:
        size = self.sizes[self.shots % len(self.sizes)]
        self.shots += 1
        Image.new("RGB", size, (9, 9, 9)).save(dest)


def _run(tmp_path: Path, **kw) -> list[Path]:
    args = dict(
        serial="S1", out=tmp_path, app="instagram", surface="explore", mode="dark",
        source="test-acct-A", count=3, scroll_fraction=0.6, pause_ms=0,
    )  # fmt: skip
    return capture.capture(**{**args, **kw})


def test_capture_writes_pngs_sidecars_and_scrolls(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    phone = FakePhone(monkeypatch, [(360, 780), (780, 360), (360, 780)])
    paths = _run(tmp_path)
    assert [p.name for p in paths] == [f"instagram-explore-000{i}.png" for i in (1, 2, 3)]
    sides = [json.loads(p.with_suffix(".json").read_text(encoding="utf-8")) for p in paths]
    assert [s["orientation"] for s in sides] == ["portrait", "landscape", "portrait"]
    for side in sides:
        ScreenLabelMeta(**{k: side[k] for k in ("app", "surface", "mode", "orientation", "source")})
        assert side["source"] == "test-acct-A" and side["capturedAt"].endswith("Z")
    assert len(phone.swipes) == 3
    assert (tmp_path / "sources.txt").read_text(encoding="utf-8").strip() == "test-acct-A"
    again = _run(tmp_path, count=1)  # numbering continues, never overwrites
    assert again[0].name == "instagram-explore-0004.png"


def test_capture_refuses_bad_input(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    phone = FakePhone(monkeypatch, [(360, 780)])
    for bad in ({"mode": "sepia"}, {"app": "Insta Gram"}, {"surface": "a/b"}, {"count": 0}):
        with pytest.raises(ValueError):
            _run(tmp_path, **bad)
    (tmp_path / "sources.txt").write_text("# allowed\ntest-acct-A\n", encoding="utf-8")
    with pytest.raises(ValueError, match="not listed"):
        _run(tmp_path, source="someone-else")
    assert phone.shots == 0 and not list(tmp_path.glob("*.png"))


def test_cli_no_device_exits_3(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture
) -> None:
    FakePhone(monkeypatch, [(360, 780)])  # single_device() -> None
    argv = ["--app", "x", "--surface", "feed", "--mode", "light", "--source", "t", "--out"]
    assert capture.main([*argv, str(tmp_path)]) == 3
    assert "no adb device" in capsys.readouterr().out
    assert not list(tmp_path.iterdir())
    assert (
        capture.main(["--app", "X", "--surface", "feed", "--mode", "light", "--source", "t"]) == 2
    )
