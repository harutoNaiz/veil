from __future__ import annotations

import json
import logging
import shutil
from pathlib import Path

import numpy as np
import pytest

from workshop.api import client, signing
from workshop.api.app import create_app
from workshop.contracts.validate import validate

FIX = Path(__file__).parent / "fixtures"
BASE = "http://t"
TOKEN = "dev-secret"


class HashEncoder:
    space_id = "fake-space"
    text_model_id = "fake-text"

    def embed_texts(self, texts: list[str]) -> np.ndarray:
        out = []
        for t in texts:
            rng = np.random.default_rng(abs(hash(t)) % (2**32))
            v = rng.normal(size=8).astype(np.float32)
            out.append(v / np.linalg.norm(v))
        return np.stack(out)


@pytest.fixture
def dirs(tmp_path):
    shutil.copytree(FIX / "packs", tmp_path / "packs")
    shutil.copytree(FIX / "models", tmp_path / "models")
    return tmp_path


@pytest.fixture
def app(dirs):
    return create_app(
        {
            "PACK_DIR": dirs / "packs",
            "MODEL_DIR": dirs / "models",
            "KEY_DIR": dirs / "keys",
            "DEV_TOKEN": TOKEN,
            "ENCODER": HashEncoder(),
        }
    )


@pytest.fixture
def http(app):
    c = app.test_client()
    return lambda url: c.get(url.removeprefix(BASE)).data


@pytest.fixture
def pub(dirs, app):
    return (dirs / "keys" / signing.PUB_NAME).read_text()


def test_packs_catalogue_shape(app):
    d = app.test_client().get("/v1/packs").get_json()
    ids = [p["packId"] for p in d["packs"]]
    assert ids == ["spiders", "sensitive-bundle"]
    assert d["packs"][0]["sensitive"] is False and d["packs"][0]["accuracy"]["recall"]
    assert d["packs"][-1]["sensitive"] is True and "name" not in d["packs"][-1]
    assert d["signature"]


def test_sensitive_not_individually_served(app):
    c = app.test_client()
    assert c.get("/v1/packs/series-spoilers").status_code == 404
    assert c.get("/v1/packs/spiders").status_code == 200
    bundle = c.get("/v1/packs/sensitive-bundle").get_json()
    assert [p["packId"] for p in bundle["packs"]] == ["series-spoilers"]


def test_models_catalogue_and_file(app):
    c = app.test_client()
    d = c.get("/v1/models").get_json()
    m = d["models"][0]
    assert m["manifest"]["modelId"] == "nudenet-320n" and m["size"] > 0
    assert c.get(m["url"]).data == b"fake-model-bytes\n"
    assert c.get("/v1/models/nope/file").status_code == 404


def test_compile(app):
    r = app.test_client().post("/v1/compile", json={"consent": True, "words": ["cats", "dog"]})
    assert r.status_code == 200
    cs = r.get_json()["concepts"]
    assert [c["conceptId"] for c in cs] == ["cats", "dog"]
    for c in cs:
        validate("CompiledConcept", c)


@pytest.mark.parametrize("words", [[], ["a"] * 9, ["x" * 65], [1], "cats"])
def test_compile_bounds(app, words):
    r = app.test_client().post("/v1/compile", json={"consent": True, "words": words})
    assert r.status_code == 422 and r.get_json() == {"error": "invalid"}


def test_metrics_ok_and_bad(app):
    c = app.test_client()
    ok = {"consent": True, "day": "2026-10-05", "counts": {"covers": "10-99", "peeks": "0"}}
    assert c.post("/v1/metrics", json=ok).status_code == 204
    for bad in (
        {**ok, "day": "2026-13-45"},
        {**ok, "counts": {"covers": "12"}},
        {**ok, "counts": {"covers": 12}},
        {**ok, "consent": "true"},
    ):
        assert c.post("/v1/metrics", json=bad).status_code in (403, 422)


def test_unknown_field_rejected_without_echo(app, caplog):
    caplog.set_level(logging.DEBUG)
    c = app.test_client()
    body = {"consent": True, "day": "2026-10-05", "counts": {}, "screenText": "SECRET-123"}
    r = c.post("/v1/metrics", json=body)
    assert r.status_code == 422 and r.get_json() == {"error": "unknown_field"}
    assert "SECRET-123" not in r.get_data(as_text=True) and "screenText" not in r.get_data(
        as_text=True
    )
    nested = {"consent": True, "day": "2026-10-05", "counts": {"SECRET-123": "1-9"}}
    r2 = c.post("/v1/metrics", json=nested)
    assert r2.status_code == 422 and "SECRET-123" not in r2.get_data(as_text=True)
    r3 = c.post("/v1/compile", json={"consent": True, "words": ["a"], "SECRET-123": 1})
    assert r3.status_code == 422 and r3.get_json() == {"error": "unknown_field"}
    assert "SECRET-123" not in caplog.text and "screenText" not in caplog.text
    assert caplog.text  # request lines were logged


