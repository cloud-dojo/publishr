"""執筆ワーカー（process_write_job）の冪等性テスト（C2.2・I-20）。

予約済み(reserved)の本を執筆して published にする。二重配信（同じジョブが2回来る）でも
1回だけ処理し、再生成しない（冪等）。予約外（draft 等）は skip。
"""

from __future__ import annotations

from publishr_api.repositories.mock_repository import MockRepository
from publishr_api.services import reservation_service


def _a_draft_id(repo) -> str:
    return next(b.id for b in repo.list_books() if b.status == "draft")


def test_process_write_job_publishes_reserved_book():
    repo = MockRepository()
    bid = _a_draft_id(repo)
    reservation_service.reserve_now(repo, bid)  # draft → reserved
    book = reservation_service.process_write_job(repo, bid)
    assert book is not None
    assert book.status == "published"
    assert book.body  # 本文が入る


def test_process_write_job_idempotent_does_not_reprocess_published():
    """二重配信されても published を再処理しない（冪等）。"""
    repo = MockRepository()
    bid = _a_draft_id(repo)
    reservation_service.reserve_now(repo, bid)
    reservation_service.process_write_job(repo, bid)  # published

    # 既に処理済みの印として本文を差し替える。
    pub = repo.get_book(bid)
    repo.upsert_book(pub.model_copy(update={"body": "SENTINEL"}))

    # 二重配信: もう一度処理しても skip＝SENTINEL のまま（再生成しない）。
    again = reservation_service.process_write_job(repo, bid)
    assert again is not None
    assert again.status == "published"
    assert again.body == "SENTINEL"


def test_process_write_job_skips_non_reserved():
    """未予約（draft）はワーカーが処理しない（skip・冪等の前提）。"""
    repo = MockRepository()
    bid = _a_draft_id(repo)
    book = reservation_service.process_write_job(repo, bid)
    assert book is not None
    assert book.status == "draft"  # 変更なし


def test_process_write_job_missing_book_returns_none():
    repo = MockRepository()
    assert reservation_service.process_write_job(repo, "nope") is None
