import numpy as np
import pytest

from workshop.twin.corrections import CAP, MAX_EXCEPTIONS, CorrectionBook


def _fb(kind, cid="cat", layer=2):
    return {"kind": kind, "conceptId": cid, "layer": layer}


def _vec(i):
    v = np.zeros(32)
    v[i % 32] = 1.0
    v[(i * 7 + 1) % 32] += 0.5 + i * 0.01
    return v


def test_exceptions_bounded_oldest_dropped():
    b = CorrectionBook()
    for i in range(70):
        b.record(_fb("notThis"), _vec(i))
    assert len(b.exceptions["cat"]) == MAX_EXCEPTIONS
    first_kept = b.exceptions["cat"][0]
    assert np.allclose(first_kept, _vec(6) / np.linalg.norm(_vec(6)), atol=1e-2)


def test_nudge_caps():
    b = CorrectionBook()
    for _ in range(10):
        b.record(_fb("notThis"), None)
    assert b.nudge["cat"] == pytest.approx(CAP)
    assert b.adjust({"conceptId": "cat", "userOffset": 0.0})["userOffset"] == pytest.approx(-CAP)
    b2 = CorrectionBook()
    for _ in range(10):
        b2.record(_fb("missed"), None)
    assert b2.nudge["cat"] == pytest.approx(-CAP)


def test_layer1_rejected_and_identity():
    b = CorrectionBook()
    with pytest.raises(ValueError):
        b.record(_fb("notThis", layer=1), _vec(0))
    with pytest.raises(ValueError):
        b.record(_fb("notThis", cid="nsfw"), _vec(0))
    cc = {"conceptId": "nsfw", "userOffset": 0.0}
    assert b.adjust(cc) is cc
    v = {"decision": "hide"}
    assert b.filter("nsfw", _vec(0), v) is v
    assert b.filter("x", _vec(0), v, layer=1) is v


def test_filter_and_roundtrip():
    b = CorrectionBook()
    b.record(_fb("notThis"), _vec(3))
    assert b.filter("cat", _vec(3), {"decision": "hide"})["decision"] == "leave"
    assert b.filter("cat", _vec(12), {"decision": "hide"})["decision"] == "hide"
    b2 = CorrectionBook.from_json(b.to_json(), 32)
    assert b2.filter("cat", _vec(3), {"decision": "hide"})["decision"] == "leave"