def test_consent_required(app, caplog):
    caplog.set_level(logging.DEBUG)
    c = app.test_client()
    for url, body in (
        ("/v1/metrics", {"day": "2026-10-05", "counts": {}, "n": "SECRET-123"}),
        ("/v1/metrics", {"consent": False, "day": "2026-10-05", "counts": {}}),
        ("/v1/compile", {"words": ["SECRET-123"]}),
    ):
        r = c.post(url, json=body)
        assert r.status_code == 403 and r.get_json() == {"error": "consent_required"}
    assert "SECRET-123" not in caplog.text


def test_bad_json_not_echoed(app, caplog):
    caplog.set_level(logging.DEBUG)
    r = app.test_client().post("/v1/metrics", data=b"SECRET-123{", content_type="application/json")
    assert r.status_code == 400 and "SECRET-123" not in r.get_data(as_text=True)
    assert "SECRET-123" not in caplog.text


def test_log_has_only_method_path_status_ms(app, caplog):
    caplog.set_level(logging.DEBUG)
    app.test_client().post(
        "/v1/metrics",
        json={"consent": True, "day": "2026-10-05", "counts": {}},
        headers={"X-Forwarded-For": "9.9.9.9", "Cookie": "id=SECRET-123"},
    )
    recs = [r.getMessage() for r in caplog.records if r.name == "veil.api"]
    assert len(recs) == 1 and recs[0].startswith("POST /v1/metrics 204 ")
    assert "9.9.9.9" not in caplog.text and "SECRET-123" not in caplog.text


def test_no_cookies_or_ip_headers(app):
    r = app.test_client().get("/v1/packs", headers={"Cookie": "a=b"})
    assert "Set-Cookie" not in r.headers
    src = (Path(__file__).parents[1] / "app.py").read_text()
    for banned in ("remote_addr", "X-Forwarded", "access_route", "session"):
        assert banned not in src


def test_dev_eval(app):
    c = app.test_client()
    assert c.post("/v1/dev/eval", json={"packId": "spiders"}).status_code == 403
    bad = c.post("/v1/dev/eval", json={"packId": "spiders"}, headers={"X-Dev-Token": "x"})
    assert bad.status_code == 403
    ok = c.post("/v1/dev/eval", json={"packId": "spiders"}, headers={"X-Dev-Token": TOKEN})
    assert ok.get_json()["status"] == "PASS"
    miss = c.post("/v1/dev/eval", json={"packId": "zzz"}, headers={"X-Dev-Token": TOKEN})
    assert miss.status_code == 404


def test_client_accepts_good_pack_and_model(app, http, pub):
    cat = client.fetch_catalogue(BASE, public_key=pub, http_get=http)
    pack = next(p for p in cat["packs"] if p["packId"] == "spiders")
    assert json.loads(client.download(pack, BASE, http_get=http))["packId"] == "spiders"
    bundle = next(p for p in cat["packs"] if p["packId"] == "sensitive-bundle")
    assert client.download(bundle, BASE, http_get=http)
    model = cat["models"][0]
    assert client.download(model, BASE, http_get=http) == b"fake-model-bytes\n"


def test_client_rejects_tampered_pack_byte(app, http, pub):
    pack = client.fetch_catalogue(BASE, public_key=pub, http_get=http)["packs"][0]

    def evil(url):
        data = bytearray(http(url))
        data[-3] ^= 0x01
        return bytes(data)

    with pytest.raises(client.Rejected):
        client.download(pack, BASE, http_get=evil)


def test_client_rejects_tampered_sha_in_catalogue(app, http, pub):
    def evil(url):
        d = json.loads(http(url))
        if url.endswith("/v1/packs"):
            d["packs"][0]["sha256"] = "0" * 64
        return json.dumps(d).encode()

    with pytest.raises(client.Rejected):
        client.fetch_catalogue(BASE, public_key=pub, http_get=evil)


def test_client_rejects_bad_signature_and_wrong_key(app, http, pub, tmp_path):
    def evil(url):
        d = json.loads(http(url))
        d["signature"] = "A" * 86 + "=="
        return json.dumps(d).encode()

    with pytest.raises(client.Rejected):
        client.fetch_catalogue(BASE, public_key=pub, http_get=evil)
    other = signing.public_b64(signing.load_or_create_key(tmp_path / "other").public_key())
    with pytest.raises(client.Rejected):
        client.fetch_catalogue(BASE, public_key=other, http_get=http)


def test_client_rejects_schema_invalid_pack(dirs, app, http, pub):
    entry = client.fetch_catalogue(BASE, public_key=pub, http_get=http)["packs"][0]
    bad = json.dumps({"packId": "spiders"}).encode()
    import hashlib

    entry = {**entry, "sha256": hashlib.sha256(bad).hexdigest()}
    with pytest.raises(client.Rejected):
        client.download(entry, BASE, http_get=lambda _u: bad)
