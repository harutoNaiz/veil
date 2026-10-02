"""Optional helper for the Human sitting: enable the Guard's do-nothing probe service over adb.

    python -m workshop.bench.a11y_probe status
    python -m workshop.bench.a11y_probe enable      (adds the probe; keeps every other entry)
    python -m workshop.bench.a11y_probe disable     (removes only the probe)

`enable` first saves the two settings it changes to data/evidence/1.1/a11y-before.txt (unless
the probe is already enabled), and `disable` restores them exactly when the list would become
empty. Nothing here runs during the build or the bench check. On a phone that blocks this
(restricted settings), enable the service by hand: App info -> menu -> Allow restricted
settings, then Settings -> Accessibility.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from workshop.bench import adb

PROBE = "com.veil.guard/com.veil.guard.probe.ProbeAccessibilityService"
BEFORE_FILE = Path(__file__).resolve().parents[2] / "data" / "evidence" / "1.1" / "a11y-before.txt"
_LIST_KEY = "enabled_accessibility_services"
_FLAG_KEY = "accessibility_enabled"


def split_services(value: str) -> list[str]:
    """The colon-separated list from settings; "null" and "" mean empty."""
    value = value.strip()
    return [] if value in ("", "null") else [item for item in value.split(":") if item]


def add_service(value: str, probe: str = PROBE) -> str:
    items = split_services(value)
    if probe not in items:
        items.append(probe)
    return ":".join(items)


def remove_service(value: str, probe: str = PROBE) -> str:
    return ":".join(item for item in split_services(value) if item != probe)


def _get(serial: str, key: str) -> str:
    return adb.shell(serial, f"settings get secure {key}").strip()


def _put(serial: str, key: str, value: str) -> None:
    if value == "null":
        adb.shell(serial, f"settings delete secure {key}")
    else:
        adb.shell(serial, f"settings put secure {key} {value}")


def _save_before(serial: str) -> None:
    """Save the two settings as they are now, unless the probe is already enabled."""
    current = _get(serial, _LIST_KEY)
    if PROBE in split_services(current):
        return
    BEFORE_FILE.parent.mkdir(parents=True, exist_ok=True)
    BEFORE_FILE.write_text(
        f"{_LIST_KEY}={current}\n{_FLAG_KEY}={_get(serial, _FLAG_KEY)}\n", "utf-8"
    )


def _load_before() -> dict[str, str]:
    saved: dict[str, str] = {}
    if BEFORE_FILE.exists():
        for line in BEFORE_FILE.read_text(encoding="utf-8").splitlines():
            key, _, value = line.partition("=")
            saved[key] = value
    return saved


def status(serial: str) -> int:
    current = _get(serial, _LIST_KEY)
    print(f"{_LIST_KEY} = {current}")
    print(f"{_FLAG_KEY} = {_get(serial, _FLAG_KEY)}")
    print(f"probe in enabled list: {PROBE in split_services(current)}")
    bound = PROBE.split("/")[1] in adb.shell(serial, "dumpsys accessibility", timeout=60)
    print(f"probe appears in `dumpsys accessibility`: {bound}")
    return 0


def enable(serial: str) -> int:
    _save_before(serial)
    _put(serial, _LIST_KEY, add_service(_get(serial, _LIST_KEY)))
    _put(serial, _FLAG_KEY, "1")
    return status(serial)


def disable(serial: str) -> int:
    remaining = remove_service(_get(serial, _LIST_KEY))
    if remaining:
        _put(serial, _LIST_KEY, remaining)
    else:
        before = _load_before()
        _put(serial, _LIST_KEY, "null")
        _put(serial, _FLAG_KEY, before.get(_FLAG_KEY, "0"))
        if before.get(_LIST_KEY, "null") != "null":
            _put(serial, _LIST_KEY, before[_LIST_KEY])
    return status(serial)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="workshop.bench.a11y_probe", description=__doc__.split("\n")[0]
    )
    parser.add_argument("command", choices=["status", "enable", "disable"])
    parser.add_argument("--serial")
    args = parser.parse_args(argv)
    try:
        serial = args.serial or adb.single_device()
        if serial is None:
            print("no adb device (connect the phone: HC-002)")
            return 3
        return {"status": status, "enable": enable, "disable": disable}[args.command](serial)
    except adb.MultipleDevicesError as exc:
        print(str(exc))
        return 4
    except adb.AdbError as exc:
        print(f"adb error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
