"""Veil Workshop server. Serves signed model and pack catalogues; opt-in routes are privacy-locked.

Errors are ``{"error": "<code>"}`` and never echo input. The request log holds method, path,
status and milliseconds only. No cookies are set; no IP or identifier header is read.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import logging
import time
from pathlib import Path
from typing import Any

from flask import Flask, Response, g, jsonify, request
from pydantic import BaseModel, ValidationError

from workshop.api import schemas, signing

HERE = Path(__file__).resolve().parent
log = logging.getLogger("veil.api")
SENSITIVE_BUNDLE = "sensitive-bundle"
MAX_BODY = 16 * 1024


class ApiError(Exception):
    def __init__(self, status: int, code: str) -> None:
        super().__init__(code)
        self.status, self.code = status, code


def _err(status: int, code: str) -> Response:
    resp = jsonify({"error": code})
    resp.status_code = status
    return resp


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _default_encoder() -> Any:
    from workshop.twin.describer import Describer

    return Describer()


def create_app(config: dict | None = None) -> Flask:
    cfg = {
        "PACK_DIR": HERE.parent / "packs",
        "MODEL_DIR": HERE.parent / "models",
        "KEY_DIR": signing.DEFAULT_KEY_DIR,
        "DEV_TOKEN": None,
        "ENCODER": None,
        **(config or {}),
    }
    pack_dir, model_dir = Path(cfg["PACK_DIR"]), Path(cfg["MODEL_DIR"])
    key = signing.load_or_create_key(cfg["KEY_DIR"])
    app = Flask(__name__)
    app.config["MAX_CONTENT_LENGTH"] = MAX_BODY
    state: dict[str, Any] = {"enc": cfg["ENCODER"]}

    def packs() -> dict[str, tuple[dict, bytes]]:
        out: dict[str, tuple[dict, bytes]] = {}
        for p in sorted(pack_dir.glob("*.json")):
            raw = p.read_bytes()
            doc = json.loads(raw)
            out[doc["packId"]] = (doc, raw)
        return out

    def bundle_bytes() -> bytes:
        items = [d for d, _ in packs().values() if d.get("sensitive")]
        return signing.canonical({"packs": items})

    def models() -> dict[str, tuple[dict, Path]]:
        out: dict[str, tuple[dict, Path]] = {}
        for m in sorted(model_dir.glob("*.manifest.json")):
            doc = json.loads(m.read_text(encoding="utf-8"))
            stem = m.name.removesuffix(".manifest.json")
            files = [f for f in model_dir.glob(stem + ".*") if f != m]
            if files:
                out[doc["modelId"]] = (doc, files[0])
        return out

    def parse(model: type[BaseModel], consent: bool = True) -> Any:
        """The only place a request body is read."""
        raw = request.get_data(cache=False)
        try:
            body = json.loads(raw)
        except ValueError:
            raise ApiError(400, "bad_json") from None
        if not isinstance(body, dict):
            raise ApiError(400, "bad_json")
        if consent and body.get("consent") is not True:
            raise ApiError(403, "consent_required")
        try:
            return model.model_validate(body)
        except ValidationError as e:
            kinds = {x["type"] for x in e.errors()}
            code = "unknown_field" if "extra_forbidden" in kinds else "invalid"
            raise ApiError(422, code) from None

    @app.before_request
    def _start() -> None:
        g.t0 = time.perf_counter()

    @app.after_request
    def _log(resp: Response) -> Response:
        ms = int((time.perf_counter() - g.get("t0", time.perf_counter())) * 1000)
        log.info("%s %s %d %dms", request.method, request.path, resp.status_code, ms)
        resp.headers.pop("Set-Cookie", None)
        return resp

    @app.errorhandler(ApiError)
    def _api_error(e: ApiError) -> Response:
        return _err(e.status, e.code)

    @app.errorhandler(404)
    def _404(_e: Exception) -> Response:
        return _err(404, "not_found")

    @app.errorhandler(405)
    def _405(_e: Exception) -> Response:
        return _err(405, "method_not_allowed")

    @app.errorhandler(413)
    def _413(_e: Exception) -> Response:
        return _err(413, "too_large")

    @app.errorhandler(Exception)
    def _500(_e: Exception) -> Response:
        return _err(500, "server_error")

    @app.get("/v1/models")
    def list_models() -> Response:
        items = []
        for mid, (manifest, path) in models().items():
            data = path.read_bytes()
            items.append(
                {
                    "manifest": manifest,
                    "url": f"/v1/models/{mid}/file",
                    "sha256": _sha(data),
                    "size": len(data),
                }
            )
        return jsonify({"models": items, "signature": signing.sign(key, items)})

    @app.get("/v1/models/<model_id>/file")
    def model_file(model_id: str) -> Response:
        found = models().get(model_id)
        if not found:
            raise ApiError(404, "not_found")
        return Response(found[1].read_bytes(), mimetype="application/octet-stream")

    @app.get("/v1/packs")
    def list_packs() -> Response:
        items: list[dict] = []
        for pid, (doc, raw) in packs().items():
            if doc.get("sensitive"):
                continue
            items.append(
                {
                    "packId": pid,
                    "name": doc["name"],
                    "version": doc["version"],
                    "sensitive": False,
                    "sha256": _sha(raw),
                    "url": f"/v1/packs/{pid}",
                    "accuracy": doc.get("accuracy"),
                }
            )
        items.append(
            {
                "packId": SENSITIVE_BUNDLE,
                "sensitive": True,
                "sha256": _sha(bundle_bytes()),
                "url": f"/v1/packs/{SENSITIVE_BUNDLE}",
            }
        )
        return jsonify({"packs": items, "signature": signing.sign(key, items)})

    @app.get("/v1/packs/<pack_id>")
    def get_pack(pack_id: str) -> Response:
        if pack_id == SENSITIVE_BUNDLE:
            return Response(bundle_bytes(), mimetype="application/json")
        found = packs().get(pack_id)
        if not found or found[0].get("sensitive"):
            raise ApiError(404, "not_found")
        return Response(found[1], mimetype="application/json")

    @app.post("/v1/compile")
    def compile_words() -> Response:
        from workshop.twin.teacher import compile_concept, concept_card

        req = parse(schemas.CompileRequest)
        if state["enc"] is None:
            state["enc"] = _default_encoder()
        out = []
        for word in req.words:
            try:
                card = concept_card(word)
            except ValueError:
                raise ApiError(422, "invalid") from None
            out.append(compile_concept(card, state["enc"]))
        return jsonify({"concepts": out})

    @app.post("/v1/metrics")
    def metrics() -> Response:
        parse(schemas.MetricsRequest)  # validated, then dropped: nothing is stored
        return Response(status=204)

    @app.post("/v1/dev/eval")
    def dev_eval() -> Response:
        token = request.headers.get("X-Dev-Token", "")
        want = cfg["DEV_TOKEN"]
        if not want or not hmac.compare_digest(token.encode(), str(want).encode()):
            raise ApiError(403, "forbidden")
        req = parse(schemas.EvalRequest, consent=False)
        if req.packId not in packs():
            raise ApiError(404, "not_found")
        report = pack_dir / "reports" / f"{req.packId}.json"
        if not report.is_file():
            raise ApiError(404, "not_found")
        return Response(report.read_bytes(), mimetype="application/json")

    return app
