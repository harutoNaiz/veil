from pathlib import Path

from workshop.perf.smooth import gfx, kill, sample, section

FX = Path(__file__).parent / "fixtures"


def _txt(n):
    return (FX / n).read_text(encoding="utf-8")


def test_gfx_compare():
    on = gfx.parse_gfxinfo(_txt("gfxinfo_on.txt"))
    off = gfx.parse_gfxinfo(_txt("gfxinfo_off.txt"))
    assert on["total"] == 1800 and on["janky"] == 90
    assert abs(gfx.compare(on, off) - 0.5) < 1e-9


def test_parsers():
    assert sample.parse_meminfo_pss_kb(_txt("meminfo.txt")) == 1500000
    assert sample.parse_thermal_status(_txt("thermal.txt")) == 2


def test_throttle_cycle():
    assert sample.throttle_cycle(section._jl(FX / "stats.jsonl"))
    assert not sample.throttle_cycle([{"kind": "stats", "phase": "throttled"}])


def test_kill_judge():
    ok = [{"i": i, "recoveredMs": 900} for i in range(5)]
    assert kill.judge(ok)
    assert not kill.judge(ok[:4] + [{"i": 4, "recoveredMs": None}])


def _build(d):
    return section.build(
        section._gfx(d / "gfxinfo_on.txt"),
        section._gfx(d / "gfxinfo_off.txt"),
        d / "pss.csv",
        section._jl(d / "stats.jsonl"),
        section._jl(d / "kills.jsonl"),
    )


def test_section_pass_fail_pending():
    assert _build(FX).status == "PASS"
    assert _build(FX / "fail").status == "FAIL"
    assert section.build(None, None, None, None, None).status == "PENDING"
