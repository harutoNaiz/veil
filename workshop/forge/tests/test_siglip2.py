import numpy as np
from PIL import Image

from workshop.forge.siglip2.parity import judge_images, prompts
from workshop.forge.siglip2.runtime import DIM, OnnxDescriber, pick_batch


class StubSession:
    def __init__(self, calls, batch):
        self.calls, self.batch = calls, batch

    def run(self, _names, feeds):
        px = feeds["pixel_values"]
        assert px.shape[0] == self.batch
        self.calls.append(self.batch)
        out = np.zeros((self.batch, DIM), dtype=np.float32)
        out[:, 0] = px[:, 0, 0, 0] + 1.0  # row i carries its own marker
        out[:, 1] = 1.0
        return [out]


class StubProcessor:
    def __call__(self, images, return_tensors):
        px = np.zeros((len(images), 3, 224, 224), dtype=np.float32)
        for i, im in enumerate(images):
            px[i] += im.getpixel((0, 0))[0]
        return {"pixel_values": px}


def test_pick_batch():
    assert [pick_batch(n) for n in (1, 2, 4, 5, 16)] == [1, 4, 4, 16, 16]


def test_padding_and_order():
    calls: list[int] = []
    d = OnnxDescriber(
        sessions={f"b{b}": StubSession(calls, b) for b in (1, 4, 16)}, processor=StubProcessor()
    )
    imgs = [Image.new("RGB", (8, 8), (i, 0, 0)) for i in range(21)]
    out = d.embed_images(imgs)
    assert out.shape == (21, DIM)
    assert calls == [16, 16]  # 16 images, then 5 padded into b16
    assert out[20, 0] > out[19, 0] > 0  # order kept, pad rows dropped
    assert np.allclose(np.linalg.norm(out, axis=1), 1.0, atol=1e-5)


def test_empty():
    assert OnnxDescriber(sessions={}).embed_images([]).shape == (0, DIM)


def test_judge_and_prompts():
    j = judge_images(np.array([1.0] * 19 + [0.9]))
    assert j["min"] == 0.9 and j["worst5"] == 0.9
    p = prompts()
    assert len(p) == 100 and len(set(p)) == 100


def test_small_chunks_use_b4_and_b1():
    calls: list[int] = []
    d = OnnxDescriber(
        sessions={f"b{b}": StubSession(calls, b) for b in (1, 4, 16)}, processor=StubProcessor()
    )
    assert d.embed_images([Image.new("RGB", (8, 8), (7, 0, 0))] * 3).shape == (3, DIM)
    assert d.embed_images([Image.new("RGB", (8, 8))]).shape == (1, DIM)
    assert calls == [4, 1]
