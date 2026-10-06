"""Reference-bank file formats (VBNK / VVOC), little-endian. See SPEC 7.1 section 2."""

from __future__ import annotations

import hashlib
import json
import struct
from dataclasses import dataclass
from pathlib import Path

import numpy as np


@dataclass
class Bank:
    rows: np.ndarray  # float64 unit (n, dim), dequantised
    lab_off: np.ndarray
    lab_idx: np.ndarray
    bank_id: str


@dataclass
class Vocab:
    rows: np.ndarray  # float64 unit (n, dim)
    thr: np.ndarray  # float32 (n, 3)
    meta: dict
    center: np.ndarray | None = None  # mean of the noun rows (float64), set by read_vocab


def noun_center(rows: np.ndarray, meta: dict) -> np.ndarray:
    ix = [i for i, e in enumerate(meta.get("entries", [])) if e["kind"] == "noun"]
    if not ix:
        return rows.mean(0)
    return rows[ix].mean(0)


def direction(e: np.ndarray, center: np.ndarray) -> np.ndarray:
    v = np.asarray(e, dtype=np.float64) - center
    return v / np.maximum(np.linalg.norm(v, axis=-1, keepdims=True), 1e-12)


def quantise(v: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    v = np.asarray(v, dtype=np.float32)
    scale = (np.abs(v).max(axis=1) / 127.0).astype("<f4")
    safe = np.where(scale == 0, 1.0, scale).astype(np.float32)
    q = np.clip(np.rint(v / safe[:, None]), -127, 127).astype(np.int8)
    return q, scale


def dequant(q: np.ndarray, scale: np.ndarray) -> np.ndarray:
    rows = q.astype(np.float64) * scale.astype(np.float64)[:, None]
    return rows / np.maximum(np.linalg.norm(rows, axis=1, keepdims=True), 1e-300)


def write_bank(path: Path, vecs: np.ndarray, labels: list[list[int]]) -> str:
    q, scale = quantise(vecs)
    n, dim = q.shape
    off = np.zeros(n + 1, dtype="<u4")
    for i, lab in enumerate(labels):
        off[i + 1] = off[i] + len(lab)
    idx = np.array([x for lab in labels for x in lab], dtype="<u2")
    blob = (
        b"VBNK"
        + struct.pack("<IIII", 1, n, dim, len(idx))
        + scale.astype("<f4").tobytes()
        + q.tobytes()
        + off.tobytes()
        + idx.tobytes()
    )
    Path(path).write_bytes(blob)
    return hashlib.sha256(blob).hexdigest()[:16]


def relabel_bank(path: Path, labels: list[list[int]]) -> str:
    """Rewrite only the label sections of a bank.bin (rows stay byte-identical)."""
    blob = Path(path).read_bytes()
    ver, n, dim, _ = struct.unpack_from("<IIII", blob, 4)
    head = blob[: 20 + 4 * n + n * dim]
    off = np.zeros(n + 1, dtype="<u4")
    for i, lab in enumerate(labels):
        off[i + 1] = off[i] + len(lab)
    idx = np.array([x for lab in labels for x in lab], dtype="<u2")
    out = bytearray(head)
    out[12:16] = struct.pack("<I", len(idx))
    out += off.tobytes() + idx.tobytes()
    Path(path).write_bytes(bytes(out))
    return hashlib.sha256(bytes(out)).hexdigest()[:16]


def read_bank(path: Path) -> Bank:
    blob = Path(path).read_bytes()
    assert blob[:4] == b"VBNK"
    ver, n, dim, nlab = struct.unpack_from("<IIII", blob, 4)
    assert ver == 1
    p = 20
    scale = np.frombuffer(blob, "<f4", n, p)
    p += 4 * n
    q = np.frombuffer(blob, np.int8, n * dim, p).reshape(n, dim)
    p += n * dim
    off = np.frombuffer(blob, "<u4", n + 1, p)
    p += 4 * (n + 1)
    idx = np.frombuffer(blob, "<u2", nlab, p)
    return Bank(dequant(q, scale), off.copy(), idx.copy(), hashlib.sha256(blob).hexdigest()[:16])


def write_vocab(folder: Path, vecs: np.ndarray, thr: np.ndarray, meta: dict) -> None:
    folder = Path(folder)
    q, scale = quantise(vecs)
    n, dim = q.shape
    blob = (
        b"VVOC"
        + struct.pack("<III", 1, n, dim)
        + scale.astype("<f4").tobytes()
        + q.tobytes()
        + np.asarray(thr, dtype="<f4").reshape(n, 3).tobytes()
    )
    (folder / "vocab.bin").write_bytes(blob)
    (folder / "vocab.json").write_text(json.dumps(meta, indent=1), encoding="utf-8")


def read_vocab(folder: Path) -> Vocab:
    folder = Path(folder)
    blob = (folder / "vocab.bin").read_bytes()
    assert blob[:4] == b"VVOC"
    ver, n, dim = struct.unpack_from("<III", blob, 4)
    assert ver == 1
    p = 16
    scale = np.frombuffer(blob, "<f4", n, p)
    p += 4 * n
    q = np.frombuffer(blob, np.int8, n * dim, p).reshape(n, dim)
    p += n * dim
    thr = np.frombuffer(blob, "<f4", n * 3, p).reshape(n, 3).copy()
    meta = json.loads((folder / "vocab.json").read_text(encoding="utf-8"))
    rows = dequant(q, scale)
    return Vocab(rows, thr, meta, noun_center(rows, meta))


def excluded_rows(bank: Bank, excl: set[int]) -> np.ndarray:
    n = len(bank.lab_off) - 1
    mask = np.zeros(n, dtype=bool)
    if not excl:
        return mask
    for i in range(n):
        labs = bank.lab_idx[bank.lab_off[i] : bank.lab_off[i + 1]]
        if any(int(x) in excl for x in labs):
            mask[i] = True
    return mask
