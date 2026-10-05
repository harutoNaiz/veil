from workshop.forge.cloud import hub, placement, profile


def _raw(units):
    return {
        "execution_detail": [
            {"name": f"l{i}", "type": t, "compute_unit": u} for i, (t, u) in enumerate(units)
        ]
    }


def test_parse_counts_and_share():
    r = placement.parse(_raw([("Conv", "NPU")] * 3 + [("NonZero", "CPU"), ("Foo", "GPU")]))
    assert r["layers"] == {"npu": 3, "gpu": 1, "cpu": 1}
    assert r["npuShare"] == 0.6
    causes = {o["op"]: o["cause"] for o in r["offChip"]}
    assert causes == {"NonZero": "dynamic shape", "Foo": "unsupported op Foo"}


def test_parse_all_npu():
    assert placement.parse(_raw([("Conv", "NPU")] * 4))["npuShare"] == 1.0


def test_fixture_client_replays():
    c = hub.FixtureClient()
    assert c.compile("nudenet-320n", "float16", 1)["url"].startswith("fixture://")
    assert c.profile("nudenet-320n/float16")["execution_detail"]


def test_fixture_run_writes_profile(tmp_path):
    assert profile.main(["--fixture", "--out", str(tmp_path)]) == 0
    import json

    d = json.loads((tmp_path / "profile.json").read_text())
    assert d["source"] == "fixture" and d["device"] == hub.DEVICE
    assert {m["modelId"] for m in d["models"]} >= {"nudenet-320n", "siglip2-base-image-b4"}
    for m in d["models"]:
        assert {
            "compileJob",
            "profileJob",
            "quantizeJob",
            "latencyMs",
            "peakMemMb",
            "layers",
        } <= set(m)
        planted = m["modelId"] == "yoloe-26s-embed-top100" and m["precision"] == "float16"
        assert (m["npuShare"] < 1.0) == planted
        assert m["latencyMs"] > 0
        if planted:
            assert len(m["offChip"]) == 2
