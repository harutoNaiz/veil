from pathlib import Path

from workshop.signals import frame_stats

FX = Path(__file__).parent / "fixtures"


def test_parse_janky() -> None:
    assert frame_stats.parse_janky((FX / "gfxinfo.txt").read_text()) == 5.0
    assert frame_stats.parse_janky("nothing") is None
