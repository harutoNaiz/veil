import json

import jsonschema
import numpy as np
import pytest
from PIL import Image

from workshop.overlay.own_join import join
from workshop.overlay.selfcap_check import check


def frame(i, t):
    return {
        "contractVersion": "1.0",
        "frameId": i,
        "tMs": t,
        "width": 360,
        "height": 792,
        "screenWidth": 1440,
        "screenHeight": 3168,
        "rotation": 0,
        "source": "replay",
        "ownOverlay": [],
    }


def test_join_latest_sample_before_frame():
    own = [
        {"tMs": 100, "rects": [{"x": 1, "y": 2, "w": 3, "h": 4}]},
        {"tMs": 200, "rects": []},
    ]
    out = join([frame(0, 50), frame(1, 150), frame(2, 250)], own)
    assert [len(f["ownOverlay"]) for f in out] == [0, 1, 0]
    assert out[1]["ownOverlay"][0] == {"x": 1, "y": 2, "w": 3, "h": 4}


def test_join_rejects_invalid_frame():
    bad = frame(0, 10)
    bad["rotation"] = 45
    with pytest.raises(jsonschema.ValidationError):
        join([bad], [])


def test_selfcap_detects_cover(tmp_path):
    img = np.full((792, 360, 3), 255, np.uint8)
    img[100:200, 40:140] = (0x20, 0x21, 0x24)
    Image.fromarray(img).save(tmp_path / "a.png")
    f = frame(0, 10)
    f["image"] = "a.png"
    f["ownOverlay"] = [{"x": 160, "y": 400, "w": 400, "h": 400}]
    res = check([f], tmp_path)
    assert res["coversCaptured"] and res["aligned2px"]
    json.dumps(res)
