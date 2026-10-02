from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from workshop.bench import adb, aihub, bench_check

PHONE_AND_CLOUD_LINES = "adb,scrcpy,guard-app,console-app,testfeed,aihub-devices,aihub-profile"


def read_json(out: Path) -> dict:
    return json.loads((out / "bench-check.json").read_text(encoding="utf-8"))


def by_id(summary: dict) -> dict[str, dict]:
    return {line["id"]: line for line in summary["lines"]}


def test_line_ids_are_the_thirteen_of_the_spec() -> None:
    assert len(bench_check.LINE_IDS) == 13
    assert set(bench_check.LINES) == set(bench_check.LINE_IDS)


def test_toolchain_line_runs_bootstrap_without_the_active_venv(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """`uv run` sets VIRTUAL_ENV, which would make bootstrap pick the repo venv as its Python."""
    seen: dict = {}

    def fake_run_cmd(cmd: list[str], cwd: Path, timeout: float, log: Path, **kwargs: object):
        seen.update(cmd=cmd, env=kwargs.get("env"))
        return SimpleNamespace(returncode=0, stdout="table\nBOOTSTRAP OK\n", stderr="")

    monkeypatch.setenv("VIRTUAL_ENV", "C:/somewhere/.venv")
    monkeypatch.setattr(bench_check, "_run_cmd", fake_run_cmd)
    ctx = bench_check._Ctx(tmp_path, "never", True, True, None, False)
    assert bench_check._line_toolchain(ctx) == ("PASS", "BOOTSTRAP OK")
    assert "-CheckOnly" in seen["cmd"]
    assert seen["env"] is not None
    assert "VIRTUAL_ENV" not in seen["env"]
    assert "PATH" in seen["env"] or "Path" in seen["env"]


def test_without_phone_or_token_every_phone_and_cloud_line_is_skipped(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr(adb, "devices", lambda: [])
    monkeypatch.setattr(aihub, "is_configured", lambda: False)
    assert bench_check.main(["--only", PHONE_AND_CLOUD_LINES, "--out", str(tmp_path)]) == 2
    summary = read_json(tmp_path)
    lines = by_id(summary)
    assert [line["id"] for line in summary["lines"]] == PHONE_AND_CLOUD_LINES.split(",")
    assert {line["status"] for line in lines.values()} == {"SKIP"}
    assert lines["adb"]["detail"] == "no adb device (connect the phone: HC-002)"
    for line_id in ("scrcpy", "guard-app", "console-app", "testfeed"):
        assert lines[line_id]["detail"].startswith("adb not PASS")
        assert "HC-002" in lines[line_id]["detail"]
    assert lines["aihub-devices"]["detail"] == "AI Hub not configured (HC-003)"
    assert lines["aihub-profile"]["detail"] == "AI Hub not configured (HC-003)"
    assert summary["result"] == {"pass": 0, "fail": 0, "skip": 7}
    assert summary["exitCode"] == 2

    out = capsys.readouterr().out.splitlines()
    assert out[-1] == "RESULT: 0 PASS, 0 FAIL, 7 SKIP"
    assert out[0].startswith("[SKIP] adb ")
    assert all(line.isascii() for line in out)
    assert (tmp_path / "bench-check.txt").read_text(encoding="ascii").splitlines() == out


def test_skip_flags_give_their_own_reasons(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    def must_not_be_called() -> list:
        raise AssertionError("adb must not be touched with --skip-phone")

    monkeypatch.setattr(adb, "devices", must_not_be_called)
    argv = [
        "--skip-phone",
        "--skip-cloud",
        "--only",
        "adb,guard-app,aihub-devices,aihub-profile,huggingface",
    ]
    assert bench_check.main([*argv, "--out", str(tmp_path)]) == 2
    lines = by_id(read_json(tmp_path))
    assert lines["adb"]["detail"] == "--skip-phone"
    assert lines["guard-app"]["detail"] == "adb not PASS (--skip-phone)"
    assert lines["aihub-devices"]["detail"] == "--skip-cloud"
    assert lines["aihub-profile"]["detail"] == "--skip-cloud"
    assert lines["huggingface"]["detail"] == "--skip-cloud"


def test_an_unauthorized_phone_is_a_failure_and_its_serial_is_never_printed(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr(adb, "devices", lambda: [("SECRETSERIAL123", "unauthorized")])
    assert bench_check.main(["--only", "adb,scrcpy", "--out", str(tmp_path)]) == 1
    lines = by_id(read_json(tmp_path))
    assert lines["adb"]["status"] == "FAIL"
    assert "accept the USB debugging prompt" in lines["adb"]["detail"]
    assert lines["scrcpy"]["status"] == "SKIP"
    everything = capsys.readouterr().out + "".join(
        p.read_text(encoding="utf-8") for p in tmp_path.iterdir()
    )
    assert "SECRETSERIAL123" not in everything


def test_one_ready_phone_passes_the_adb_line_with_a_hashed_id(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(adb, "devices", lambda: [("SECRETSERIAL123", "device")])
    assert bench_check.main(["--only", "adb", "--out", str(tmp_path)]) == 0
    detail = by_id(read_json(tmp_path))["adb"]["detail"]
    assert "SECRETSERIAL123" not in detail
    assert "(id " in detail


def test_two_ready_phones_need_a_serial(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.setattr(adb, "devices", lambda: [("A1", "device"), ("B2", "device")])
    assert bench_check.main(["--only", "adb", "--out", str(tmp_path)]) == 1
    assert "choose one with --serial" in by_id(read_json(tmp_path))["adb"]["detail"]
    assert bench_check.main(["--only", "adb", "--serial", "B2", "--out", str(tmp_path)]) == 0


def test_missing_apk_is_a_failure_when_a_phone_is_present(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(adb, "devices", lambda: [("A1", "device")])
    monkeypatch.setattr(bench_check, "TESTFEED_APK", tmp_path / "nope" / "testfeed-debug.apk")
    assert bench_check.main(["--only", "adb,testfeed", "--out", str(tmp_path / "out")]) == 1
    detail = by_id(read_json(tmp_path / "out"))["testfeed"]["detail"]
    assert detail.startswith("APK missing: ")
    assert detail.endswith("(run without --only, or build first)")


def test_a_line_that_raises_is_a_failure_not_a_crash(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    def boom() -> list:
        raise adb.AdbError("adb not found (adb); load the toolchain with tools/env.ps1")

    monkeypatch.setattr(adb, "devices", boom)
    assert bench_check.main(["--only", "adb", "--out", str(tmp_path)]) == 1
    assert "adb not found" in by_id(read_json(tmp_path))["adb"]["detail"]


def test_unknown_line_id_is_rejected(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    assert bench_check.main(["--only", "nonsense", "--out", str(tmp_path)]) == 1
    assert "unknown line id" in capsys.readouterr().out
