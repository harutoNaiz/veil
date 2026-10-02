from __future__ import annotations

from pathlib import Path

import pytest

from workshop.bench import parse

FIX = Path(__file__).parent / "fixtures" / "sm8850"


def read(name: str) -> str:
    return (FIX / name).read_text(encoding="utf-8")


def test_parse_devices_variants() -> None:
    assert parse.parse_devices(read("devices-none.txt")) == []
    assert parse.parse_devices(read("devices-one.txt")) == [("SYNTHETICSERIAL01", "device")]
    assert parse.parse_devices(read("devices-unauthorized.txt")) == [
        ("SYNTHETICSERIAL01", "unauthorized")
    ]
    assert parse.parse_devices(read("devices-two.txt")) == [
        ("SYNTHETICSERIAL01", "device"),
        ("SYNTHETICSERIAL02", "device"),
    ]


def test_parse_getprop() -> None:
    props = parse.parse_getprop(read("getprop.txt"))
    assert props["ro.soc.model"] == "SM8850"
    assert props["ro.product.model"] == "SYNTHETIC-IQOO15"
    assert props["ro.vivo.os.version"] == "6.0"
    assert parse.parse_getprop("garbage\n[a]: [b c]\n[empty]: []") == {"a": "b c", "empty": ""}


def test_parse_wm_size_and_density() -> None:
    assert parse.parse_wm_size(read("wm-size.txt")) == (1440, 3168)
    assert parse.parse_wm_size("Physical size: 1440x3168\nOverride size: 1080x2376\n") == (
        1080,
        2376,
    )
    assert parse.parse_wm_density(read("wm-density.txt")) == 510
    assert parse.parse_wm_density("Physical density: 510\nOverride density: 420\n") == 420
    with pytest.raises(ValueError):
        parse.parse_wm_size("nothing here")
    with pytest.raises(ValueError):
        parse.parse_wm_density("nothing here")


def test_parse_meminfo() -> None:
    assert parse.parse_meminfo_total_bytes(read("meminfo.txt")) == 15728640 * 1024
    with pytest.raises(ValueError):
        parse.parse_meminfo_total_bytes("MemFree: 1 kB")


def test_parse_refresh_rates() -> None:
    assert parse.parse_refresh_rates(read("dumpsys-display-modes.txt")) == [
        60.0,
        90.0,
        120.0,
        144.0,
    ]
    assert parse.parse_refresh_rates("no rates") == []


def test_parse_resumed_activity() -> None:
    assert parse.parse_resumed_activity(read("activities.txt")) == "com.veil.console/.MainActivity"
    only_m = "  mResumedActivity: ActivityRecord{abc u0 com.veil.guard/.MainActivity t3}\n"
    assert parse.parse_resumed_activity(only_m) == "com.veil.guard/.MainActivity"
    assert parse.parse_resumed_activity("") is None


def test_parse_hello_line_takes_the_last_one() -> None:
    hello = parse.parse_hello_line(read("logcat-hello.txt"))
    assert hello is not None
    assert hello["socModel"] == "SM8850"
    assert hello["sdkInt"] == 36
    assert hello["refreshRatesHz"] == [60.0, 90.0, 120.0, 144.0]
    assert parse.parse_hello_line("no marker here") is None
    assert parse.parse_hello_line("I VeilHello: VEIL_HELLO {not json") is None
    assert parse.parse_hello_line("VEIL_HELLO [1, 2]") is None


def test_marketing_ram_gb() -> None:
    assert parse.marketing_ram_gb(15728640 * 1024) == 16
    assert parse.marketing_ram_gb(8 * 2**30) == 8
    assert parse.marketing_ram_gb(8 * 2**30 + 1) == 12
    assert parse.marketing_ram_gb(100 * 2**30) == 32


def test_chip_family_match() -> None:
    assert parse.chip_family_match("SM8850", "")
    assert parse.chip_family_match("sm8850-ac", "")
    assert parse.chip_family_match("", "canoe")
    assert not parse.chip_family_match("SM8750", "sun")
    assert not parse.chip_family_match("", "")


def test_detect_os_skin() -> None:
    assert parse.detect_os_skin(parse.parse_getprop(read("getprop.txt"))) == ("OriginOS", "6.0")
    assert parse.detect_os_skin({"ro.build.display.id": "Funtouch OS_15.0"}) == (
        "Funtouch OS",
        "15.0",
    )
    assert parse.detect_os_skin({"x": "originOS 6.1.2 beta"}) == ("OriginOS", "6.1.2")
    assert parse.detect_os_skin({"x": "OriginOS"}) == ("OriginOS", "unknown")
    assert parse.detect_os_skin({"ro.build.display.id": "plain android"}) == ("unknown", "unknown")


def test_filter_props_keeps_only_the_allowlist() -> None:
    raw = parse.parse_getprop(read("getprop.txt"))
    kept = parse.filter_props(raw)
    assert kept == parse.parse_getprop(read("getprop-filtered.txt"))
    assert "ro.serialno" not in kept
    assert "ro.boot.serialno" not in kept
    assert "persist.sys.timezone" not in kept
    assert not any("serial" in key for key in kept)
    assert not any("SERIAL" in value for value in kept.values())


def test_filter_props_keeps_skin_keys_and_values_but_not_identifiers() -> None:
    props = {
        "ro.vivo.rom.version": "rom_15",
        "ro.iqoo.os.name": "x",
        "ro.vivo.serialno": "SECRET",
        "ro.vivo.os.imei": "SECRET",
        "persist.whatever": "OriginOS 6",
        "persist.other": "unrelated",
    }
    assert parse.filter_props(props) == {
        "ro.vivo.rom.version": "rom_15",
        "ro.iqoo.os.name": "x",
        "persist.whatever": "OriginOS 6",
    }
