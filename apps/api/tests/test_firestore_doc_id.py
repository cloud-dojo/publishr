"""FirestoreRepository のドキュメントID安全化（planningJobs/{run_id}）のテスト。

未検証の run_id（ユーザー入力・pubsub payload 由来）が Firestore の禁止パターン
（予約 `__.*__` / `/` を含む / `.`・`..` / 空・長すぎ）に該当すると .document() が
InvalidArgument(400)→worker 500→Pub/Sub 再配信ストームになる。demo_rate の `_safe_key`
と同型の境界サニタイズを検証する（Firestore 接続不要の純関数テスト）。
"""

from __future__ import annotations

import re

from publishr_api.repositories.firestore_repository import FirestoreRepository

_RESERVED = re.compile(r"__.*__")


def _safe(run_id: str) -> str:
    return FirestoreRepository._safe_doc_id(run_id)


def test_normal_run_id_is_unchanged():
    """正規の run_id（planning_uid_ts_hex）は不変＝冪等キーが従来と一致。"""
    rid = "planning_5JLLGOc3rpXiGN9KXmsISBNAKty2_20260709074239_c14585ff"
    assert _safe(rid) == rid


def test_reserved_pattern_is_escaped():
    for rid in ("__server__", "__x__", "____"):
        out = _safe(rid)
        assert not _RESERVED.fullmatch(out), f"{rid!r} -> {out!r} は予約パターンに残っている"


def test_slash_and_dots_are_neutralized():
    assert "/" not in _safe("a/b/c")            # パス segment 破壊を防ぐ
    assert _safe(".") not in (".", "")           # 不正ドキュメントID
    assert _safe("..") not in ("..", "")


def test_length_is_bounded():
    assert len(_safe("x" * 5000)) <= 256         # 1500バイト制限に余裕を持って収める


def test_deterministic():
    """同じ入力は同じ safe ID＝Pub/Sub 再配信の冪等 dedup が壊れない。"""
    assert _safe("__x__") == _safe("__x__")
