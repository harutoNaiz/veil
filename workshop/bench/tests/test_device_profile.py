from __future__ import annotations

import dataclasses
import json
from pathlib import Path

import pytest

from workshop.bench import adb, device_profile, parse

FIX = Path(__file__).parent / "fixtures" / "sm8850"

DECISIONS = """# Decisions

Numbered, newest last. Scripts may append entries between their own markers.

## D-001 · One

Date: 2026-10-02

## D-002 · Two

Date: 2026-10-02

## D-003 · Three

Date: 2026-10-02

<!-- The target-chip check (D-004 or later) is appended by workshop.bench.device_profile. -->
"""

PENDING = """# Device profile
Status: PENDING - the phone has not been connected yet (HC-002).

<!-- DEVICE-PROFILE-JSON:BEGIN -->
```json
null
```
<!-- DEVICE-PROFILE-JSON:END -->
"""


@pytest.fixture
def profile() -> device_profile.DeviceProfile:
    return device_profile.from_dir(FIX)[0]


def test_from_dir_builds_the_expected_profile(profile: device_profile.DeviceProfile) -> None:
    assert profile == device_profile.DeviceProfile(
        capturedAt="2026-10-02T00:00:00+00:00",
        socModel="SM8850",
        socManufacturer="QTI",
        boardPlatform="canoe",
        hardware="qcom",
        chipFamilyMatch=True,
        manufacturer="vivo",
        brand="iQOO",
        model="SYNTHETIC-IQOO15",
        device="synthetic_device",
        androidRelease="16",
        sdkInt=36,
        buildDisplay="SYNTHETIC.16.0.0.000",
        securityPatch="2026-09-01",
        fingerprint="vivo/synthetic_product/synthetic_device:16/SYNTH.000000.000/synthetic000:user/release-keys",
        osSkinName="OriginOS",
        osSkinVersion="6.0",
        ramTotalBytes=15728640 * 1024,
        ramMarketingGb=16,
        screenWidthPx=1440,
        screenHeightPx=3168,
        densityDpi=510,
        refreshRatesHz=[60.0, 90.0, 120.0, 144.0],
    )


def test_render_markdown_round_trips_through_load_profile_json(
    tmp_path: Path, profile: device_profile.DeviceProfile
) -> None:
    text = device_profile.render_markdown(profile)
    assert text.startswith(
        "# Device profile\nStatus: MEASURED (captured 2026-10-02T00:00:00+00:00 by "
    )
    assert "8 Elite Gen 5 family: YES" in text
    assert "OriginOS 6.0" in text
    assert "1440 × 3168 px, 510 dpi" in text
    assert "60 / 90 / 120 / 144 Hz" in text
    assert "no serial numbers" in text
    path = tmp_path / "device-profile.md"
    path.write_text(text, encoding="utf-8")
    assert device_profile.load_profile_json(path) == dataclasses.asdict(profile)


def test_load_profile_json_is_none_for_the_pending_template(tmp_path: Path) -> None:
    path = tmp_path / "device-profile.md"
    assert device_profile.load_profile_json(path) is None  # no file
    path.write_text(PENDING, encoding="utf-8")
    assert device_profile.load_profile_json(path) is None
    path.write_text("no markers", encoding="utf-8")
    assert device_profile.load_profile_json(path) is None


def test_update_decisions_inserts_replaces_and_flags(
    tmp_path: Path, profile: device_profile.DeviceProfile
) -> None:
    decisions = tmp_path / "decisions.md"
    decisions.write_text(DECISIONS, encoding="utf-8")
    device_profile.update_decisions(decisions, profile, "2026-10-03")
    text = decisions.read_text(encoding="utf-8")
    assert "## D-004 · Target chip check" in text
    assert "Date: 2026-10-03 · Source: docs/device-profile.md" in text
    assert (
        "Result: CONFIRMED - SM8850 (platform canoe) is the Snapdragon 8 Elite Gen 5 family. "
        "Published speeds in PLAN.md apply."
    ) in text
    assert "Phone runs Android API 36; apps target API 36." in text
    assert "Note: moving to targetSdk" not in text
    assert "is appended by workshop.bench.device_profile" not in text  # the placeholder was used up
    assert text.startswith(DECISIONS.split("<!-- The target-chip")[0])

    device_profile.update_decisions(decisions, profile, "2026-10-04")
    again = decisions.read_text(encoding="utf-8")
    assert again.count("Target chip check") == 1
    assert again.count("<!-- veil:target-chip:begin -->") == 1
    assert "Date: 2026-10-04" in again
    assert "2026-10-03" not in again.split("D-004")[1]

    other = dataclasses.replace(
        profile, socModel="SM8750", boardPlatform="sun", chipFamilyMatch=False, sdkInt=37
    )
    device_profile.update_decisions(decisions, other, "2026-10-05")
    flagged = decisions.read_text(encoding="utf-8")
    assert flagged.count("Target chip check") == 1
    assert "## D-004 · Target chip check" in flagged
    assert (
        "Result: FLAGGED - the phone reports SM8750 / sun, not the Snapdragon 8 Elite "
        "Gen 5 family (SM8850)."
    ) in flagged
    assert "Chapter 3 must rely on measured numbers." in flagged
    assert "Note: moving to targetSdk 37 needs platforms;android-37 and AGP >= 9.1.1." in flagged
    assert "CONFIRMED" not in flagged
    assert flagged.startswith(DECISIONS.split("<!-- The target-chip")[0])


