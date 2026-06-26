"""執筆ワーカー（process_write_job）の冪等性テスト（C2.2・I-20）。

予約済み(reserved)の本を執筆して published にする。二重配信（同じジョブが2回来る）でも
1回だけ処理し、再生成しない（冪等）。予約外（draft 等）は skip。
"""

from __future__ import annotations

import pytest

from publishr_api.repositories.mock_repository import MockRepository
from publishr_api.services import reservation_service, write_queue


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


def test_process_write_job_uses_mode_b_and_records_edit_rounds():
    """worker は mode_b（編集長⇄著者ループ）で本文を生成し editRounds を記録する。"""
    repo = MockRepository()
    bid = _a_draft_id(repo)
    reservation_service.reserve_now(repo, bid)
    book = reservation_service.process_write_job(repo, bid)
    assert book is not None
    assert book.status == "published"
    assert book.edit_round >= 2  # 編集ループを通った証跡（既存 Book.edit_round に記録）
    assert book.body.count("## ") >= 3  # 複数章の本文（mode_b 形式）
    assert "## はじめに" in book.body
    assert "## おわりに" in book.body


# --- 滞留防止: 本文生成失敗で writing に取り残さない（§7-2・I-20）-----------------


def test_process_write_job_rolls_back_to_reserved_on_generation_failure(monkeypatch):
    """本文生成が例外で落ちても writing で取り残さず reserved へ戻す。例外は呼び出し側へ送出。

    旧バグ: process_write_job は先に reserved→writing を確定してから本文生成するため、生成例外時に
    本が writing（=UI「準備中」）のまま恒久滞留していた（incident-vertex-quota-writing-stuck §2/§7-2）。
    """
    repo = MockRepository()
    bid = _a_draft_id(repo)
    reservation_service.reserve_now(repo, bid)  # reserved

    def boom(_repo, _book):
        raise RuntimeError("vertex 429 resource exhausted")

    monkeypatch.setattr(reservation_service, "_generate_body", boom)
    with pytest.raises(RuntimeError):
        reservation_service.process_write_job(repo, bid)

    book = repo.get_book(bid)
    assert book.status == "reserved"  # writing で取り残さない（再実行で拾える状態へ）
    assert not book.body


def test_release_reservation_rolls_reserved_back_to_draft():
    """enqueue 失敗時のロールバック原子: reserved → draft。"""
    repo = MockRepository()
    bid = _a_draft_id(repo)
    reservation_service.reserve_now(repo, bid)
    book = reservation_service.release_reservation(repo, bid)
    assert book is not None
    assert book.status == "draft"


def test_release_reservation_noop_when_not_reserved():
    """reserved 以外（draft/published 等）は触らない（冪等・誤巻き戻し防止）。"""
    repo = MockRepository()
    bid = _a_draft_id(repo)  # draft のまま
    book = reservation_service.release_reservation(repo, bid)
    assert book is not None
    assert book.status == "draft"  # 変化なし


def test_reserve_and_enqueue_rolls_back_to_draft_when_publish_fails(monkeypatch):
    """予約後の執筆ジョブ投入(publish)が失敗したら reserved 孤児を作らず draft へ戻す。

    旧バグ: reserve_now（draft→reserved 確定）の後に publish_write_job が落ちると、再配信する元
    メッセージも無いまま reserved（=「準備中」）で誰にも拾われず滞留していた。
    """
    repo = MockRepository()
    bid = _a_draft_id(repo)

    def boom(_repo, _book_id):
        raise RuntimeError("pubsub publish timeout")

    monkeypatch.setattr(write_queue, "enqueue", boom)
    with pytest.raises(RuntimeError):
        write_queue.reserve_and_enqueue(repo, bid)

    assert repo.get_book(bid).status == "draft"  # reserved 孤児にしない


def test_reserve_and_enqueue_happy_path_enqueues_once(monkeypatch):
    """正常時は予約して1回だけ enqueue する（reserved のまま・worker が後で published 化）。"""
    repo = MockRepository()
    bid = _a_draft_id(repo)
    calls = {"n": 0}
    monkeypatch.setattr(write_queue, "enqueue", lambda _r, _b: calls.__setitem__("n", calls["n"] + 1))
    book = write_queue.reserve_and_enqueue(repo, bid)
    assert book is not None and book.status == "reserved"
    assert calls["n"] == 1


def test_published_estimate_and_preface_match_body():
    """入荷時に推定分量(章数/分)・序文サンプルを実本文から再計算＝preview の見積り/別ティザーと
    実体の乖離（推定分量が違う・序文と本文が異なる）を是正する。"""
    from publishr_api.services.reservation_service import _body_chapter_count, _body_preface

    repo = MockRepository()
    bid = _a_draft_id(repo)
    reservation_service.reserve_now(repo, bid)
    book = reservation_service.process_write_job(repo, bid)
    assert book is not None and book.status == "published"
    assert book.estimated_chapters == _body_chapter_count(book.body) >= 3  # 実本文の章数
    assert book.estimated_minutes >= 1
    assert book.preface_sample == _body_preface(book.body)  # 本文冒頭プローズ＝本文と整合
    assert book.preface_sample and not book.preface_sample.lstrip().startswith("#")
    assert book.preface_sample[:15] in book.body  # サンプルは実本文の一部
