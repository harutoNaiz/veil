"""Reads the phone's facts over adb, writes docs/device-profile.md and the target-chip check.

    python -m workshop.bench.device_profile [--write] [--docs-dir docs] [--evidence-dir DIR]
                                            [--serial S] [--from-dir DIR]

Without --write the markdown is printed. With --write it is saved to
<docs-dir>/device-profile.md and the "Target chip check" entry of <docs-dir>/decisions.md is
added or replaced. Exit codes: 0 ok, 3 no device, 4 several devices and no --serial, 1 any
other error. Only allowlisted properties are read; no serial numbers.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import asdict, dataclass
from datetime import UTC, date, datetime
from pathlib import Path

from workshop.bench import adb, parse

JSON_BEGIN = "<!-- DEVICE-PROFILE-JSON:BEGIN -->"
JSON_END = "<!-- DEVICE-PROFILE-JSON:END -->"
CHIP_BEGIN = "<!-- veil:target-chip:begin -->"
CHIP_END = "<!-- veil:target-chip:end -->"
CHIP_PLACEHOLDER_RE = re.compile(r"^<!-- The target-chip check .*-->[ \t]*(?=\r?$)", re.M)
CAPTURED_AT_FILE = "captured-at.txt"

RAW_FILES = {
    "getprop": "getprop-filtered.txt",
    "meminfo": "meminfo.txt",
    "wm_size": "wm-size.txt",
    "wm_density": "wm-density.txt",
    "display": "dumpsys-display-modes.txt",
}
_DISPLAY_LINE_RE = re.compile(r"fps=|refreshRate")
# `dumpsys display` lines that mention fps can also carry display identifiers; drop those fields.
_IDENTIFIER_FIELD_RE = re.compile(
    r'(uniqueId|address|serial\w*|deviceProductInfo)=("[^"]*"|\S+)', re.I
)
TARGET_SDK = 36


@dataclass(frozen=True)
class DeviceProfile:
    capturedAt: str
    socModel: str
    socManufacturer: str
    boardPlatform: str
    hardware: str
    chipFamilyMatch: bool
    manufacturer: str
    brand: str
    model: str
    device: str
    androidRelease: str
    sdkInt: int
    buildDisplay: str
    securityPatch: str
    fingerprint: str
    osSkinName: str
    osSkinVersion: str
    ramTotalBytes: int
    ramMarketingGb: int
    screenWidthPx: int
    screenHeightPx: int
    densityDpi: int
    refreshRatesHz: list[float]


def _build_profile(captured_at: str, raw: dict[str, str]) -> DeviceProfile:
    props = parse.parse_getprop(raw["getprop"])
    soc_model = props.get("ro.soc.model", "")
    platform = props.get("ro.board.platform", "")
    ram = parse.parse_meminfo_total_bytes(raw["meminfo"])
    width, height = parse.parse_wm_size(raw["wm_size"])
    skin_name, skin_version = parse.detect_os_skin(props)
    return DeviceProfile(
        capturedAt=captured_at,
        socModel=soc_model,
        socManufacturer=props.get("ro.soc.manufacturer", ""),
        boardPlatform=platform,
        hardware=props.get("ro.hardware", ""),
        chipFamilyMatch=parse.chip_family_match(soc_model, platform),
        manufacturer=props.get("ro.product.manufacturer", ""),
        brand=props.get("ro.product.brand", ""),
        model=props.get("ro.product.model", ""),
        device=props.get("ro.product.device", ""),
        androidRelease=props.get("ro.build.version.release", ""),
        sdkInt=int(props.get("ro.build.version.sdk", "0") or 0),
        buildDisplay=props.get("ro.build.display.id", ""),
        securityPatch=props.get("ro.build.version.security_patch", ""),
        fingerprint=props.get("ro.build.fingerprint", ""),
        osSkinName=skin_name,
        osSkinVersion=skin_version,
        ramTotalBytes=ram,
        ramMarketingGb=parse.marketing_ram_gb(ram),
        screenWidthPx=width,
        screenHeightPx=height,
        densityDpi=parse.parse_wm_density(raw["wm_density"]),
        refreshRatesHz=parse.parse_refresh_rates(raw["display"]),
    )


def collect(serial: str) -> tuple[DeviceProfile, dict[str, str]]:
    """Read the phone: the profile, and the raw texts keyed like RAW_FILES (already filtered)."""
    props = adb.getprop(serial)
    meminfo = adb.shell(serial, "cat /proc/meminfo")
    display_lines = []
    for line in adb.shell(serial, "dumpsys display", timeout=90).splitlines():
        if _DISPLAY_LINE_RE.search(line):
            display_lines.append(_IDENTIFIER_FIELD_RE.sub(r"\1=<removed>", line.strip()))
    raw = {
        "getprop": "".join(f"[{k}]: [{v}]\n" for k, v in parse.filter_props(props).items()),
        "meminfo": "".join(
            line + "\n" for line in meminfo.splitlines() if line.startswith("MemTotal:")
        ),
        "wm_size": adb.shell(serial, "wm size"),
        "wm_density": adb.shell(serial, "wm density"),
        "display": "".join(line + "\n" for line in display_lines),
    }
    return _build_profile(_now(), raw), raw


def from_dir(path: Path) -> tuple[DeviceProfile, dict[str, str]]:
    """Rebuild a profile from raw files saved earlier (or from the test fixtures)."""
    raw = {key: (path / name).read_text(encoding="utf-8") for key, name in RAW_FILES.items()}
    stamp = path / CAPTURED_AT_FILE
    if stamp.exists():
        captured_at = stamp.read_text(encoding="utf-8").strip()
    else:
        mtime = (path / RAW_FILES["getprop"]).stat().st_mtime
        captured_at = datetime.fromtimestamp(mtime, UTC).isoformat(timespec="seconds")
    return _build_profile(captured_at, raw), raw


def _now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


def _fmt_hz(rates: list[float]) -> str:
    return " / ".join(f"{r:g}" for r in rates) + " Hz" if rates else "unknown"


def render_markdown(p: DeviceProfile) -> str:
    """The text of docs/device-profile.md for a measured profile."""
    family = "YES" if p.chipFamilyMatch else "NO"
    rows = [
        ("Phone", f"{p.manufacturer} {p.brand} {p.model} (device {p.device})"),
        (
            "Chip",
            f"{p.socModel} ({p.socManufacturer}), platform {p.boardPlatform}, "
            f"hardware {p.hardware}; "
            f"8 Elite Gen 5 family: {family}",
        ),
        (
            "Android",
            f"{p.androidRelease} (API {p.sdkInt}), build {p.buildDisplay}, "
            f"security patch {p.securityPatch}",
        ),
        ("OS skin", f"{p.osSkinName} {p.osSkinVersion}"),
        ("RAM", f"{p.ramMarketingGb} GB (exact: {p.ramTotalBytes} bytes)"),
        ("Screen", f"{p.screenWidthPx} × {p.screenHeightPx} px, {p.densityDpi} dpi"),
        ("Refresh rates", _fmt_hz(p.refreshRatesHz)),
    ]
    lines = [
        "# Device profile",
        f"Status: MEASURED (captured {p.capturedAt} by workshop.bench.device_profile)",
        "",
        "| Item | Value |",
        "| --- | --- |",
        *[f"| {name} | {value} |" for name, value in rows],
        "",
        "Raw values (allowlisted properties only; no serial numbers) are saved in the phase "
        "evidence folder.",
        "",
        JSON_BEGIN,
        "```json",
        json.dumps(asdict(p), indent=2, ensure_ascii=False),
        "```",
        JSON_END,
        "",
    ]
    return "\n".join(lines)


def load_profile_json(md_path: Path) -> dict | None:
    """The JSON between the markers of a device-profile.md; None if it is `null` or missing."""
    if not md_path.exists():
        return None
    text = md_path.read_text(encoding="utf-8")
    match = re.search(
        re.escape(JSON_BEGIN) + r"\s*```json\s*(.*?)\s*```\s*" + re.escape(JSON_END), text, re.S
    )
    if not match:
        return None
    value = json.loads(match.group(1))
    return value if isinstance(value, dict) else None


def _chip_block(number: str, p: DeviceProfile, today: str, eol: str) -> str:
    if p.chipFamilyMatch:
        result = (
            f"Result: CONFIRMED - {p.socModel} (platform {p.boardPlatform}) is the "
            "Snapdragon 8 Elite Gen 5 "
            "family. Published speeds in PLAN.md apply."
        )
    else:
        result = (
            f"Result: FLAGGED - the phone reports {p.socModel} / {p.boardPlatform}, not the "
            "Snapdragon 8 Elite Gen 5 family (SM8850). Published speeds in PLAN.md may not "
            "apply; Chapter 3 must rely on "
            "measured numbers."
        )
    lines = [
        CHIP_BEGIN,
        f"## {number} · Target chip check",
        "",
        f"Date: {today} · Source: docs/device-profile.md",
        "",
        result,
        "",
        f"Phone runs Android API {p.sdkInt}; apps target API {TARGET_SDK}.",
    ]
    if p.sdkInt > TARGET_SDK:
        lines.append(
            f"Note: moving to targetSdk {p.sdkInt} needs platforms;android-{p.sdkInt} "
            "and AGP >= 9.1.1."
        )
    lines.append(CHIP_END)
    return eol.join(lines)


def update_decisions(decisions_md: Path, p: DeviceProfile, today: str) -> None:
    """Add or replace the "Target chip check" entry, keeping its D-NNN number on replacement.

    A first insert takes the next free number (D-004 when D-001..D-003 exist) and replaces the
    placeholder comment that docs/decisions.md ends with, or else is appended at the end.
    """
    text = "# Decisions\n"
    if decisions_md.exists():
        with decisions_md.open(
            encoding="utf-8", newline=""
        ) as handle:  # keep the file's line endings
            text = handle.read()
    eol = "\r\n" if "\r\n" in text else "\n"
    existing = re.search(re.escape(CHIP_BEGIN) + r".*?" + re.escape(CHIP_END), text, re.S)
    if existing:
        heading = re.search(r"^## (D-\d+)", existing.group(0), re.M)
        number = heading.group(1) if heading else _next_number(text)
        block = _chip_block(number, p, today, eol)
        text = text[: existing.start()] + block + text[existing.end() :]
    else:
        block = _chip_block(_next_number(text), p, today, eol)
        placeholder = CHIP_PLACEHOLDER_RE.search(text)
        if placeholder:
            text = text[: placeholder.start()] + block + text[placeholder.end() :]
        else:
            text = text.rstrip("\r\n") + eol + eol + block
    if not text.endswith(("\n", "\r")):
        text += eol
    decisions_md.parent.mkdir(parents=True, exist_ok=True)
    decisions_md.write_text(text, encoding="utf-8", newline="")


def _next_number(text: str) -> str:
    numbers = [int(n) for n in re.findall(r"^## D-(\d+)", text, re.M)]
    return f"D-{(max(numbers) if numbers else 0) + 1:03d}"


def _parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="workshop.bench.device_profile", description=__doc__.split("\n")[0]
    )
    parser.add_argument(
        "--write", action="store_true", help="write device-profile.md and update decisions.md"
    )
    parser.add_argument(
        "--docs-dir", default="docs", help="folder holding device-profile.md and decisions.md"
    )
    parser.add_argument("--evidence-dir", help="also save the raw (filtered) files here")
    parser.add_argument(
        "--serial", help="adb serial, needed only when several devices are attached"
    )
    parser.add_argument("--from-dir", help="read raw files from this folder instead of a phone")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    try:
        if args.from_dir:
            profile, raw = from_dir(Path(args.from_dir))
        else:
            serial = args.serial
            if not serial:
                attached = adb.devices()
                ready = [s for s, state in attached if state == "device"]
                if not ready:
                    hint = "; accept the USB debugging prompt on the phone" if attached else ""
                    print(f"no adb device (connect the phone: HC-002){hint}")
                    return 3
                if len(ready) > 1:
                    print(f"{len(ready)} adb devices attached; choose one with --serial")
                    return 4
                serial = ready[0]
            profile, raw = collect(serial)
    except adb.AdbError as exc:
        print(f"adb error: {exc}", file=sys.stderr)
        return 1
    except (OSError, ValueError, KeyError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    if args.evidence_dir:
        evidence = Path(args.evidence_dir)
        evidence.mkdir(parents=True, exist_ok=True)
        for key, name in RAW_FILES.items():
            (evidence / name).write_text(raw[key], encoding="utf-8", newline="\n")
        (evidence / CAPTURED_AT_FILE).write_text(
            profile.capturedAt + "\n", encoding="utf-8", newline="\n"
        )

    markdown = render_markdown(profile)
    if args.write:
        docs = Path(args.docs_dir)
        docs.mkdir(parents=True, exist_ok=True)
        (docs / "device-profile.md").write_text(markdown, encoding="utf-8", newline="\n")
        update_decisions(docs / "decisions.md", profile, date.today().isoformat())
        verdict = "CONFIRMED" if profile.chipFamilyMatch else "FLAGGED"
        print(f"wrote {docs / 'device-profile.md'}; decisions.md target chip check: {verdict}")
    else:
        print(markdown)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
