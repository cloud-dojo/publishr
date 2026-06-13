"""本文オフロード結線（C3.3）のオフラインテスト。

inline 既定は従来どおり body をドキュメントに持つ（mock不変）。body_store=gcs 相当（FakeStore
注入）では本文が退避され bodyUrl だけ残り、読出 endpoint がサーバ側で本文を再構成して返す。
実GCS は使わず FakeStore で seam を検証（決定的・課金ゼロ）。
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from publishr_api.deps import get_repository
from publishr_api.main import app
from publishr_api.repositories.mock_repository import MockRepository
from publishr_api.services import body_store, reservation_service

client = TestClient(app)


class _FakeStore:
    """インメモリの本文ストア（GCS の put/get/signed_url を模す）。"""

    def __init__(self) -> None:
        self.saved: dict[str, str] = {}

    def put(self, book_id: str, body: str) -> str:
        self.saved[book_id] = body
        return f"books/{book_id}/body.md"

    def get(self, book_id: str, body_url: str) -> str | None:
        return self.saved.get(book_id)

    def signed_url(self, book_id: str, body_url: str) -> str | None:
        return f"https://signed.example/{book_id}"


def _a_draft_id(repo: MockRepository) -> str:
    drafts = repo.list_books(status="draft")
    assert drafts, "fixture に draft の本が必要"
    return drafts[0].id


@pytest.fixture(autouse=True)
def _fresh_repo():
    get_repository.cache_clear()
    yield
    get_repository.cache_clear()


def test_inline_default_keeps_body_in_document():
    """既定（inline）: published 本は本文をドキュメントに持ち bodyUrl は付かない（従来挙動）。"""
    repo = MockRepository()
    bid = _a_draft_id(repo)
    reservation_service.reserve_now(repo, bid)
    out = reservation_service.process_write_job(repo, bid)
    assert out is not None and out.status == "published"
    assert out.body and len(out.body) > 0
    assert not out.body_url


def test_offload_moves_body_to_store_and_clears_doc(monkeypatch):
    """gcs 相当: 本文は store へ退避し、ドキュメントには bodyUrl だけ残る（body は空）。"""
    repo = MockRepository()
    fake = _FakeStore()
    monkeypatch.setattr(body_store, "get_body_store", lambda: fake)
    bid = _a_draft_id(repo)
    reservation_service.reserve_now(repo, bid)
    out = reservation_service.process_write_job(repo, bid)
    assert out is not None and out.status == "published"
    assert out.body == ""  # 退避済み＝ドキュメントに本文を残さない
    assert out.body_url == f"books/{bid}/body.md"
    assert fake.saved[bid]  # 本文は store に渡っている


def test_body_endpoint_returns_inline_body():
    """inline: GET /api/books/{id}/body は book.body をそのまま返す。"""
    repo = get_repository()
    bid = _a_draft_id(repo)
    reservation_service.reserve_now(repo, bid)
    reservation_service.process_write_job(repo, bid)
    res = client.get(f"/api/books/{bid}/body")
    assert res.status_code == 200
    assert res.json()["body"]


def test_body_endpoint_rehydrates_from_store(monkeypatch):
    """offload: ドキュメントの body は空でも、endpoint が store からサーバ側 read して返す。"""
    repo = get_repository()
    fake = _FakeStore()
    monkeypatch.setattr(body_store, "get_body_store", lambda: fake)
    bid = _a_draft_id(repo)
    reservation_service.reserve_now(repo, bid)
    written = reservation_service.process_write_job(repo, bid)
    assert written is not None and written.body == ""  # ドキュメントは空
    res = client.get(f"/api/books/{bid}/body")
    assert res.status_code == 200
    assert res.json()["body"] == fake.saved[bid]  # store の本文が返る


def test_body_endpoint_404_for_unknown_book():
    res = client.get("/api/books/does-not-exist/body")
    assert res.status_code == 404
