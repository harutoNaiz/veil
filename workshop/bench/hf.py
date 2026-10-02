"""Hugging Face checks. Veil's models are public, so an anonymous download is the real test."""

from __future__ import annotations

PROBE_REPO = "google/siglip2-base-patch16-224"
PROBE_FILE = "config.json"


def token_configured() -> bool:
    """True when a token is stored (`hf auth login`). The token itself is never printed."""
    import huggingface_hub

    return huggingface_hub.get_token() is not None


def anonymous_probe() -> str:
    """Download one small file of a public model without a token; returns its local path.

    The "unauthenticated requests" and "no symlinks" warnings are silenced: an anonymous download is
    exactly what this check wants, and Windows without Developer Mode cannot make symlinks.
    """
    import os
    import warnings

    os.environ.setdefault("HF_HUB_DISABLE_SYMLINKS_WARNING", "1")
    from huggingface_hub import hf_hub_download
    from huggingface_hub.utils import logging as hf_logging

    hf_logging.set_verbosity_error()
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        return hf_hub_download(PROBE_REPO, PROBE_FILE, token=False)
