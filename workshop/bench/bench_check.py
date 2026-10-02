"""bench_check: the Phase 1.1 proof test in one command. See docs/bench-check.md.

    tools\\bench_check.ps1 [--out DIR] [--build {if-missing,always,never}] [--skip-phone]
                          [--skip-cloud]
                          [--only ID[,ID...]] [--serial S] [--reinstall]

Runs the 13 lines in LINE_IDS order, one at a time, and prints one ASCII line per check
("[PASS] id  detail"), then "RESULT: n PASS, n FAIL, n SKIP". Exit code: 0 all PASS, 1 any FAIL,
2 no FAIL and at least one SKIP (for example no phone yet: HC-002, or AI Hub not set up: HC-003).
Output files (logs, screenshots, bench-check.txt and bench-check.json) go to --out, which
defaults to
data/evidence/1.1/bench-<YYYYmmdd-HHMMSS>/. The adb serial and any token are never printed or saved.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import time
from collections.abc import Callable
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Literal

from workshop.bench import adb, aihub, device_profile, drive, hf, parse, testfeed

REPO = Path(__file__).resolve().parents[2]
GUARD_DIR = REPO / "guard"
CONSOLE_DIR = REPO / "console"
GUARD_APK = GUARD_DIR / "app" / "build" / "outputs" / "apk" / "debug" / "app-debug.apk"
TESTFEED_APK = GUARD_DIR / "testfeed" / "build" / "outputs" / "apk" / "debug" / "testfeed-debug.apk"
CONSOLE_APK = CONSOLE_DIR / "build" / "app" / "outputs" / "flutter-apk" / "app-debug.apk"
PROFILE_MD = REPO / "docs" / "device-profile.md"

LINE_IDS = (
    "toolchain",
    "python-tests",
    "contracts",
    "build-guard",
    "build-console",
    "adb",
    "scrcpy",
    "guard-app",
    "console-app",
    "testfeed",
    "aihub-devices",
    "aihub-profile",
    "huggingface",
)

BUILD_TIMEOUT_S = 45 * 60
PYTEST_TIMEOUT_S = 10 * 60
AIHUB_TIMEOUT_S = 30 * 60
DEFAULT_TIMEOUT_S = 3 * 60
HELLO_WAIT_S = 10
CONSOLE_WAIT_S = 15
RAM_TOLERANCE = 0.01

Status = Literal["PASS", "FAIL", "SKIP"]
Outcome = tuple[Status, str]

NO_PHONE = "no adb device (connect the phone: HC-002)"
NO_AIHUB = "AI Hub not configured (HC-003)"


@dataclass
class LineResult:
    id: str
    status: Status
    detail: str
    seconds: float


@dataclass
class _Ctx:
    out: Path
    build: str
    skip_phone: bool
    skip_cloud: bool
    serial: str | None
    reinstall: bool
    device: tuple[Status, str, str | None] | None = None
    hub_names: tuple[Status, str, list[str]] | None = None


def _rel(path: Path) -> str:
    try:
        return path.relative_to(REPO).as_posix()
    except ValueError:
        return str(path)


def _ascii(text: str) -> str:
    return " ".join(text.split()).encode("ascii", "replace").decode("ascii")


def _run_cmd(
    cmd: list[str],
    cwd: Path,
    timeout: float,
    log: Path,
    hide: str | None = None,
    env: dict[str, str] | None = None,
) -> subprocess.CompletedProcess:
    """Run a command, save its output to `log` (minus `hide`) and return it. Raises on timeout."""
    completed = subprocess.run(
        cmd,
        cwd=cwd,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=timeout,
        env=env,
    )
    header = f"$ {' '.join(cmd)}\n(exit {completed.returncode})\n\n"
    body = header + f"{completed.stdout}\n{completed.stderr}"
    if hide:
        body = body.replace(hide, "<serial>")
    log.write_text(body, encoding="utf-8")
    return completed


def _last_line(text: str) -> str:
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    return lines[-1] if lines else ""


def _mb(path: Path) -> str:
    return f"{path.stat().st_size / 1_000_000:.1f} MB"


# --- device and cloud state, resolved once and shared by the lines that need them ---------


def _device(ctx: _Ctx) -> tuple[Status, str, str | None]:
    if ctx.device is not None:
        return ctx.device
    result: tuple[Status, str, str | None]
    if ctx.skip_phone:
        result = ("SKIP", "--skip-phone", None)
    else:
        try:
            result = _find_device(ctx)
        except adb.AdbError as exc:
            result = ("FAIL", str(exc), None)
    ctx.device = result
    return result


def _find_device(ctx: _Ctx) -> tuple[Status, str, str | None]:
    attached = adb.devices()
    if not attached:
        return "SKIP", NO_PHONE, None
    if ctx.serial:
        states = [state for serial, state in attached if serial == ctx.serial]
        if not states:
            return "FAIL", "the serial given with --serial is not attached", None
        if states[0] != "device":
            return "FAIL", _state_problem([states[0]]), None
        serial: str | None = ctx.serial
    else:
        try:
            serial = adb.single_device()
        except adb.AdbError as exc:
            return "FAIL", str(exc), None
        if serial is None:
            return "FAIL", _state_problem([state for _, state in attached]), None
    assert serial is not None
    tag = hashlib.sha256(serial.encode()).hexdigest()[:8]
    return "PASS", f"1 device in state 'device' (id {tag})", serial


def _state_problem(states: list[str]) -> str:
    if "unauthorized" in states:
        return "device unauthorized: accept the USB debugging prompt on the phone"
    return f"device not ready (state: {', '.join(states)})"


def _need_device(ctx: _Ctx) -> tuple[str | None, Outcome | None]:
    """(serial, None) when a phone is ready, else (None, the SKIP outcome for the line)."""
    status, detail, serial = _device(ctx)
    if status == "PASS" and serial:
        return serial, None
    return None, ("SKIP", f"adb not PASS ({detail})")


def _hub_names(ctx: _Ctx) -> tuple[Status, str, list[str]]:
    if ctx.hub_names is not None:
        return ctx.hub_names
    result: tuple[Status, str, list[str]]
    if ctx.skip_cloud:
        result = ("SKIP", "--skip-cloud", [])
    elif not aihub.is_configured():
        result = ("SKIP", NO_AIHUB, [])
    else:
        try:
            names = aihub.family_devices()
        except Exception as exc:
            result = ("FAIL", f"{type(exc).__name__}: {exc}", [])
        else:
            if names:
                result = ("PASS", f"{len(names)} device(s): {', '.join(names)}", names)
            else:
                result = ("FAIL", "no 8 Elite Gen 5 family device listed by AI Hub", [])
    ctx.hub_names = result
    return result


# --- the 13 lines --------------------------------------------------------------------------


def _line_toolchain(ctx: _Ctx) -> Outcome:
    powershell = shutil.which("powershell") or shutil.which("pwsh")
    if powershell is None:
        return "FAIL", "powershell not found"
    script = REPO / "tools" / "bootstrap.ps1"
    cmd = [
        powershell,
        "-NoProfile",
        "-ExecutionPolicy",
        "Bypass",
        "-File",
        str(script),
        "-CheckOnly",
    ]
    # `uv run` sets VIRTUAL_ENV, which would make `uv python find` report the repo venv instead of
    # the toolchain's Python, so the check runs without it.
    env = {key: value for key, value in os.environ.items() if key != "VIRTUAL_ENV"}
    done = _run_cmd(cmd, REPO, DEFAULT_TIMEOUT_S, ctx.out / "toolchain.txt", env=env)
    last = _last_line(done.stdout)
    if done.returncode == 0:
        return "PASS", last or "bootstrap -CheckOnly exit 0"
    return "FAIL", f"bootstrap -CheckOnly exit {done.returncode}: {last}"


def _pytest(ctx: _Ctx, target: str, log: str) -> Outcome:
    done = _run_cmd(
        [sys.executable, "-m", "pytest", "-q", target], REPO, PYTEST_TIMEOUT_S, ctx.out / log
    )
    summary = _last_line(done.stdout)
    if done.returncode == 0:
        return "PASS", f"pytest {target}: {summary}"
    return "FAIL", f"pytest {target} exit {done.returncode}: {summary}"


def _line_python_tests(ctx: _Ctx) -> Outcome:
    return _pytest(ctx, "workshop", "python-tests.log")


def _line_contracts(ctx: _Ctx) -> Outcome:
    return _pytest(ctx, "contracts", "contracts.log")


def _want_build(ctx: _Ctx, apks: list[Path]) -> bool:
    return ctx.build == "always" or (
        ctx.build == "if-missing" and not all(a.exists() for a in apks)
    )


def _check_apks(ctx: _Ctx, apks: list[Path]) -> Outcome | None:
    missing = [_rel(a) for a in apks if not a.exists()]
    if missing:
        hint = " (run without --build never, or build first)" if ctx.build == "never" else ""
        return "FAIL", f"APK missing: {', '.join(missing)}{hint}"
    return None


def _line_build_guard(ctx: _Ctx) -> Outcome:
    apks = [GUARD_APK, TESTFEED_APK]
    built = _want_build(ctx, apks)
    if built:
        gradlew = GUARD_DIR / ("gradlew.bat" if os.name == "nt" else "gradlew")
        cmd = [str(gradlew), "--no-daemon", ":app:assembleDebug", ":testfeed:assembleDebug"]
        done = _run_cmd(cmd, GUARD_DIR, BUILD_TIMEOUT_S, ctx.out / "build-guard.log")
        if done.returncode != 0:
            return "FAIL", f"gradle exit {done.returncode} (see build-guard.log)"
    problem = _check_apks(ctx, apks)
    if problem:
        return problem
    how = "built" if built else "present, build skipped"
    return "PASS", f"{how}: app-debug.apk {_mb(GUARD_APK)}, testfeed-debug.apk {_mb(TESTFEED_APK)}"


def _line_build_console(ctx: _Ctx) -> Outcome:
    apks = [CONSOLE_APK]
    built = _want_build(ctx, apks)
    if built:
        flutter = shutil.which("flutter")
        if flutter is None:
            return "FAIL", "flutter not found on PATH (load the toolchain with tools/env.ps1)"
        done = _run_cmd(
            [flutter, "build", "apk", "--debug"],
            CONSOLE_DIR,
            BUILD_TIMEOUT_S,
            ctx.out / "build-console.log",
        )
        if done.returncode != 0:
            return "FAIL", f"flutter build exit {done.returncode} (see build-console.log)"
    problem = _check_apks(ctx, apks)
    if problem:
        return problem
    how = "built" if built else "present, build skipped"
    return "PASS", f"{how}: console app-debug.apk {_mb(CONSOLE_APK)}"


def _line_adb(ctx: _Ctx) -> Outcome:
    status, detail, _ = _device(ctx)
    return status, detail


def _line_scrcpy(ctx: _Ctx) -> Outcome:
    serial, skip = _need_device(ctx)
    if skip or serial is None:
        return skip or ("SKIP", NO_PHONE)
    scrcpy, ffprobe = shutil.which("scrcpy"), shutil.which("ffprobe")
    if not scrcpy or not ffprobe:
        return "FAIL", "scrcpy or ffprobe not found on PATH (load the toolchain with tools/env.ps1)"
    video = ctx.out / "scrcpy.mp4"
    video.unlink(missing_ok=True)
    cmd = [
        scrcpy,
        "--serial",
        serial,
        "--no-window",
        "--no-audio",
        f"--record={video}",
        "--time-limit=5",
    ]
    done = _run_cmd(cmd, REPO, DEFAULT_TIMEOUT_S, ctx.out / "scrcpy.txt", hide=serial)
    if done.returncode != 0 or not video.exists():
        return "FAIL", f"scrcpy exit {done.returncode}: {_last_line(done.stderr or done.stdout)}"
    probe = [
        ffprobe,
        "-v",
        "error",
        "-show_entries",
        "format=duration",
        "-of",
        "default=nw=1:nk=1",
        str(video),
    ]
    timing = _run_cmd(probe, REPO, DEFAULT_TIMEOUT_S, ctx.out / "ffprobe.txt")
    try:
        seconds = float(timing.stdout.strip().splitlines()[0])
    except (IndexError, ValueError):
        return "FAIL", "ffprobe could not read the recording's duration"
    if seconds < 3.0:
        return "FAIL", f"recording lasts {seconds:.1f} s, need at least 3.0 s"
    return "PASS", f"recorded {seconds:.1f} s of the phone screen"


def _wake(serial: str) -> None:
    adb.keyevent(serial, "KEYCODE_WAKEUP")
    adb.keyevent(serial, "82")


def _apk_problem(apk: Path) -> Outcome | None:
    if not apk.exists():
        return "FAIL", f"APK missing: {_rel(apk)} (run without --only, or build first)"
    return None


def _installed_text(result: str) -> str:
    return "installed (unchanged)" if result == "unchanged" else "installed (updated)"


def _line_guard_app(ctx: _Ctx) -> Outcome:
    serial, skip = _need_device(ctx)
    if skip or serial is None:
        return skip or ("SKIP", NO_PHONE)
    problem = _apk_problem(GUARD_APK)
    if problem:
        return problem
    _wake(serial)
    result = adb.install_if_changed(serial, GUARD_APK, "com.veil.guard", force=ctx.reinstall)
    adb.force_stop(serial, "com.veil.guard")
    adb.logcat_clear(serial)
    adb.launch(serial, "com.veil.guard/.MainActivity")
    hello = None
    deadline = time.monotonic() + HELLO_WAIT_S
    while time.monotonic() < deadline:
        hello = parse.parse_hello_line(adb.logcat_dump(serial, ["VeilHello:I"]))
        if hello:
            break
        time.sleep(0.5)
    adb.screencap(serial, ctx.out / "guard.png")
    if not hello:
        return "FAIL", f"no VEIL_HELLO line in logcat within {HELLO_WAIT_S} s"
    profile = device_profile.load_profile_json(PROFILE_MD)
    if profile is None:
        return "FAIL", "docs/device-profile.md is PENDING: run device_profile --write"
    ram, expected_ram = hello.get("ramTotalBytes", 0), profile["ramTotalBytes"]
    wrong = [
        key for key in ("socModel", "androidRelease", "sdkInt") if hello.get(key) != profile[key]
    ]
    if abs(ram - expected_ram) / expected_ram > RAM_TOLERANCE:
        wrong.append("ramTotalBytes")
    if wrong:
        return "FAIL", f"live values differ from docs/device-profile.md: {', '.join(wrong)}"
    return "PASS", (
        f"{_installed_text(result)}; live soc={hello['socModel']} "
        f"android={hello['androidRelease']}/"
        f"API {hello['sdkInt']} ram={ram / 2**30:.1f} GiB match docs/device-profile.md"
    )


def _line_console_app(ctx: _Ctx) -> Outcome:
    serial, skip = _need_device(ctx)
    if skip or serial is None:
        return skip or ("SKIP", NO_PHONE)
    problem = _apk_problem(CONSOLE_APK)
    if problem:
        return problem
    _wake(serial)
    result = adb.install_if_changed(serial, CONSOLE_APK, "com.veil.console", force=ctx.reinstall)
    adb.force_stop(serial, "com.veil.console")
    adb.launch(serial, "com.veil.console/.MainActivity")
    resumed = None
    deadline = time.monotonic() + CONSOLE_WAIT_S
    while time.monotonic() < deadline:
        resumed = adb.resumed_activity(serial)
        if resumed and "com.veil.console" in resumed:
            break
        time.sleep(0.5)
    adb.screencap(serial, ctx.out / "console.png")
    if not resumed or "com.veil.console" not in resumed:
        return (
            "FAIL",
            f"console app is not in the foreground after {CONSOLE_WAIT_S} s (resumed: {resumed})",
        )
    return "PASS", f"{_installed_text(result)}; resumed activity {resumed}"


def _line_testfeed(ctx: _Ctx) -> Outcome:
    serial, skip = _need_device(ctx)
    if skip or serial is None:
        return skip or ("SKIP", NO_PHONE)
    problem = _apk_problem(TESTFEED_APK)
    if problem:
        return problem
    _wake(serial)
    result = adb.install_if_changed(serial, TESTFEED_APK, "com.veil.testfeed", force=ctx.reinstall)
    adb.force_stop(serial, "com.veil.testfeed")  # so onCreate truncates the log
    adb.launch(serial, "com.veil.testfeed/.FeedActivity")
    time.sleep(2)
    drive.scroll(serial, times=3)
    adb.screencap(serial, ctx.out / "testfeed.png")
    adb.keyevent(serial, "KEYCODE_HOME")  # onPause flushes the log
    time.sleep(1)
    data = adb.run_as_cat(serial, "com.veil.testfeed", "files/feedlog.jsonl")
    (ctx.out / "feedlog.jsonl").write_bytes(data)
    summary = testfeed.parse_feed_log(data.decode("utf-8", "replace"))
    ok, why = testfeed.scroll_check(summary, adb.screen_size(serial)[1])
    if not ok:
        return "FAIL", f"scroll check failed: {why}"
    return "PASS", f"{_installed_text(result)}; {why}"


def _line_aihub_devices(ctx: _Ctx) -> Outcome:
    status, detail, names = _hub_names(ctx)
    if names:
        (ctx.out / "aihub-devices.txt").write_text("\n".join(names) + "\n", encoding="utf-8")
    return status, detail


def _line_aihub_profile(ctx: _Ctx) -> Outcome:
    status, detail, names = _hub_names(ctx)
    if status == "SKIP":  # --skip-cloud, or AI Hub not configured: same reason as aihub-devices
        return "SKIP", detail
    if status == "FAIL":
        return "SKIP", "aihub-devices did not PASS"
    info = aihub.tiny_profile(names[0], ctx.out, AIHUB_TIMEOUT_S)
    (ctx.out / "aihub-profile.json").write_text(json.dumps(info, indent=2), encoding="utf-8")
    micros = info.get("estimatedInferenceTimeUs", 0)
    if not micros or micros <= 0:
        return "FAIL", "AI Hub returned no estimated inference time"
    return (
        "PASS",
        f"device={info['device']} estimatedInferenceTimeUs={micros} "
        f"runtime={info['targetRuntime']}",
    )


def _line_huggingface(ctx: _Ctx) -> Outcome:
    if ctx.skip_cloud:
        return "SKIP", "--skip-cloud"
    path = hf.anonymous_probe()
    token = "configured" if hf.token_configured() else "not configured (optional)"
    size = Path(path).stat().st_size
    return (
        "PASS",
        f"anonymous download of {hf.PROBE_REPO}/{hf.PROBE_FILE} ok ({size} bytes); token: {token}",
    )


LINES: dict[str, Callable[[_Ctx], Outcome]] = {
    "toolchain": _line_toolchain,
    "python-tests": _line_python_tests,
    "contracts": _line_contracts,
    "build-guard": _line_build_guard,
    "build-console": _line_build_console,
    "adb": _line_adb,
    "scrcpy": _line_scrcpy,
    "guard-app": _line_guard_app,
    "console-app": _line_console_app,
    "testfeed": _line_testfeed,
    "aihub-devices": _line_aihub_devices,
    "aihub-profile": _line_aihub_profile,
    "huggingface": _line_huggingface,
}


def _run_line(ctx: _Ctx, line_id: str) -> LineResult:
    started = time.monotonic()
    try:
        status, detail = LINES[line_id](ctx)
    except subprocess.TimeoutExpired as exc:
        status, detail = "FAIL", f"timed out after {exc.timeout:g} s"
    except Exception as exc:
        status, detail = "FAIL", f"{type(exc).__name__}: {exc}"
    return LineResult(line_id, status, _ascii(detail), round(time.monotonic() - started, 1))


def _format(result: LineResult) -> str:
    return f"[{result.status}] {result.id:<14} {result.detail}"


def _parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(prog="bench_check", description=__doc__.split("\n")[0])
    parser.add_argument(
        "--out", help="output folder (default data/evidence/1.1/bench-<timestamp>/)"
    )
    parser.add_argument("--build", choices=["if-missing", "always", "never"], default="if-missing")
    parser.add_argument(
        "--skip-phone", action="store_true", help="skip every line that needs the phone"
    )
    parser.add_argument("--skip-cloud", action="store_true", help="skip AI Hub and Hugging Face")
    parser.add_argument("--only", help="comma-separated line ids to run: " + ", ".join(LINE_IDS))
    parser.add_argument("--serial", help="adb serial when several devices are attached")
    parser.add_argument(
        "--reinstall", action="store_true", help="install the apps even if unchanged"
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    wanted = list(LINE_IDS)
    if args.only:
        chosen = [part.strip() for part in args.only.split(",") if part.strip()]
        unknown = [part for part in chosen if part not in LINE_IDS]
        if unknown:
            print(f"unknown line id(s): {', '.join(unknown)}; valid: {', '.join(LINE_IDS)}")
            return 1
        wanted = [line_id for line_id in LINE_IDS if line_id in chosen]
    out = (
        Path(args.out)
        if args.out
        else REPO / "data" / "evidence" / "1.1" / f"bench-{datetime.now():%Y%m%d-%H%M%S}"
    )
    out.mkdir(parents=True, exist_ok=True)
    ctx = _Ctx(out, args.build, args.skip_phone, args.skip_cloud, args.serial, args.reinstall)

    started = datetime.now().isoformat(timespec="seconds")
    results: list[LineResult] = []
    with (out / "bench-check.txt").open(
        "w", encoding="ascii", errors="replace", newline="\n"
    ) as report:

        def emit(text: str) -> None:
            print(text, flush=True)
            report.write(text + "\n")
            report.flush()

        for line_id in wanted:
            result = _run_line(ctx, line_id)
            results.append(result)
            emit(_format(result))
        counts = {s: sum(1 for r in results if r.status == s) for s in ("PASS", "FAIL", "SKIP")}
        emit(f"RESULT: {counts['PASS']} PASS, {counts['FAIL']} FAIL, {counts['SKIP']} SKIP")

    exit_code = 1 if counts["FAIL"] else (2 if counts["SKIP"] else 0)
    summary = {
        "startedAt": started,
        "build": args.build,
        "lines": [asdict(r) for r in results],
        "result": {"pass": counts["PASS"], "fail": counts["FAIL"], "skip": counts["SKIP"]},
        "exitCode": exit_code,
    }
    (out / "bench-check.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
