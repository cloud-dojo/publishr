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


def test_server_sentinel_is_not_firestore_reserved() -> None:
    """server バケットの client_id は Firestore の予約フィールド名（__.*__）に該当しない。

    Firestore の map キー/フィールド名は `__.*__` を予約しており、`__server__` を書くと
    本番トランザクションが InvalidArgument(400) で落ちる（Scheduler 経路が500になる）。
    """
    import re

    from publishr_api.services.demo_rate_limit import DemoRateLimiter

    assert not re.fullmatch(r"__.*__", DemoRateLimiter._SERVER_CLIENT_ID)


def test_firestore_safe_key_never_reserved() -> None:
    """Firestore ストアのキー安全化: 予約パターン `__.*__` を送っても安全なキーに包む。"""
    import re

    from publishr_api.services.demo_rate_limit import FirestoreDemoRateStore

    for cid in ("__server__", "__x__", "550e8400-e29b-41d4-a716-446655440000", "anon"):
        assert not re.fullmatch(r"__.*__", FirestoreDemoRateStore._safe_key(cid))


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


# ── フェイルセーフ cap（env ドリフト保険・②G P0ハードニング）─────────────────────
# 実課金(vertex)なのに PUBLISHR_DEMO_RATE_* が欠落したままデプロイされても、匿名ライブ生成が
# 無制限に実 Vertex を叩かないよう組込みの保守的上限を強制する。純関数なので Firestore/設定不要。
from publishr_api.services.demo_rate_limit import (  # noqa: E402
    _VERTEX_FAILSAFE_GLOBAL_CAP,
    _VERTEX_FAILSAFE_PER_CLIENT_CAP,
    _effective_caps,
)


def test_effective_caps_mock_is_passthrough() -> None:
    # mock（非課金）は従来どおり素通し＝caps 0 なら無効のまま（挙動不変）。
    assert _effective_caps("mock", 0, 0) == (0, 0)
    assert _effective_caps("mock", 7, 3) == (7, 3)


def test_effective_caps_vertex_unset_forces_failsafe() -> None:
    # 実課金なのに未設定 → 組込み上限を強制（無制限化を防ぐ最後の砦）。
    assert _effective_caps("vertex", 0, 0) == (
        _VERTEX_FAILSAFE_GLOBAL_CAP,
        _VERTEX_FAILSAFE_PER_CLIENT_CAP,
    )


def test_effective_caps_vertex_partial_unset_is_filled() -> None:
    # 片方だけ未設定でも欠けた側だけ組込み値で埋める。
    assert _effective_caps("vertex", 0, 3) == (_VERTEX_FAILSAFE_GLOBAL_CAP, 3)
    assert _effective_caps("vertex", 5, 0) == (5, _VERTEX_FAILSAFE_PER_CLIENT_CAP)


def test_effective_caps_vertex_explicit_caps_respected() -> None:
    # 明示設定は尊重（フェイルセーフは floor であって、緩くも厳しくも上書きしない）。
    assert _effective_caps("vertex", 5, 2) == (5, 2)
    assert _effective_caps("vertex", 100, 50) == (100, 50)
