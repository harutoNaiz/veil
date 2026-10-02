"""Pure parsers for adb output. No I/O here, so every function is unit-tested with fixtures."""

from __future__ import annotations

import json
import re

# Properties that are safe to keep in the device profile and in saved evidence.
# Serial numbers are never listed.
ALLOWED_PROPS: tuple[str, ...] = (
    "ro.soc.model",
    "ro.soc.manufacturer",
    "ro.board.platform",
    "ro.hardware",
    "ro.product.board",
    "ro.product.manufacturer",
    "ro.product.brand",
    "ro.product.model",
    "ro.product.device",
    "ro.product.name",
    "ro.build.version.release",
    "ro.build.version.sdk",
    "ro.build.version.security_patch",
    "ro.build.display.id",
    "ro.build.id",
    "ro.build.version.incremental",
    "ro.build.fingerprint",
)
SKIN_KEY_RE = re.compile(r"^ro\.(vivo|iqoo)\.[a-z0-9_.]*(os|rom|version|name)[a-z0-9_.]*$", re.I)
# Keys that could identify the phone. They are dropped even when the rules above would keep them.
_IDENTIFYING_KEY_RE = re.compile(r"serial|imei|meid|macaddr|\.mac$|uuid|android_id|\.sn$", re.I)

_RAM_MARKETING_GB = (4, 6, 8, 12, 16, 18, 20, 24, 32)


def parse_devices(text: str) -> list[tuple[str, str]]:
    """Parse `adb devices` into [(serial, state)]; daemon messages and the header are skipped."""
    found: list[tuple[str, str]] = []
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("*") or line.lower().startswith("list of devices"):
            continue
        parts = line.split()
        if len(parts) >= 2:
            found.append((parts[0], parts[1]))
    return found


def parse_getprop(text: str) -> dict[str, str]:
    """Parse `adb shell getprop` lines of the form "[key]: [value]"."""
    props: dict[str, str] = {}
    for line in text.splitlines():
        match = re.match(r"^\[(.+?)\]: \[(.*)\]\s*$", line)
        if match:
            props[match.group(1)] = match.group(2)
    return props


def parse_wm_size(text: str) -> tuple[int, int]:
    """Screen size from `wm size`. "Override size" wins over "Physical size"."""
    override = re.search(r"Override size:\s*(\d+)x(\d+)", text)
    physical = re.search(r"Physical size:\s*(\d+)x(\d+)", text)
    match = override or physical
    if not match:
        raise ValueError("no 'Physical size: WxH' in wm size output")
    return int(match.group(1)), int(match.group(2))


def parse_wm_density(text: str) -> int:
    """Density in dpi from `wm density`. "Override density" wins over "Physical density"."""
    override = re.search(r"Override density:\s*(\d+)", text)
    physical = re.search(r"Physical density:\s*(\d+)", text)
    match = override or physical
    if not match:
        raise ValueError("no 'Physical density: N' in wm density output")
    return int(match.group(1))


def parse_meminfo_total_bytes(text: str) -> int:
    """`MemTotal: N kB` from /proc/meminfo, in bytes."""
    match = re.search(r"^MemTotal:\s*(\d+)\s*kB", text, re.M)
    if not match:
        raise ValueError("no MemTotal line in meminfo output")
    return int(match.group(1)) * 1024


def parse_refresh_rates(dumpsys_display: str) -> list[float]:
    """Unique, sorted refresh rates (Hz) from the `fps=` values of `dumpsys display`."""
    rates: set[float] = set()
    for value in re.findall(r"fps=([0-9.]+)", dumpsys_display):
        try:
            rates.add(float(value.rstrip(".")))
        except ValueError:
            continue
    return sorted(rates)


def parse_resumed_activity(text: str) -> str | None:
    """The resumed activity as "package/.Class" from `dumpsys activity activities`, or None."""
    for key in ("topResumedActivity", "mResumedActivity", "ResumedActivity"):
        match = re.search(rf"{key}[=:]\s*ActivityRecord\{{[0-9a-f]+ u\d+ (\S+)", text)
        if match:
            return match.group(1)
    return None


def parse_hello_line(logcat: str) -> dict | None:
    """The JSON after the last "VEIL_HELLO " in a logcat dump; None if absent or invalid."""
    marker = "VEIL_HELLO "
    index = logcat.rfind(marker)
    if index < 0:
        return None
    rest = logcat[index + len(marker) :].splitlines()
    if not rest:
        return None
    try:
        value = json.loads(rest[0].strip())
    except json.JSONDecodeError:
        return None
    return value if isinstance(value, dict) else None


def marketing_ram_gb(total_bytes: int) -> int:
    """The smallest marketing RAM size (GB) that holds `total_bytes` (the kernel reports less)."""
    for size in _RAM_MARKETING_GB:
        if size * 2**30 >= total_bytes:
            return size
    return _RAM_MARKETING_GB[-1]


def chip_family_match(soc_model: str, board_platform: str) -> bool:
    """True for the 8 Elite Gen 5 family: soc model SM8850*, or board platform "canoe"."""
    return soc_model.upper().startswith("SM8850") or board_platform == "canoe"


def detect_os_skin(props: dict[str, str]) -> tuple[str, str]:
    """(name, version) of the vendor skin, e.g. ("OriginOS", "6.0"); "unknown" if none."""
    name = "unknown"
    matched_value = ""
    for needle, label in (("originos", "OriginOS"), ("funtouch", "Funtouch OS")):
        for value in props.values():
            if needle in value.lower():
                name, matched_value = label, value
                break
        if name != "unknown":
            break
    if name == "unknown":
        return "unknown", "unknown"
    if props.get("ro.vivo.os.version"):
        return name, props["ro.vivo.os.version"]
    match = re.search(r"\d+(\.\d+)*", matched_value)
    return name, match.group(0) if match else "unknown"


def filter_props(props: dict[str, str]) -> dict[str, str]:
    """Keep allowlisted properties, vendor-skin keys and skin values. Never serials."""
    kept: dict[str, str] = {}
    for key, value in props.items():
        if _IDENTIFYING_KEY_RE.search(key):
            continue
        lowered = value.lower()
        if (
            key in ALLOWED_PROPS
            or SKIN_KEY_RE.match(key)
            or "originos" in lowered
            or "funtouch" in lowered
        ):
            kept[key] = value
    return kept
