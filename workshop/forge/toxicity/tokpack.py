"""Pack Gemma BPE tokenizer.json files into VBPE binaries and build/check golden id sets."""

from __future__ import annotations

import argparse
import json
import os
import struct
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[3]
HF = "models--Horizon-Labs--multilingual-toxicity-small"
SPECS = {
    "toxicity": {"prepend": 1, "split": 1, "bos": 2, "eos": 1},
    "siglip2": {"prepend": 0, "split": 0, "bos": -1, "eos": 1},
}
GOLDEN_DIR = REPO / "guard/conductor/src/test/resources/tok"
STRINGS = [
    "The quick brown fox jumps over the lazy dog.",
    "Hello World, MiXeD CaSe TEXT",
    "Order 66 costs $12.50 (approx.), see #3: ok?!",
    "double  space inside",
    "  leading and trailing  ",
    "line one\nline two\tTabbed",
    "Café crème brûlée naïve façade",
    "नमस्ते दुनिया, आप कैसे हैं",
    "你好，世界。今天天气很好",
    "مرحبا بالعالم",
    "smile \U0001f600 party \U0001f389",
    "family \U0001f468‍\U0001f469‍\U0001f467 emoji",
    "https://example.com/path?q=1&r=two#frag",
    "a" * 400,
    "word " * 80,
    "",
    " ",
    "\n",
    "x",
    "I like cats",
    "<pad> and <eos> literal",
    "Numbers 1234567890 and 3.14159",
    "snake_case and kebab-case and CamelCase",
    "Olá, como vai você?",
    "Привет, мир!",
    "á combining mark and  nbsp",
]


def tok_json(name: str) -> Path:
    if name == "siglip2":
        return REPO / "data/forge/siglip2/tokenizer.json"
    hf = Path(os.environ["HF_HOME"])
    snaps = (hf / "hub" / HF / "snapshots", hf / HF / "snapshots")
    for s in snaps:
        if s.is_dir():
            for d in sorted(s.iterdir()):
                if (d / "tokenizer.json").is_file():
                    return d / "tokenizer.json"
    raise SystemExit(f"toxicity tokenizer.json not found under {hf}")


def out_bin(name: str) -> Path:
    base = "data/forge/toxicity" if name == "toxicity" else "data/forge/siglip2"
    return REPO / base / f"{name}-tok.bin"


def u16s(s: str) -> bytes:
    b = s.encode("utf-8")
    return struct.pack(">H", len(b)) + b


def pack(name: str) -> None:
    spec = SPECS[name]
    d = json.loads(tok_json(name).read_text(encoding="utf-8"))
    m = d["model"]
    assert m["type"] == "BPE" and m.get("byte_fallback") and m.get("fuse_unk")
    assert not m.get("ignore_merges")
    vocab = m["vocab"]
    n = len(vocab)
    by_id = [""] * n
    for tok, i in vocab.items():
        by_id[i] = tok
    assert all(by_id) or n == len(set(vocab.values())), "ids not dense"
    assert sorted(vocab.values()) == list(range(n)), "ids not dense"
    unk = vocab[m["unk_token"]]
    pad = vocab["<pad>"]
    pre = d.get("pre_tokenizer") or {}
    if name == "toxicity":
        assert pre.get("type") == "Metaspace", pre
        assert pre.get("prepend_scheme") == "always" and pre.get("split") is True
    else:
        assert pre.get("type") == "Split" and pre["pattern"] == {"String": " "}
    tmpl = [next(iter(x)) for x in d["post_processor"]["single"]]
    assert tmpl == (
        ["SpecialToken", "Sequence", "SpecialToken"]
        if spec["bos"] >= 0
        else ["Sequence", "SpecialToken"]
    ), tmpl
    merges = []
    for mg in m["merges"]:
        a, b = mg if isinstance(mg, list) else mg.split(" ")
        merges.append((vocab[a], vocab[b], vocab[a + b]))
    added, dropped = [], 0
    for t in d["added_tokens"]:
        if t.get("lstrip") or t.get("rstrip") or t.get("single_word"):
            dropped += 1
            continue
        added.append((t["id"], t["content"]))
    buf = bytearray(b"VBPE" + struct.pack(">i", 1))
    buf += struct.pack(">6i", spec["prepend"], spec["split"], spec["bos"], spec["eos"], unk, pad)
    buf += struct.pack(">i", n)
    for s in by_id:
        buf += u16s(s)
    buf += struct.pack(">i", len(merges))
    for t3 in merges:
        buf += struct.pack(">3i", *t3)
    buf += struct.pack(">i", len(added))
    for i, c in added:
        buf += struct.pack(">i", i) + u16s(c)
    out = out_bin(name)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_bytes(bytes(buf))
    print(f"{name}: vocab={n} merges={len(merges)} added={len(added)} dropped={dropped}")


def encode_all(name: str) -> list[list[int]]:
    from tokenizers import Tokenizer

    tk = Tokenizer.from_file(str(tok_json(name)))
    return [tk.encode(s).ids for s in STRINGS]


def main() -> int:
    ap = argparse.ArgumentParser()
    g = ap.add_mutually_exclusive_group()
    g.add_argument("--golden", action="store_true")
    g.add_argument("--check-golden", action="store_true")
    a = ap.parse_args()
    for name in SPECS:
        pack(name)
        gp = GOLDEN_DIR / f"golden-{name}.json"
        if a.golden:
            GOLDEN_DIR.mkdir(parents=True, exist_ok=True)
            doc = {"strings": STRINGS, "ids": encode_all(name)}
            gp.write_text(json.dumps(doc, ensure_ascii=True), encoding="utf-8")
            print(f"wrote {gp.name}")
        elif a.check_golden:
            doc = json.loads(gp.read_text(encoding="utf-8"))
            if doc["strings"] != STRINGS or doc["ids"] != encode_all(name):
                print(f"golden MISMATCH for {name}")
                return 1
            print(f"golden ok: {name}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
