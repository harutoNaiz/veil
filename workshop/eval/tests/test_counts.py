"""Count report on the fixture (75 images, exact numbers from its construction)."""

from __future__ import annotations

import json
from pathlib import Path

from workshop.eval import counts


def test_counts_exact(labels):
    got = {name: (value, need) for name, value, need in counts.counts(labels)}
    assert got["total"] == (75, 300)
    assert got["cats"][0] == 25 and got["spiders"][0] == 25 and got["clean"][0] == 25
    assert got["hard"][0] == 13  # every second clean image carries a dog
    assert got["apps"][0] == 5
    assert got["dark share"][0] == 25 / 75
    assert got["landscape"] == (5, None)


def test_counts_require_flags_low(tmp_path: Path, labels, capsys):
    lp = tmp_path / "l.json"
    lp.write_text(json.dumps(labels))
    assert counts.main(["--labels", str(lp)]) == 0
    assert counts.main(["--labels", str(lp), "--require"]) == 1
    assert "total: 75 (>= 300) LOW" in capsys.readouterr().out