def test_update_decisions_appends_without_placeholder_and_keeps_crlf(
    tmp_path: Path, profile: device_profile.DeviceProfile
) -> None:
    decisions = tmp_path / "decisions.md"
    decisions.write_bytes(b"# Decisions\r\n\r\n## D-001 \xc2\xb7 One\r\n\r\nText\r\n")
    device_profile.update_decisions(decisions, profile, "2026-10-03")
    raw = decisions.read_bytes()
    assert b"## D-002" in raw
    assert b"\n" not in raw.replace(b"\r\n", b"")  # every newline is still CRLF


def test_update_decisions_with_the_placeholder_keeps_crlf(
    tmp_path: Path, profile: device_profile.DeviceProfile
) -> None:
    decisions = tmp_path / "decisions.md"
    decisions.write_bytes(DECISIONS.replace("\n", "\r\n").encode("utf-8"))
    device_profile.update_decisions(decisions, profile, "2026-10-03")
    device_profile.update_decisions(decisions, profile, "2026-10-04")
    raw = decisions.read_bytes()
    assert b"is appended by workshop.bench.device_profile" not in raw
    assert raw.count(b"Target chip check") == 1
    assert b"\n" not in raw.replace(b"\r\n", b"")
    assert raw.endswith(b"<!-- veil:target-chip:end -->\r\n")


def test_main_from_dir_prints_markdown(capsys: pytest.CaptureFixture[str]) -> None:
    assert device_profile.main(["--from-dir", str(FIX)]) == 0
    out = capsys.readouterr().out
    assert "8 Elite Gen 5 family: YES" in out
    assert "OriginOS 6.0" in out


def test_main_write_updates_both_files_and_saves_evidence(tmp_path: Path) -> None:
    docs = tmp_path / "docs"
    docs.mkdir()
    (docs / "decisions.md").write_text(DECISIONS, encoding="utf-8")
    evidence = tmp_path / "evidence"
    argv = [
        "--from-dir",
        str(FIX),
        "--docs-dir",
        str(docs),
        "--evidence-dir",
        str(evidence),
        "--write",
    ]
    assert device_profile.main(argv) == 0
    assert device_profile.load_profile_json(docs / "device-profile.md")["socModel"] == "SM8850"
    assert "Target chip check" in (docs / "decisions.md").read_text(encoding="utf-8")
    for name in device_profile.RAW_FILES.values():
        assert (evidence / name).read_text(encoding="utf-8") == (FIX / name).read_text(
            encoding="utf-8"
        )
    # saved evidence can be turned back into the same profile
    assert device_profile.from_dir(evidence)[0].socModel == "SM8850"


def test_main_write_creates_decisions_when_the_folder_is_empty(tmp_path: Path) -> None:
    docs = tmp_path / "newdocs"
    assert device_profile.main(["--from-dir", str(FIX), "--docs-dir", str(docs), "--write"]) == 0
    assert "## D-001 · Target chip check" in (docs / "decisions.md").read_text(encoding="utf-8")


def test_main_without_a_phone_exits_3(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr(adb, "devices", lambda: [])
    assert device_profile.main([]) == 3
    assert "no adb device" in capsys.readouterr().out


def test_main_with_an_unauthorized_phone_exits_3(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr(adb, "devices", lambda: [("S1", "unauthorized")])
    assert device_profile.main([]) == 3
    assert "USB debugging prompt" in capsys.readouterr().out


def test_main_with_two_phones_and_no_serial_exits_4(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(adb, "devices", lambda: [("S1", "device"), ("S2", "device")])
    assert device_profile.main([]) == 4


def test_collect_filters_and_matches_the_fixture_profile(monkeypatch: pytest.MonkeyPatch) -> None:
    display = (
        'DisplayDeviceInfo{"Built-in Screen": uniqueId="local:4630946000000000001", fps=144.0, '
        "address=Physical{port=0}}\n"
        "    some unrelated line with SYNTHETIC-SERIAL-0000\n"
        "    mRefreshRate=144.0\n"
        "    DisplayModeRecord{mMode={id=1, fps=60.0}}\n"
        "    DisplayModeRecord{mMode={id=2, fps=90.0}}\n"
        "    DisplayModeRecord{mMode={id=3, fps=120.0}}\n"
    )
    meminfo = (
        "MemTotal:       15728640 kB\nMemFree:         1234 kB\nSerial: SYNTHETIC-SERIAL-0000\n"
    )
    answers = {
        "cat /proc/meminfo": meminfo,
        "wm size": (FIX / "wm-size.txt").read_text(encoding="utf-8"),
        "wm density": (FIX / "wm-density.txt").read_text(encoding="utf-8"),
        "dumpsys display": display,
    }
    full_props = parse.parse_getprop((FIX / "getprop.txt").read_text(encoding="utf-8"))
    monkeypatch.setattr(adb, "getprop", lambda serial: full_props)
    monkeypatch.setattr(adb, "shell", lambda serial, cmd, timeout=60: answers[cmd])
    profile, raw = device_profile.collect("SERIAL-NEVER-PRINTED")
    expected = device_profile.from_dir(FIX)[0]
    assert dataclasses.replace(profile, capturedAt=expected.capturedAt) == expected
    everything = json.dumps(raw)
    assert "SYNTHETIC-SERIAL" not in everything
    assert "SERIAL-NEVER-PRINTED" not in everything
    assert "uniqueId=<removed>" in raw["display"]
    assert "unrelated" not in raw["display"]
    assert raw["meminfo"] == "MemTotal:       15728640 kB\n"
