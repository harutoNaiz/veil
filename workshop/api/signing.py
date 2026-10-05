"""Ed25519 signing for the Workshop catalogue. The dev key is created on first use."""

from __future__ import annotations

import base64
import json
from pathlib import Path

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PrivateKey,
    Ed25519PublicKey,
)

DEFAULT_KEY_DIR = Path(__file__).resolve().parent / "keys"
PRIV_NAME = "dev_ed25519_private.pem"
PUB_NAME = "dev_ed25519_public.b64"


def canonical(obj: object) -> bytes:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()


def load_or_create_key(key_dir: Path | str | None = None) -> Ed25519PrivateKey:
    d = Path(key_dir) if key_dir else DEFAULT_KEY_DIR
    d.mkdir(parents=True, exist_ok=True)
    priv_path = d / PRIV_NAME
    if priv_path.is_file():
        key = serialization.load_pem_private_key(priv_path.read_bytes(), password=None)
        assert isinstance(key, Ed25519PrivateKey)
    else:
        key = Ed25519PrivateKey.generate()
        priv_path.write_bytes(
            key.private_bytes(
                serialization.Encoding.PEM,
                serialization.PrivateFormat.PKCS8,
                serialization.NoEncryption(),
            )
        )
    (d / PUB_NAME).write_text(public_b64(key.public_key()), encoding="ascii")
    return key


def public_b64(pub: Ed25519PublicKey) -> str:
    raw = pub.public_bytes(serialization.Encoding.Raw, serialization.PublicFormat.Raw)
    return base64.b64encode(raw).decode("ascii")


def sign(key: Ed25519PrivateKey, payload: object) -> str:
    return base64.b64encode(key.sign(canonical(payload))).decode("ascii")


def verify(public_key_b64: str, payload: object, signature_b64: str) -> bool:
    try:
        pub = Ed25519PublicKey.from_public_bytes(base64.b64decode(public_key_b64))
        pub.verify(base64.b64decode(signature_b64), canonical(payload))
    except (InvalidSignature, ValueError, TypeError):
        return False
    return True
