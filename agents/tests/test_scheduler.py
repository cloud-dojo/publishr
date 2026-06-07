"""C1.7 自律トリガー（曜日別スケジュール）の決定的テスト。

Cloud Scheduler 週3回（水/土=本命・日=セレンディピティ）の判定ロジックを、隠れ時計を持たず
（now を引数で受ける）決定的に検証する。正本: docs/planning/wbs.md C1.7 / 構想 §6。
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from publishr_agents.scheduler import (
    is_run_day,
    next_run,
    theme_kind_for,
    theme_kind_for_weekday,
)

JST = timezone(timedelta(hours=9))


def _d(y, m, d, hh=6, mm=0):
    return datetime(y, m, d, hh, mm, tzinfo=JST)


# ── 曜日→themeKind ─────────────────────────────────────────
def test_theme_kind_by_weekday():
    # Python weekday: Mon=0..Sun=6
    assert theme_kind_for_weekday(2) == "honmei"        # 水
    assert theme_kind_for_weekday(5) == "honmei"        # 土
    assert theme_kind_for_weekday(6) == "serendipity"   # 日
    for wd in (0, 1, 3, 4):                              # 月火木金は起動しない
        assert theme_kind_for_weekday(wd) is None


def test_theme_kind_for_known_dates():
    # 2026-06-03=水, 06-06=土, 06-07=日, 06-08=月
    assert theme_kind_for(_d(2026, 6, 3)) == "honmei"
    assert theme_kind_for(_d(2026, 6, 6)) == "honmei"
    assert theme_kind_for(_d(2026, 6, 7)) == "serendipity"
    assert theme_kind_for(_d(2026, 6, 8)) is None


def test_is_run_day():
    assert is_run_day(_d(2026, 6, 3)) is True    # 水
    assert is_run_day(_d(2026, 6, 7)) is True     # 日
    assert is_run_day(_d(2026, 6, 8)) is False    # 月


# ── next_run（次の起動時刻・決定的）──────────────────────────
def test_next_run_from_monday():
    # 月 06-08 06:00 → 次は 水 06-10 06:00
    nr = next_run(_d(2026, 6, 8))
    assert nr == _d(2026, 6, 10)


def test_next_run_same_day_before_time():
    # 水 06-10 の 05:00（起動時刻前）→ 当日 06:00
    nr = next_run(_d(2026, 6, 10, 5, 0))
    assert nr == _d(2026, 6, 10, 6, 0)


def test_next_run_same_day_after_time():
    # 水 06-10 の 07:00（起動時刻後）→ 次は 土 06-13 06:00
    nr = next_run(_d(2026, 6, 10, 7, 0))
    assert nr == _d(2026, 6, 13)


def test_next_run_sunday_after_time_wraps_to_wed():
    # 日 06-07 07:00 → 次は 水 06-10 06:00
    nr = next_run(_d(2026, 6, 7, 7, 0))
    assert nr == _d(2026, 6, 10)
