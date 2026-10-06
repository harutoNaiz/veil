import json
import threading
import time

import numpy as np

from workshop.twin.bank import build_bank, engine


class FakeSession:
    def __init__(self):
        self.shapes = []

    def run(self, names, feed):
        px = feed["pixel_values"]
        self.shapes.append(px.shape)
        return [np.tile(px.reshape(px.shape[0], -1)[:, :1], (1, 768)).astype(np.float32) + 1.0]


def test_pads_to_16():
    sess = FakeSession()
    d = engine.FixedBatchOnnx(".", sessions={"b16": sess})
    px = np.arange(5, dtype=np.float32).reshape(5, 1, 1, 1) * np.ones((5, 3, 4, 4), "f4")
    out = d._run_chunk(px)
    assert sess.shapes == [(16, 3, 4, 4)]
    assert out.shape == (5, 768)
    assert out[3, 0] == 4.0


def test_prefetch_ordered_and_bounded():
    started = []
    lock = threading.Lock()

    def fetch(x):
        with lock:
            started.append(x)
        return x * 2

    chunks = [[i * 3, i * 3 + 1, i * 3 + 2] for i in range(40)]
    gen = engine.prefetch(chunks, fetch, threads=4, depth=4)
    ch, res = next(gen)
    time.sleep(0.5)
    assert res == [x * 2 for x in ch]
    assert len(started) <= 3 * (4 + 3)  # bounded read-ahead
    got = [c for c, _ in gen]
    assert [x for c in [ch] + got for x in c] == list(range(120))


def test_engine_mismatch_refused(tmp_path):
    (tmp_path / "partial.npz").write_bytes(b"x")
    (tmp_path / "engine.json").write_text(json.dumps({"engine": "torch", "provider": "cpu"}))
    rc = build_bank.main(["--out", str(tmp_path), "--limit", "1", "--ui", "0", "--engine", "onnx"])
    assert rc == 3
