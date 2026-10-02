"""Light tests for 3.1.2: numpy decode pieces, concept score, proposal_pe. No model load."""

from __future__ import annotations

import numpy as np
import pytest

from workshop.forge.yoloe import runtime as rt

SIZE = (360, 800)  # w, h of a phone screenshot


def test_proposal_pe_shape_and_norm():
    pe = np.load(rt.PROPOSAL_PE)
    assert pe.shape == (8, 512) and pe.dtype == np.float32
    assert np.allclose(np.linalg.norm(pe, axis=1), 1, atol=1e-4)


def test_pad_prompts_repeats_last():
    pe = np.eye(3, 512, dtype=np.float32)
    out = rt.pad_prompts(pe)
    assert out.shape == (1, 8, 512)
    assert np.array_equal(out[0, 2], out[0, 7])
    with pytest.raises(ValueError):
        rt.pad_prompts(np.ones((9, 512), np.float32))


def test_nms_keeps_best_and_disjoint():
    boxes = np.array([[0, 0, 10, 10], [1, 1, 10, 10], [50, 50, 60, 60]], np.float32)
    assert rt.nms(boxes, np.array([0.5, 0.9, 0.4])) == [1, 2]


def test_unletterbox_roundtrip():
    w0, h0 = SIZE
    gain, left, top = rt.letterbox_params(w0, h0)
    box = np.array([[100.0, 200.0, 300.0, 600.0]], np.float32)
    lb = box.copy()
    lb[:, [0, 2]] = lb[:, [0, 2]] * gain + left
    lb[:, [1, 3]] = lb[:, [1, 3]] * gain + top
    assert np.allclose(rt.unletterbox(lb, SIZE), box, atol=1.0)


def test_select_filters_and_regions():
    boxes = np.zeros((100, 4), np.float32)
    obj = np.zeros(100, np.float32)
    gain, left, top = rt.letterbox_params(*SIZE)
    boxes[0] = [left + 20, top + 40, left + 200, top + 400]  # kept
    boxes[1] = [left + 21, top + 41, left + 201, top + 401]  # NMS duplicate of 0
    boxes[2] = [left + 5, top + 5, left + 8, top + 8]  # too small
    boxes[3] = [left + 0, top + 0, left + 100, top + 100]  # below CONF
    obj[:4] = [0.9, 0.8, 0.7, 0.01]
    xyxy, conf, keep = rt.select(boxes, obj, SIZE)
    assert list(keep) == [0] and len(xyxy) == 1 and conf[0] == pytest.approx(0.9)
    from workshop.twin.finder import Finder

    regs = Finder._regions(xyxy, conf, SIZE)
    assert regs[0]["rect"]["w"] > 0 and regs[0]["source"] == "finder"


def test_concept_score_formula():
    fp = np.array([[1.0, 0.0]], np.float32)
    text = np.array([[1.0, 0.0], [0.0, 1.0]], np.float32)
    s = rt.concept_score(fp, np.array([10.0]), np.array([-5.0]), text)
    assert s[0, 0] == pytest.approx(1 / (1 + np.exp(-5)), abs=1e-6)
    assert s[0, 1] == pytest.approx(1 / (1 + np.exp(5)), abs=1e-6)


def test_wrapper_torch_concept_score_matches_numpy():
    torch = pytest.importorskip("torch")
    from workshop.forge.yoloe.wrapper import concept_scores

    rng = np.random.default_rng(0)
    fp, text = rng.normal(size=(4, 16)), rng.normal(size=(3, 16))
    fp /= np.linalg.norm(fp, axis=1, keepdims=True)
    sc, bi = rng.uniform(1, 20, 4), rng.uniform(-8, 0, 4)
    a = concept_scores(*(torch.tensor(v, dtype=torch.float32) for v in (fp, sc, bi, text)))
    b = rt.concept_score(fp, sc, bi, text)
    assert np.allclose(a.numpy(), b, atol=1e-5)
