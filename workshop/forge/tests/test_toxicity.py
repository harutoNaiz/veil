import numpy as np

from workshop.forge.toxicity.parity import auc, pad_truncate, positive_index, toxic_score


def test_auc():
    assert auc([0, 0, 1, 1], [0.1, 0.2, 0.8, 0.9]) == 1.0
    assert auc([0, 0, 1, 1], [0.9, 0.8, 0.2, 0.1]) == 0.0
    assert auc([0, 1, 0, 1], [0.5, 0.5, 0.5, 0.5]) == 0.5
    assert np.isnan(auc([1, 1], [0.1, 0.2]))


def test_pad_truncate():
    i, m = pad_truncate([5, 6, 7], 5, 1)
    assert i.tolist() == [[5, 6, 7, 1, 1]] and m.tolist() == [[1, 1, 1, 0, 0]]
    i, m = pad_truncate(list(range(10)), 4, 1)
    assert i.shape == (1, 4) and m.sum() == 4 and i.dtype == np.int64


def test_score_and_index():
    assert abs(toxic_score(np.array([[0.0]]), 0) - 0.5) < 1e-9
    assert toxic_score(np.array([[0.0, 5.0]]), 1) > 0.99
    assert positive_index({0: "non-toxic", 1: "toxic"}) == 1
    assert positive_index({0: "LABEL_0", 1: "LABEL_1"}) == 1
