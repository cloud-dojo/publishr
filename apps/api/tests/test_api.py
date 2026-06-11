"""BFF エンドポイント＋状態機械のテスト。"""

from __future__ import annotations

import asyncio

import pytest
from fastapi.testclient import TestClient
from publishr_api.deps import get_repository
from publishr_api.main import app
from publishr_api.repositories.mock_repository import MockRepository
from publishr_api.routers.api import trigger_guard
from publishr_api.services import reservation_service

client = TestClient(app)


@pytest.fixture(autouse=True)
def _fresh_repo():
    """各テストで新しいインメモリ状態＋トリガーガードをリセットする。"""
    get_repository.cache_clear()
    trigger_guard.reset()
    yield
    get_repository.cache_clear()
    trigger_guard.reset()


def test_healthz():
    res = client.get("/healthz")
    assert res.status_code == 200
    assert res.json()["status"] == "ok"


def test_api_healthz():
    """公開URL用 health（`/healthz` は run.app エッジ予約で届かないため）。"""
    res = client.get("/api/healthz")
    assert res.status_code == 200
    assert res.json()["status"] == "ok"


def test_cors_allows_next_dev_fallback_port():
    res = client.options(
        "/pipeline/run",
        headers={
            "Origin": "http://localhost:3001",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "content-type",
        },
    )
    assert res.status_code == 200
    assert res.headers["access-control-allow-origin"] == "http://localhost:3001"


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


def _a_draft_id() -> str:
    return client.get("/books", params={"status": "draft"}).json()[0]["id"]


def test_reserve_blocked_for_external_when_auth_required(monkeypatch):
    """require_reserve_auth=True かつ トークン無 → 401（完全な外部はブロック）。"""
    from publishr_api import config

    monkeypatch.setattr(config.settings, "require_reserve_auth", True)
    res = client.post("/api/reserve", json={"bookId": _a_draft_id()})
    assert res.status_code == 401
    # /books/{id}/reserve（レガシー経路）も同様に塞がる
    assert client.post(f"/books/{_a_draft_id()}/reserve").status_code == 401


def test_reserve_allowed_for_logged_in_when_auth_required(monkeypatch):
    """require_reserve_auth=True でも 有効トークン（ログイン済み）なら誰でも予約可。"""
    from publishr_api import config
    from publishr_api.routers import api as api_mod

    monkeypatch.setattr(config.settings, "require_reserve_auth", True)
    monkeypatch.setattr(api_mod, "_verify_uid", lambda _auth: "u_loggedin")
    res = client.post(
        "/api/reserve",
        json={"bookId": _a_draft_id()},
        headers={"Authorization": "Bearer valid"},
    )
    assert res.status_code == 200
    assert res.json()["status"] == "reserved"


def test_reserve_anonymous_ok_when_auth_not_required():
    """既定（require_reserve_auth=False）では従来どおり匿名でも予約可（mock/$0）。"""
    res = client.post("/api/reserve", json={"bookId": _a_draft_id()})
    assert res.status_code == 200


def test_feedback_updates():
    published = client.get("/books", params={"status": "published"}).json()[0]
    bid = published["id"]
    res = client.post(
        f"/books/{bid}/feedback",
        json={"rating": 5, "wantsSequel": True, "readPercent": 25, "readingReaction": "helpful"},
    )
    assert res.status_code == 200
    fb = res.json()["feedback"]
    assert fb["rating"] == 5 and fb["wantsSequel"] is True
    assert fb["readPercent"] == 25
    assert fb["readingReaction"] == "helpful"


def test_reading_state_updates_granularity_and_annotations():
    published = client.get("/books", params={"status": "published"}).json()[0]
    bid = published["id"]
    res = client.post(
        f"/books/{bid}/reading-state",
        json={
            "granularity": "summary",
            "annotations": [
                {
                    "id": "ann_test",
                    "kind": "note",
                    "paragraphIndex": 0,
                    "text": "着任直後の100日",
                    "note": "ここを次の1on1で使う",
                }
            ],
        },
    )
    assert res.status_code == 200
    body = res.json()
    assert body["granularity"] == "summary"
    assert body["annotations"][0]["kind"] == "note"
    assert body["annotations"][0]["paragraphIndex"] == 0


def test_pipeline_run_returns_reject_log():
    """新モードA: 入荷(arrivals/draft)を生成し、却下→採用の証跡を返す。"""
    res = client.post("/pipeline/run", json={"userId": "u_sakura"})
    assert res.status_code == 200
    data = res.json()
    assert len(data["books"]) >= 1
    for b in data["books"]:
        assert b["shelf"] == "arrivals"
        assert b["status"] == "draft"
    # 採用企画ID と本の planId が整合。
    assert data["approvedPlanIds"]
    assert {b["planId"] for b in data["books"]} <= set(data["approvedPlanIds"])
    # 企画会議の却下→採用（基準1の画）。
    assert any(e["round"] == 1 and e["verdict"] == "却下" for e in data["rejectLog"])
    assert any(e["round"] == 2 and e["verdict"] == "採用" for e in data["rejectLog"])


def test_trigger_planning_adds_books():
    """手動トリガー（モードA）で入荷が増える＝『押す→本ができる』。"""
    res = client.post("/api/trigger/planning", json={"userId": "u_sakura"})
    assert res.status_code == 200
    data = res.json()
    assert data["ok"] is True
    assert data["booksAdded"] >= 1


def test_trigger_planning_rate_limited_on_immediate_repeat():
    """同一 uid の連打はレート制限（429）。"""
    first = client.post("/api/trigger/planning", json={"userId": "u_sakura"})
    assert first.status_code == 200
    second = client.post("/api/trigger/planning", json={"userId": "u_sakura"})
    assert second.status_code == 429


def test_trigger_releases_lock_on_failure():
    """失敗（不明ユーザー404）でもロックは解放され、uid が実行中で固着しない。"""
    res = client.post("/api/trigger/planning", json={"userId": "u_nope"})
    assert res.status_code == 404
    assert "u_nope" not in trigger_guard._running


def test_advance_state_machine():
    """reserved → writing → published と本文生成（タイマー0で即時検証）。"""
    repo = MockRepository()
    reservation_service.reserve_now(repo, "b_makasekata")
    asyncio.run(reservation_service.advance(repo, "b_makasekata", t1=0, t2=0))
    book = repo.get_book("b_makasekata")
    assert book.status == "published"
    assert book.body and "権限の設計図" in book.body
