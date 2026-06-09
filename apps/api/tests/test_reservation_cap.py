"""予約の「同時最大5冊」上限ガード（C2.1・I-16）のテスト。

reserved + writing の合計が上限未満のときだけ予約できる。満杯なら ConflictError。
1冊が reserved/writing を抜ける（published 等）と枠が空き、再び予約できる。
"""

from __future__ import annotations

import pytest
from publishr_api.config import settings
from publishr_api.errors import ConflictError
from publishr_api.repositories.mock_repository import MockRepository
from publishr_api.services import reservation_service

_ACTIVE = ("reserved", "writing")


def _active_count(repo) -> int:
    return len([b for b in repo.list_books() if b.status in _ACTIVE])


def _draft_ids(repo) -> list[str]:
    return [b.id for b in repo.list_books() if b.status == "draft"]


def test_reserve_caps_at_max_concurrent():
    repo = MockRepository()
    cap = settings.max_concurrent_reservations
    slots = cap - _active_count(repo)
    drafts = _draft_ids(repo)
    assert slots >= 1 and len(drafts) > slots  # 前提: 枠より多く draft がある

    # 空き枠ぶんは予約できる。
    for bid in drafts[:slots]:
        reservation_service.reserve_now(repo, bid)
    assert _active_count(repo) == cap

    # 満杯時の次の予約は上限で弾かれる（draft なのに予約不可）。
    with pytest.raises(ConflictError):
        reservation_service.reserve_now(repo, drafts[slots])


def test_reserve_frees_slot_when_book_leaves_active():
    repo = MockRepository()
    cap = settings.max_concurrent_reservations
    slots = cap - _active_count(repo)
    drafts = _draft_ids(repo)

    for bid in drafts[:slots]:
        reservation_service.reserve_now(repo, bid)
    assert _active_count(repo) == cap

    # 1冊を published にして枠を空ける。
    reserved = next(b for b in repo.list_books() if b.status == "reserved")
    repo.upsert_book(reserved.model_copy(update={"status": "published"}))

    # 空いた枠で新規予約できる（例外が出なければOK）。
    reservation_service.reserve_now(repo, drafts[slots])
    assert _active_count(repo) == cap


def test_reserve_non_draft_still_conflicts_with_status_not_cap():
    """二重予約は『状態が draft でない』конфликト（上限とは別経路）。"""
    repo = MockRepository()
    bid = _draft_ids(repo)[0]
    reservation_service.reserve_now(repo, bid)
    with pytest.raises(ConflictError):
        reservation_service.reserve_now(repo, bid)
