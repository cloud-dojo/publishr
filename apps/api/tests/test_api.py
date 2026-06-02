"""BFF エンドポイント＋状態機械のテスト。"""

from __future__ import annotations

import asyncio

import pytest
from fastapi.testclient import TestClient
from publishr_api.deps import get_repository
from publishr_api.main import app
from publishr_api.repositories.mock_repository import MockRepository
from publishr_api.services import reservation_service

client = TestClient(app)


@pytest.fixture(autouse=True)
def _fresh_repo():
    """各テストで新しいインメモリ状態にする。"""
    get_repository.cache_clear()
    yield
    get_repository.cache_clear()


def test_healthz():
    res = client.get("/healthz")
    assert res.status_code == 200
    assert res.json()["status"] == "ok"


def test_list_books_full_shelf():
    res = client.get("/books")
    assert res.status_code == 200
    assert len(res.json()) >= 8


def test_list_books_filtered():
    res = client.get("/books", params={"shelf": "arrivals"})
    assert res.status_code == 200
    assert all(b["shelf"] == "arrivals" for b in res.json())


def test_get_book_camel_case():
    res = client.get("/books/b_makasekata")
    assert res.status_code == 200
    body = res.json()
    assert body["authorPersonaId"] == "p_kirishima"
    assert "readPercent" in body["feedback"]


def test_get_book_404():
    assert client.get("/books/nope").status_code == 404


def test_reserve_then_conflict():
    draft = client.get("/books", params={"status": "draft"}).json()[0]
    bid = draft["id"]
    res = client.post(f"/books/{bid}/reserve")
    assert res.status_code == 200
    assert res.json()["status"] == "reserved"
    # 二重予約は 409
    assert client.post(f"/books/{bid}/reserve").status_code == 409


def test_feedback_updates():
    published = client.get("/books", params={"status": "published"}).json()[0]
    bid = published["id"]
    res = client.post(f"/books/{bid}/feedback", json={"rating": 5, "wantsSequel": True})
    assert res.status_code == 200
    fb = res.json()["feedback"]
    assert fb["rating"] == 5 and fb["wantsSequel"] is True


def test_pipeline_run_returns_reject_log():
    res = client.post("/pipeline/run", json={"userId": "u_tadokoro"})
    assert res.status_code == 200
    data = res.json()
    assert len(data["books"]) >= 4
    assert len(data["rejectLog"]) >= 6
    assert any(e["round"] == 1 and e["verdict"] == "却下" for e in data["rejectLog"])
    assert any(e["round"] == 2 and e["verdict"] == "採用" for e in data["rejectLog"])


def test_advance_state_machine():
    """reserved → writing → published と本文生成（タイマー0で即時検証）。"""
    repo = MockRepository()
    reservation_service.reserve_now(repo, "b_makasekata")
    asyncio.run(reservation_service.advance(repo, "b_makasekata", t1=0, t2=0))
    book = repo.get_book("b_makasekata")
    assert book.status == "published"
    assert book.body and "権限の設計図" in book.body
