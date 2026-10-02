from __future__ import annotations

from pathlib import Path

import pytest

from workshop.bench import a11y_probe, adb

PROBE = a11y_probe.PROBE


def test_single_device_cases(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(adb, "devices", lambda: [])
    assert adb.single_device() is None
    monkeypatch.setattr(adb, "devices", lambda: [("S1", "unauthorized")])
    assert adb.single_device() is None
    monkeypatch.setattr(adb, "devices", lambda: [("S1", "device")])
    assert adb.single_device() == "S1"
    monkeypatch.setattr(adb, "devices", lambda: [("S1", "device"), ("S2", "unauthorized")])
    assert adb.single_device() == "S1"
    monkeypatch.setattr(adb, "devices", lambda: [("S1", "device"), ("S2", "device")])
    with pytest.raises(adb.MultipleDevicesError) as info:
        adb.single_device()
    assert "S1" not in str(info.value)
    assert "device, device" in str(info.value)


def test_only_veil_packages_can_be_touched(tmp_path: Path) -> None:
    apk = tmp_path / "x.apk"
    apk.write_bytes(b"x")
    with pytest.raises(adb.AdbError, match="refusing"):
        adb.install_if_changed("S1", apk, "com.android.settings")
    with pytest.raises(adb.AdbError, match="refusing"):
        adb.force_stop("S1", "com.android.settings")
    with pytest.raises(adb.AdbError, match="refusing"):
        adb.run_as_cat("S1", "com.android.settings", "files/x")


def test_bad_arguments_are_refused_before_adb_runs() -> None:
    with pytest.raises(adb.AdbError):
        adb.run_as_cat("S1", "com.veil.testfeed", "../databases/x")
    with pytest.raises(adb.AdbError):
        adb.run_as_cat("S1", "com.veil.testfeed", "/etc/passwd")
    with pytest.raises(adb.AdbError):
        adb.launch("S1", "com.veil.guard/.Main; rm -rf /")
    with pytest.raises(adb.AdbError):
        adb.keyevent("S1", "KEYCODE_HOME; reboot")


def test_install_if_changed_skips_an_identical_apk(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    apk = tmp_path / "x.apk"
    apk.write_bytes(b"same bytes")
    digest = adb._sha256(apk)
    calls: list[list[str]] = []

    class Done:
        def __init__(self, stdout: str) -> None:
            self.stdout, self.stderr, self.returncode = stdout, "", 0

    def fake_run(args: list[str], serial: str | None = None, **kwargs: object) -> Done:
        calls.append(args)
        if args[1].startswith("pm path"):
            return Done("package:/data/app/~~abc/com.veil.guard-xyz==/base.apk\n")
        if args[1].startswith("sha256sum"):
            return Done(f"{digest}  /data/app/~~abc/com.veil.guard-xyz==/base.apk\n")
        return Done("Success\n")

    monkeypatch.setattr(adb, "run", fake_run)
    assert adb.install_if_changed("S1", apk, "com.veil.guard") == "unchanged"
    assert not any(call[0] == "install" for call in calls)
    assert adb.install_if_changed("S1", apk, "com.veil.guard", force=True) == "installed"
    assert any(call[0] == "install" for call in calls)


def test_a11y_service_list_helpers() -> None:
    assert a11y_probe.split_services("null") == []
    assert a11y_probe.split_services("") == []
    assert a11y_probe.split_services("a/b:c/d") == ["a/b", "c/d"]
    assert a11y_probe.add_service("null") == PROBE
    assert a11y_probe.add_service("a/b:c/d") == f"a/b:c/d:{PROBE}"
    assert a11y_probe.add_service(f"a/b:{PROBE}") == f"a/b:{PROBE}"  # no duplicate
    assert a11y_probe.remove_service(f"a/b:{PROBE}:c/d") == "a/b:c/d"
    assert a11y_probe.remove_service(PROBE) == ""
    assert a11y_probe.remove_service("a/b") == "a/b"
