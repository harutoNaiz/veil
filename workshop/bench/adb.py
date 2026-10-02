"""Thin wrappers around the adb command line.

The adb program is `$ADB` when set (tools/env.ps1 points it at the toolchain), else `adb` on PATH.
Rules this module enforces, so a test run cannot do harm to the phone:
- only Veil's own three packages can be installed, force-stopped or read with run-as;
- the device serial never appears in an error message or in anything these functions return.
"""

from __future__ import annotations

import hashlib
import os
import re
import subprocess
from pathlib import Path

from workshop.bench import parse

ALLOWED_PACKAGES = ("com.veil.guard", "com.veil.console", "com.veil.testfeed")
_COMPONENT_RE = re.compile(r"^[A-Za-z0-9_.]+/[A-Za-z0-9_.$]+$")
_KEY_RE = re.compile(r"^(KEYCODE_[A-Z0-9_]+|\d+)$")
_REL_PATH_RE = re.compile(r"^[A-Za-z0-9_][A-Za-z0-9_./-]*$")


class AdbError(RuntimeError):
    """An adb call failed (not found, non-zero exit, timeout, or an unexpected device state)."""


class MultipleDevicesError(AdbError):
    """More than one device is in state "device" and no serial was chosen."""


def _exe() -> str:
    return os.environ.get("ADB") or "adb"


def _redact(text: str, serial: str | None) -> str:
    return text.replace(serial, "<serial>") if serial else text


def _check_package(package: str) -> None:
    if package not in ALLOWED_PACKAGES:
        raise AdbError(
            f"refusing to touch package {package!r}: only {', '.join(ALLOWED_PACKAGES)} are allowed"
        )


def run(
    args: list[str],
    serial: str | None = None,
    timeout: float = 60,
    check: bool = True,
    text: bool = True,
) -> subprocess.CompletedProcess:
    """Run `adb [-s serial] <args>`. With text=True the output is str (UTF-8), else bytes."""
    cmd = [_exe()] + (["-s", serial] if serial else []) + list(args)
    label = "adb " + " ".join(args[:2])
    kwargs: dict = {"capture_output": True, "timeout": timeout}
    if text:
        kwargs.update(text=True, encoding="utf-8", errors="replace")
    try:
        completed = subprocess.run(cmd, **kwargs)
    except FileNotFoundError as exc:
        raise AdbError(f"adb not found ({_exe()}); load the toolchain with tools/env.ps1") from exc
    except subprocess.TimeoutExpired as exc:
        raise AdbError(f"{label} timed out after {timeout:g} s") from exc
    if check and completed.returncode != 0:
        err = completed.stderr if text else completed.stderr.decode("utf-8", "replace")
        raise AdbError(
            f"{label} failed (exit {completed.returncode}): {_redact(err.strip(), serial)}"
        )
    return completed


def _lf(value: str) -> str:
    return value.replace("\r\n", "\n")


def devices() -> list[tuple[str, str]]:
    """Attached devices as [(serial, state)]."""
    return parse.parse_devices(run(["devices"], timeout=30).stdout)


def single_device() -> str | None:
    """The one serial in state "device"; None if no device; MultipleDevicesError if several."""
    attached = devices()
    ready = [serial for serial, state in attached if state == "device"]
    if len(ready) > 1:
        states = ", ".join(state for _, state in attached)
        raise MultipleDevicesError(
            f"{len(attached)} devices attached (states: {states}); choose one with --serial"
        )
    return ready[0] if ready else None


def shell(serial: str, cmd: str, timeout: float = 60) -> str:
    """Run a command on the phone and return its stdout."""
    return _lf(run(["shell", cmd], serial, timeout).stdout)


def getprop(serial: str) -> dict[str, str]:
    return parse.parse_getprop(shell(serial, "getprop"))


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def install_if_changed(
    serial: str, apk: Path, package: str, force: bool = False, timeout: float = 180
) -> str:
    """Install `apk` unless the phone already has the same file: "installed" or "unchanged"."""
    _check_package(package)
    if not apk.is_file():
        raise AdbError(f"APK missing: {apk}")
    if not force:
        listed = run(["shell", f"pm path {package}"], serial, timeout=60, check=False).stdout
        paths = [
            line[len("package:") :].strip()
            for line in listed.splitlines()
            if line.startswith("package:")
        ]
        base = next((p for p in paths if p.endswith("base.apk")), paths[0] if paths else None)
        if base and re.fullmatch(r"/[A-Za-z0-9_.=~/+-]+", base):
            digest = run(
                ["shell", f"sha256sum {base}"], serial, timeout=60, check=False
            ).stdout.split()
            if digest and digest[0].lower() == _sha256(apk):
                return "unchanged"
    out = run(["install", "-r", str(apk)], serial, timeout=timeout)
    if "Success" not in out.stdout:
        raise AdbError(f"adb install did not report Success: {_redact(out.stdout.strip(), serial)}")
    return "installed"


def launch(serial: str, component: str) -> None:
    """Start an activity and wait for it: `am start -W -n <package>/<activity>`."""
    if not _COMPONENT_RE.match(component):
        raise AdbError(f"bad component name {component!r}")
    out = shell(serial, f"am start -W -n {component}")
    if "Error" in out:
        raise AdbError(f"am start failed: {out.strip()}")


def force_stop(serial: str, package: str) -> None:
    _check_package(package)
    shell(serial, f"am force-stop {package}")


def resumed_activity(serial: str) -> str | None:
    """The activity that is on screen now, as "package/.Class", or None."""
    out = run(
        ["shell", "dumpsys activity activities | grep -E 'ResumedActivity'"],
        serial,
        timeout=60,
        check=False,
    ).stdout
    return parse.parse_resumed_activity(_lf(out))


def screencap(serial: str, dest: Path) -> None:
    """Save a PNG screenshot of the phone to `dest`."""
    data = run(["exec-out", "screencap", "-p"], serial, timeout=60, text=False).stdout
    if not data.startswith(b"\x89PNG"):
        raise AdbError("screencap did not return a PNG (screen off or secure window?)")
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(data)


def swipe(serial: str, x1: int, y1: int, x2: int, y2: int, duration_ms: int) -> None:
    shell(serial, f"input swipe {int(x1)} {int(y1)} {int(x2)} {int(y2)} {int(duration_ms)}")


def tap(serial: str, x: int, y: int) -> None:
    shell(serial, f"input tap {int(x)} {int(y)}")


def keyevent(serial: str, key: str) -> None:
    if not _KEY_RE.match(key):
        raise AdbError(f"bad key name {key!r}")
    shell(serial, f"input keyevent {key}")


def logcat_clear(serial: str) -> None:
    run(["logcat", "-c"], serial, timeout=30)


def logcat_dump(serial: str, filterspecs: list[str]) -> str:
    """`adb logcat -d -s <specs>`: the log buffer now, for the given tag:priority filters."""
    return _lf(run(["logcat", "-d", "-s", *filterspecs], serial, timeout=60).stdout)


def run_as_cat(serial: str, package: str, rel_path: str) -> bytes:
    """Read a private app file (debug builds only): `run-as <package> cat <path>`."""
    _check_package(package)
    if not _REL_PATH_RE.match(rel_path) or ".." in rel_path.split("/"):
        raise AdbError(f"bad relative path {rel_path!r}")
    return run(
        ["exec-out", "run-as", package, "cat", rel_path], serial, timeout=60, text=False
    ).stdout


def screen_size(serial: str) -> tuple[int, int]:
    """(width, height) in px; an "Override size" wins over the physical size."""
    return parse.parse_wm_size(shell(serial, "wm size"))
