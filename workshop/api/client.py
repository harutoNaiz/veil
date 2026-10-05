"""Catalogue client: verifies the signature, sha256 and contract schema. Failure raises Rejected."""

from __future__ import annotations

import hashlib
import json
import urllib.request
from collections.abc import Callable
from pathlib import Path

from workshop.api import signing
from workshop.contracts.validate import validate

PINNED_PUBLIC_KEY_FILE = signing.DEFAULT_KEY_DIR / signing.PUB_NAME
HttpGet = Callable[[str], bytes]


class Rejected(Exception):
    """A catalogue, pack or model failed a check; nothing from it may be used."""


def _urlget(url: str) -> bytes:
    with urllib.request.urlopen(url, timeout=10) as r:
        return r.read()


def _pinned(public_key: str | None) -> str:
    if public_key:
        return public_key
    try:
        return Path(PINNED_PUBLIC_KEY_FILE).read_text(encoding="ascii").strip()
    except OSError:
        raise Rejected("no pinned public key") from None


def fetch_catalogue(
    base: str, *, public_key: str | None = None, http_get: HttpGet | None = None
) -> dict:
    """Both lists, each verified: ``{"packs": [...], "models": [...]}``."""
    get, pub = http_get or _urlget, _pinned(public_key)
    base = base.rstrip("/")
    out: dict = {}
    for part in ("packs", "models"):
        try:
            doc = json.loads(get(f"{base}/v1/{part}"))
            items, sig = doc[part], doc["signature"]
        except (ValueError, KeyError, TypeError, OSError) as e:
            raise Rejected(f"bad {part} catalogue") from e
        if not isinstance(sig, str) or not signing.verify(pub, items, sig):
            raise Rejected(f"bad signature on {part}")
        out[part] = items
    return out


def download(entry: dict, base: str = "", *, http_get: HttpGet | None = None) -> bytes:
    """Fetch an entry's bytes; check sha256, then the ConceptPack or ModelManifest schema."""
    get = http_get or _urlget
    try:
        data = get(base.rstrip("/") + entry["url"])
        want = entry["sha256"]
    except (KeyError, TypeError, OSError) as e:
        raise Rejected("download failed") from e
    if hashlib.sha256(data).hexdigest() != want:
        raise Rejected("sha256 mismatch")
    try:
        if "manifest" in entry:
            validate("ModelManifest", entry["manifest"])
        else:
            doc = json.loads(data)
            for pack in doc["packs"] if "packs" in doc else [doc]:
                validate("ConceptPack", pack)
    except Exception as e:
        raise Rejected("schema check failed") from e
    return data
