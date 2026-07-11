"""予約の「同時最大5冊」上限ガード（C2.1・I-16）のテスト。

reserved + writing の合計が上限未満のときだけ予約できる。満杯なら ConflictError。
1冊が reserved/writing を抜ける（published 等）と枠が空き、再び予約できる。
"""

from __future__ import annotations

import threading

import pytest
from publishr_api.config import settings
from publishr_api.errors import ConflictError, NotFoundError
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
    """二重予約は『状態が draft でない』競合（上限とは別経路）。"""
    repo = MockRepository()
    bid = _draft_ids(repo)[0]
    reservation_service.reserve_now(repo, bid)
    with pytest.raises(ConflictError):
        reservation_service.reserve_now(repo, bid)


def test_reserve_cap_is_owner_scoped():
    """cap は owner 単位（I-20）。ownerA が満杯でも ownerB は独立に予約できる。"""
    repo = MockRepository()
    cap = settings.max_concurrent_reservations
    drafts = _draft_ids(repo)
    assert len(drafts) >= cap + 1
    a_ids = drafts[:cap]
    b_id = drafts[cap]
    for bid in a_ids:
        b = repo.get_book(bid)
        repo.upsert_book(b.model_copy(update={"owner_uid": "ownerA"}))
    bb = repo.get_book(b_id)
    repo.upsert_book(bb.model_copy(update={"owner_uid": "ownerB"}))

    for bid in a_ids:
        reservation_service.reserve_now(repo, bid, owner_uid="ownerA")
    # ownerB は独立 cap なので、ownerA が満杯でも自分の本を予約できる。
    reservation_service.reserve_now(repo, b_id, owner_uid="ownerB")
    assert repo.get_book(b_id).status == "reserved"


def test_reserve_rejects_other_owners_draft():
    """他 owner の draft は予約できない（IDOR/課金発火の write 版・P0-1 の予約経路）。

    read 系（get_book）は owner 不一致で NotFound。予約（draft→reserved＝実Vertex執筆の発火）も
    同様に他 owner の本には効かず、存在秘匿のため NotFound を返す。
    """
    repo = MockRepository()
    bid = _draft_ids(repo)[0]
    b = repo.get_book(bid)
    repo.upsert_book(b.model_copy(update={"owner_uid": "ownerA"}))

    # ownerB は ownerA の draft を予約できない（存在秘匿の NotFound）。
    with pytest.raises(NotFoundError):
        reservation_service.reserve_now(repo, bid, owner_uid="ownerB")
    assert repo.get_book(bid).status == "draft"  # 状態は変わっていない

    # 本人（ownerA）は予約できる（正常系は不変）。
    reservation_service.reserve_now(repo, bid, owner_uid="ownerA")
    assert repo.get_book(bid).status == "reserved"


def test_reserve_atomic_under_concurrency_never_exceeds_cap():
    """並行予約でも owner の active は cap を超えない（ロックで原子化・I-20）。"""
    repo = MockRepository()
    cap = settings.max_concurrent_reservations
    # 全 book を draft・同一 owner に揃え、cap より多く同時予約を試す。
    for b in repo.list_books():
        repo.upsert_book(b.model_copy(update={"status": "draft", "owner_uid": "ownerX"}))
    ids = [b.id for b in repo.list_books()][: cap + 8]
    assert len(ids) > cap

    results: list[bool] = []
    lock = threading.Lock()
    barrier = threading.Barrier(len(ids))  # 全スレッド同時スタートで競合を最大化

    def worker(bid: str) -> None:
        barrier.wait()
        try:
            reservation_service.reserve_now(repo, bid, owner_uid="ownerX")
            ok = True
        except ConflictError:
            ok = False
        with lock:
            results.append(ok)

    threads = [threading.Thread(target=worker, args=(bid,)) for bid in ids]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    active = sum(1 for b in repo.list_books() if b.status in _ACTIVE and b.owner_uid == "ownerX")
    assert active == cap
    assert sum(results) == cap  # ちょうど cap 件だけ成功
