import json
from pathlib import Path

from workshop.forge.cloud import budget, manifests, report

HERE = Path(budget.__file__).parent


def _inputs():
    p = json.loads((HERE / "fixtures/3/profile.json").read_text())
    q = json.loads((HERE / "fixtures/3/precision.json").read_text())
    c = json.loads((HERE / "budget_config.json").read_text())
    return p, q, c


def test_compute_pass_and_fail():
    p, q, c = _inputs()
    r = budget.compute(p, q, c)
    assert r["pass"] and r["totalMs"] <= 45
    for m in p["models"]:
        if m["modelId"] == "siglip2-base-image-b4":
            m["latencyMs"] += 46 - r["totalMs"]
    r2 = budget.compute(p, q, c)
    assert r2["totalMs"] == 46 and not r2["pass"]


def test_validate_dir(tmp_path):
    assert manifests.main(["--fixture", "--out", str(tmp_path)]) == 0
    assert manifests.validate_dir(tmp_path) == []
    next(tmp_path.glob("files/*.bin")).write_bytes(b"x")
    assert any("checksum" in e for e in manifests.validate_dir(tmp_path))
    mf = tmp_path / "siglip2-base-image-b1.json"
    m = json.loads(mf.read_text())
    del m["fingerprint"]["pairedWith"]
    mf.write_text(json.dumps(m))
    assert any("pairedWith" in e for e in manifests.validate_dir(tmp_path))


def test_report_links(tmp_path):
    budget.main(["--fixture", "--out", str(tmp_path)])
    for n in ("profile.json", "precision.json"):
        (tmp_path / n).write_text((HERE / "fixtures/3" / n).read_text())
    md = report.render(tmp_path)
    assert "Source: fixture" in md
    checked = 0
    for ln in md.splitlines():
        if ln.startswith("| ") and any(
            f"| {m} |" in ln for m in ("nudenet-320n", "toxicity-seq128")
        ):
            assert "](fixture://" in ln, ln
            checked += 1
    assert checked >= 2
