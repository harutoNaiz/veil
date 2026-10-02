from __future__ import annotations

from pathlib import Path

from workshop.bench import testfeed

FIX = Path(__file__).parent / "fixtures" / "sm8850"
SCREEN_H = 3168


def read(name: str) -> str:
    return (FIX / name).read_text(encoding="utf-8")


def test_scroll_check_passes_on_a_feed_that_scrolled() -> None:
    summary = testfeed.parse_feed_log(read("feedlog-ok.jsonl"))
    assert summary.has_session
    assert summary.frames == 40
    assert summary.max_scroll_y == 3300
    assert summary.first_visible_start == "item-000"
    assert summary.first_visible_end == "item-003"
    assert summary.taps == 1
    ok, why = testfeed.scroll_check(summary, SCREEN_H)
    assert ok, why


def test_scroll_check_fails_on_a_feed_that_did_not_scroll() -> None:
    summary = testfeed.parse_feed_log(read("feedlog-noscroll.jsonl"))
    assert summary.frames == 3
    assert summary.max_scroll_y == 0
    ok, why = testfeed.scroll_check(summary, SCREEN_H)
    assert not ok
    assert "only 3 frames" in why
    assert "max scrollY 0" in why
    assert "never changed" in why


def test_scroll_check_needs_a_session_line() -> None:
    lines = [
        line for line in read("feedlog-ok.jsonl").splitlines() if '"type":"session"' not in line
    ]
    ok, why = testfeed.scroll_check(testfeed.parse_feed_log("\n".join(lines)), SCREEN_H)
    assert not ok
    assert "no session line" in why


def test_scroll_check_needs_enough_distance() -> None:
    summary = testfeed.parse_feed_log(read("feedlog-ok.jsonl"))
    ok, why = testfeed.scroll_check(summary, 5000)  # 0.8 * 5000 = 4000 > 3300
    assert not ok
    assert "80%" in why


def test_parse_feed_log_skips_a_cut_off_last_line() -> None:
    text = read("feedlog-ok.jsonl") + '{"type":"frame","tMs":1,"scrollY":99'
    assert testfeed.parse_feed_log(text).frames == 40
    assert testfeed.parse_feed_log("") == testfeed.FeedSummary(0, 0, None, None, 0, False)
