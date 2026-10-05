"""6.3.2 tests."""

import json

from workshop.final import lint_report, report, sources

H = "| id | claim | value | status | conditions | source |\n| --- | --- | --- | --- | --- | --- |\n"


def _fixture(tmp_path):
    (tmp_path / "data/final").mkdir(parents=True)
    (tmp_path / "data/final/phone-metrics.json").write_text(
        json.dumps({"conditions": "test phone", "looksPerSecond": 4.5})
    )
    return tmp_path


def test_known_row_and_missing_pending(tmp_path):
    rows = {r[0]: r for r in sources.phone(_fixture(tmp_path))}
    assert rows["F-31"][2:4] == ("4.5", "measured")
    assert rows["F-01"][2:4] == (sources.DASH, "PENDING-HUMAN")


def test_missing_sources_all_pending(tmp_path):
    for _, loader in sources.AREAS:
        assert all(r[3] == "PENDING-HUMAN" for r in loader(tmp_path))


def test_generated_report_lints(tmp_path):
    root = _fixture(tmp_path)
    text = report.render(root, build="abc1234", date="2026-01-01")
    assert "| F-01 |" in text and "| F-02 |" in text and "## Limits" in text
    assert lint_report.lint(text, root) == []


def test_linter_failures(tmp_path):
    (tmp_path / "x.json").write_text("{}")
    bad_num = H + "| F-01 | a | 3 | PENDING-HUMAN | c | x.json |\n"
    bad_cond = H + "| F-01 | a | 3 | measured |  | x.json |\n"
    bad_src = H + "| F-01 | a | 3 | measured | c | nope.json |\n"
    dup = H + "| F-01 | a | - | PENDING-HUMAN | c | x |\n| F-01 | a | - | PENDING-HUMAN | c | x |\n"
    loose = H + "\nWe got 5 percent.\n"
    for t in (bad_num, bad_cond, bad_src, dup, loose):
        assert lint_report.lint(t, tmp_path), t
