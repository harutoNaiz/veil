import numpy as np

from workshop.twin.bank import bankio, coco, ui_synth, vocab


def _unit(rng, n, d):
    v = rng.normal(size=(n, d)).astype(np.float32)
    return v / np.linalg.norm(v, axis=1, keepdims=True)


def test_roundtrip(tmp_path):
    rng = np.random.default_rng(1)
    v = _unit(rng, 20, 32)
    labels = [[1, 2], [], [3]] + [[] for _ in range(17)]
    bid = bankio.write_bank(tmp_path / "bank.bin", v, labels)
    b = bankio.read_bank(tmp_path / "bank.bin")
    assert b.bank_id == bid
    assert (b.rows * v).sum(axis=1).min() >= 0.9999
    assert list(b.lab_idx) == [1, 2, 3] and list(b.lab_off[:4]) == [0, 2, 2, 3]
    assert bankio.excluded_rows(b, {2}).tolist()[:3] == [True, False, False]
    thr = rng.normal(size=(5, 3)).astype(np.float32)
    meta = {"version": 1}
    bankio.write_vocab(tmp_path, v[:5], thr, meta)
    voc = bankio.read_vocab(tmp_path)
    assert np.allclose(voc.thr, thr) and voc.meta == meta
    assert (voc.rows * v[:5]).sum(axis=1).min() >= 0.9999


def test_ui_deterministic():
    a, b = ui_synth.render_screen(5), ui_synth.render_screen(5)
    assert a.tobytes() == b.tobytes() and a.size == (360, 720)
    assert a.tobytes() != ui_synth.render_screen(6).tobytes()


def test_filter():
    imgs = [
        {"id": 1, "file_name": "a.jpg", "license": 4},
        {"id": 2, "file_name": "b.jpg", "license": 1},  # licence not allowed
        {"id": 3, "file_name": "c.jpg", "license": 7},
        {"id": 4, "file_name": "d.jpg", "license": 8},  # blocklisted caption
        {"id": 5, "file_name": "e.jpg", "license": 5},
    ]
    caps = {1: "a dog", 2: "a cat", 3: "a bison", 4: "a woman in a Bikini", 5: "a bus"}
    ann = [{"image_id": i, "caption": c} for i, c in caps.items()]
    out = coco.filter_items({"images": imgs, "annotations": ann})
    assert sorted(x["id"] for x in out) == [1, 3, 5]


def test_relations():
    names = ["dog", "puppy", "animal", "cat"]
    tbl = {
        "dog": ({"dog", "puppy"}, {"animal"}),
        "puppy": ({"puppy"}, {"dog", "animal"}),
        "animal": ({"animal", "dog", "puppy", "cat"}, set()),
        "cat": ({"cat"}, {"animal"}),
    }
    excl, rel = vocab.relations(names, lambda n: tbl[n])
    assert excl[0] == [0, 1] and rel[0] == [0, 1, 2]
    assert excl[3] == [3] and rel[3] == [2, 3]
    assert excl[2] == [0, 1, 2, 3]


def test_quantile():
    d = np.arange(1000, dtype=np.float64)
    assert vocab.quantile(d, 995) == 994.0


def test_relabel_keeps_header(tmp_path):
    """relabel_bank must update nLabels, never the dim field (A1 regression)."""
    rng = np.random.default_rng(1)
    vecs = rng.normal(size=(5, 8)).astype(np.float32)
    path = tmp_path / "bank.bin"
    bankio.write_bank(path, vecs, [[1], [2, 3], [], [4], [5, 6, 7]])
    bankio.relabel_bank(path, [[1, 2, 3, 4], [], [5], [6], [7, 8]])
    bk = bankio.read_bank(path)
    assert bk.rows.shape == (5, 8)
    got = [bk.lab_idx[bk.lab_off[i] : bk.lab_off[i + 1]].tolist() for i in range(5)]
    assert got == [[1, 2, 3, 4], [], [5], [6], [7, 8]]
