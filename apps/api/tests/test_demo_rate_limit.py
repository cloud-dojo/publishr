"""デモ公開ライブ生成レートガード（②G）の単体テスト。

グローバル日次上限・client 単位日次上限・日付リセット・無効化（上限0）を押さえる。
"""

from __future__ import annotations

import pytest

from publishr_api.services.demo_rate_limit import (
    DemoRateError,
    DemoRateLimiter,
    InMemoryDemoRateStore,
)

DAY = "2026-07-15"


def _limiter(global_cap: int = 7, per_client_cap: int = 3) -> DemoRateLimiter:
    return DemoRateLimiter(
        store=InMemoryDemoRateStore(),
        global_cap=global_cap,
        per_client_cap=per_client_cap,
    )


def test_allows_under_caps() -> None:
    lim = _limiter()
    lim.acquire("client-a", day=DAY)  # 例外が出なければ OK


def test_per_client_cap_blocks_4th_but_other_client_ok() -> None:
    lim = _limiter(global_cap=7, per_client_cap=3)
    for _ in range(3):
        lim.acquire("a", day=DAY)
    with pytest.raises(DemoRateError):
        lim.acquire("a", day=DAY)  # a の4回目は per-client 超過
    # 別 client はまだ枠がある（グローバルは 3/7）。
    lim.acquire("b", day=DAY)


def test_global_cap_blocks_8th_across_clients() -> None:
    lim = _limiter(global_cap=7, per_client_cap=99)
    for i in range(7):
        lim.acquire(f"c{i}", day=DAY)  # 7 client が1回ずつ＝global 7
    with pytest.raises(DemoRateError):
        lim.acquire("c7", day=DAY)  # 8回目は global 超過


def test_over_cap_does_not_consume_quota() -> None:
    # 超過リクエストでカウンタを増やさない＝拒否後も状態は据え置き。
    lim = _limiter(global_cap=1, per_client_cap=1)
    lim.acquire("a", day=DAY)
    with pytest.raises(DemoRateError):
        lim.acquire("b", day=DAY)  # global 超過
    with pytest.raises(DemoRateError):
        lim.acquire("b", day=DAY)  # 何度叩いても同じ（枠を消費しない）


def test_day_resets_counter() -> None:
    lim = _limiter(global_cap=1, per_client_cap=1)
    lim.acquire("a", day="2026-07-15")
    with pytest.raises(DemoRateError):
        lim.acquire("a", day="2026-07-15")
    lim.acquire("a", day="2026-07-16")  # 翌日は枠が戻る


def test_acquire_server_uses_global_cap_only() -> None:
    """client_id 無し（Scheduler/直叩き）は global のみ課す＝per-client 3 に縛られない。"""
    lim = _limiter(global_cap=5, per_client_cap=1)
    for _ in range(5):
        lim.acquire_server(day=DAY)
    with pytest.raises(DemoRateError):
        lim.acquire_server(day=DAY)  # 6回目は global 超過


def test_acquire_server_shares_global_with_clients() -> None:
    """server 消費分も global に合算される（別勘定にしない）。"""
    lim = _limiter(global_cap=2, per_client_cap=2)
    lim.acquire("a", day=DAY)
    lim.acquire_server(day=DAY)
    with pytest.raises(DemoRateError):
        lim.acquire("b", day=DAY)  # global 2 を使い切っている


def test_disabled_when_caps_zero() -> None:
    # 上限 0 以下は無効（全許可）＝ローカル/mock の従来挙動を壊さない。
    lim = _limiter(global_cap=0, per_client_cap=0)
    for _ in range(100):
        lim.acquire("a", day=DAY)  # いくら叩いても通る
    assert lim.enabled is False
