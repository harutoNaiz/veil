import json

from workshop.harden.session_check import check, main

HDR = "10-05 12:00:00.000  100  100 E AndroidRuntime: "


def _log(tmp_path, body):
    p = tmp_path / "l.txt"
    p.write_text(body, encoding="utf-8")
    return p


def _crash(proc):
    return f"{HDR}FATAL EXCEPTION: main\n{HDR}Process: {proc}, PID: 5\n{HDR}java.lang.Boom\n"


def test_clean(tmp_path):
    assert check(_log(tmp_path, "I/x ok\n"), None, "com.veil")["verdict"] == "PASS"


def test_veil_crash(tmp_path):
    r = check(_log(tmp_path, _crash("com.veil.guard")), None, "com.veil")
    assert r["crashes"] == 1 and r["verdict"] == "FAIL"


def test_other_app_crash_ignored(tmp_path):
    r = check(_log(tmp_path, _crash("com.other.app")), None, "com.veil")
    assert r["crashes"] == 0 and r["verdict"] == "PASS"


def test_stuck_cover(tmp_path):
    ev = [
        {"tMs": 0, "id": "a", "op": "show"},
        {"tMs": 100, "id": "", "op": "appSwitch"},
    ]
    c = tmp_path / "c.jsonl"
    c.write_text("\n".join(json.dumps(e) for e in ev), encoding="utf-8")
    log = _log(tmp_path, "ok\n")
    assert check(log, c, "com.veil")["stuckCovers"] == 1
    assert main(["--logcat", str(log), "--covers", str(c)]) == 1
    ev.append({"tMs": 900, "id": "a", "op": "hide"})
    c.write_text("\n".join(json.dumps(e) for e in ev), encoding="utf-8")
    assert check(log, c, "com.veil")["stuckCovers"] == 0
