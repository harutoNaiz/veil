import json
from pathlib import Path

from workshop.signals.scroll_ruler import main

FIX = Path(__file__).parent / "fixtures"


def _write(path: Path, rows: list[dict]) -> None:
    path.write_text("\n".join(json.dumps(r) for r in rows) + "\n", encoding="utf-8")


def _truth() -> list[dict]:
    rows: list[dict] = [{"type": "session", "tMs": 0}]
    for base, y0 in ((1000, 0), (3000, 100)):
        for i in range(6):
            rows.append({"type": "frame", "tMs": base + i * 16, "scrollY": y0 + i * 20})
    return rows


def _guard(sign: int) -> list[dict]:
    return [
        {"type": "scrolled", "tMs": base + i * 16, "packageName": "app", "dx": 0, "dy": -20 * sign}
        for base in (1000, 3000)
        for i in range(1, 6)
    ]


def test_pass_and_fail(capsys):
    FIX.mkdir(exist_ok=True)
    _write(FIX / "truth.jsonl", _truth())
    _write(FIX / "guard_ok.jsonl", _guard(1))
    _write(FIX / "guard_bad.jsonl", _guard(-1))
    truth = str(FIX / "truth.jsonl")
    assert main(["--guard", str(FIX / "guard_ok.jsonl"), "--truth", truth]) == 0
    assert "RULER: PASS" in capsys.readouterr().out
    assert main(["--guard", str(FIX / "guard_bad.jsonl"), "--truth", truth]) == 1
    assert "RULER: FAIL" in capsys.readouterr().out
