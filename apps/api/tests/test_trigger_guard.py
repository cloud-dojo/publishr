"""手動トリガーのガード（許可uid・レート制限・実行中ロック）テスト。

時刻は注入（now 引数）して決定的に検証する。
"""

from __future__ import annotations

import pytest
from publishr_api.services.trigger_guard import TriggerError, TriggerGuard


def test_allows_when_allowlist_empty():
    """allowlist 空 = dev（全許可）。acquire→release が通る。"""
    g = TriggerGuard(min_interval_sec=10.0, allowed_uids=[])
    g.acquire("uid_x", now=0.0)
    g.release("uid_x", now=1.0)


def test_rejects_uid_not_in_allowlist():
    g = TriggerGuard(min_interval_sec=10.0, allowed_uids=["uid_ok"])
    with pytest.raises(TriggerError) as ei:
        g.acquire("uid_ng", now=0.0)
    assert ei.value.status == 403


def test_allows_uid_in_allowlist():
    g = TriggerGuard(min_interval_sec=10.0, allowed_uids=["uid_ok"])
    g.acquire("uid_ok", now=0.0)  # 例外が出なければ通過


def test_already_running_conflicts():
    g = TriggerGuard(min_interval_sec=10.0, allowed_uids=[])
    g.acquire("uid_x", now=0.0)  # 取得したまま release しない
    with pytest.raises(TriggerError) as ei:
        g.acquire("uid_x", now=1.0)
    assert ei.value.status == 409


def test_rate_limited_within_interval():
    g = TriggerGuard(min_interval_sec=10.0, allowed_uids=[])
    g.acquire("uid_x", now=0.0)
    g.release("uid_x", now=1.0)
    with pytest.raises(TriggerError) as ei:
        g.acquire("uid_x", now=5.0)  # 直近 release から 10秒未満
    assert ei.value.status == 429


def test_allows_after_interval_elapsed():
    g = TriggerGuard(min_interval_sec=10.0, allowed_uids=[])
    g.acquire("uid_x", now=0.0)
    g.release("uid_x", now=1.0)
    g.acquire("uid_x", now=20.0)  # 間隔経過後は再取得可


def test_rate_limit_is_per_uid():
    g = TriggerGuard(min_interval_sec=10.0, allowed_uids=[])
    g.acquire("uid_a", now=0.0)
    g.release("uid_a", now=1.0)
    # 別 uid は影響を受けない。
    g.acquire("uid_b", now=2.0)
    g.release("uid_b", now=3.0)


def test_reset_clears_state():
    g = TriggerGuard(min_interval_sec=10.0, allowed_uids=[])
    g.acquire("uid_x", now=0.0)
    g.reset()
    # reset 後は running も last も消えるので即 acquire 可。
    g.acquire("uid_x", now=0.5)
