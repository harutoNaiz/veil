from pathlib import Path

from workshop.demo import trace_claims as t

FIX = Path(__file__).parent / "fixture_final.md"
STEPS = "".join(f"## Step {i}\nSay it.\n" for i in range(1, 8)) + "Then airplane mode.\n"
QA = "\n".join(t.APPENDIX_C) + "\n"


def make(tmp_path, script=STEPS, qa=QA, pitch="Covers in 250 ms [F-01].\n"):
    (tmp_path / "demo-script.md").write_text(script, encoding="utf-8")
    (tmp_path / "qa-sheet.md").write_text(qa, encoding="utf-8")
    (tmp_path / "pitch-outline.md").write_text(pitch, encoding="utf-8")
    return ["--docs", str(tmp_path), "--report", str(FIX), "--appendix-c"]


def test_good(tmp_path):
    assert t.main(make(tmp_path)) == 0


def test_uncited_number(tmp_path):
    assert t.main(make(tmp_path, pitch="Covers in 250 ms.\n")) == 1


def test_unknown_id(tmp_path):
    assert t.main(make(tmp_path, pitch="Covers in 250 ms [F-09].\n")) == 1


def test_missing_part(tmp_path):
    assert t.main(make(tmp_path, qa=QA.replace("NudeNet", ""))) == 1


def test_script_needs_seven_steps(tmp_path):
    assert t.main(make(tmp_path, script="## Step 1\nairplane mode\n")) == 1
