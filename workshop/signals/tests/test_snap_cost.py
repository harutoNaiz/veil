from pathlib import Path

from workshop.signals import snap_cost

FX = Path(__file__).parent / "fixtures"


def test_parse_and_report() -> None:
    rows = snap_cost.parse((FX / "snap.log").read_text().splitlines())
    assert rows == [(12, 80, False), (20, 120, False), (41, 300, True)]
    text, ok = snap_cost.report(rows)
    assert "maxNodes=300" in text
    assert not ok  # p95 = 41 > 40


def test_pass() -> None:
    _, ok = snap_cost.report([(10, 50, False)] * 20)
    assert ok


def test_empty() -> None:
    assert not snap_cost.report([])[1]
