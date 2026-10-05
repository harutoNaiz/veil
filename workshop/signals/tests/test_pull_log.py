import json

from workshop.signals.pull_log import shift_boottime


def test_shift_boottime():
    lines = [
        '{"eventId":0,"tMs":100,"type":"screenOn"}',
        "",
        '{"eventId":1,"tMs":250,"type":"screenOff"}',
    ]
    out = shift_boottime(lines, {"uptimeMs": 1000, "elapsedRealtimeMs": 5000})
    assert [json.loads(x)["tMs"] for x in out] == [4100, 4250]
    assert json.loads(out[0])["eventId"] == 0
