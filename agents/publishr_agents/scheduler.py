"""C1.7 自律トリガーのスケジュール判定（純粋・決定的）。

Cloud Scheduler 週3回（水/土=本命 honmei・日=セレンディピティ serendipity・各06:00 JST）の
曜日マッピングと次回起動時刻を、隠れ時計を持たず（now を引数で受ける）決定的に計算する。

本番は Cloud Scheduler の cron がこの曜日でトリガー（デプロイは別途・コスト発生）:
  honmei      : `0 6 * * 3,6`   （水・土 06:00／cron は 0=日..6=土）
  serendipity : `0 6 * * 0`     （日 06:00）
ローカル/デモは scripts/run_scheduler.py が同じ判定で mock 起動（課金ゼロ）。
"""

from __future__ import annotations

from datetime import datetime, timedelta
from typing import Optional

RUN_HOUR = 6  # 起動時刻（朝6時・現地）

# Python datetime.weekday(): Mon=0 .. Sun=6
_WEEKDAY_THEME: dict[int, str] = {
    2: "honmei",       # 水（本命）
    5: "honmei",       # 土（本命）
    6: "serendipity",  # 日（セレンディピティ）
}


def theme_kind_for_weekday(weekday: int) -> Optional[str]:
    """Python weekday(Mon=0..Sun=6) → themeKind（起動しない曜日は None）。"""
    return _WEEKDAY_THEME.get(weekday)


def theme_kind_for(now: datetime) -> Optional[str]:
    """その日の themeKind（起動日でなければ None）。"""
    return theme_kind_for_weekday(now.weekday())


def is_run_day(now: datetime) -> bool:
    """その日が起動日（水/土/日）か。"""
    return theme_kind_for(now) is not None


def next_run(now: datetime) -> datetime:
    """now 以降で最も近い起動時刻（水/土/日 の RUN_HOUR:00）を返す。

    当日が起動日かつ now が RUN_HOUR 前なら当日。そうでなければ次の起動曜日。
    """
    anchor = now.replace(hour=RUN_HOUR, minute=0, second=0, microsecond=0)
    if is_run_day(now) and now <= anchor:
        return anchor
    # 翌日以降で最初の起動曜日を探す（最大7日）。
    for offset in range(1, 8):
        day = (now + timedelta(days=offset)).replace(
            hour=RUN_HOUR, minute=0, second=0, microsecond=0
        )
        if is_run_day(day):
            return day
    raise RuntimeError("起動曜日が見つかりません（不変条件違反）")
