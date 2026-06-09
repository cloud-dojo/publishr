"""Pub/Sub push worker endpoint（/api/worker/write）のテスト（C2.2 Phase②）。

ローカルは PUBSUB_PUSH_AUDIENCE 未設定＝OIDC検証スキップ。push エンベロープを decode し、
冪等に process_write_job を呼ぶ。不正/欠損メッセージも 2xx で ack（再配信ループ防止）。
"""

from __future__ import annotations

import base64
import json

import pytest
from fastapi.testclient import TestClient
from publishr_api.deps import get_repository
from publishr_api.main import app
from publishr_api.services import reservation_service

client = TestClient(app)


@pytest.fixture(autouse=True)
def _fresh_repo():
    get_repository.cache_clear()
    yield
    get_repository.cache_clear()


def _push(book_id: str) -> dict:
    data = base64.b64encode(json.dumps({"bookId": book_id}).encode()).decode()
    return {"message": {"data": data, "messageId": "m1"}, "subscription": "sub"}


def _reserved_book_id(repo) -> str:
    bid = next(b.id for b in repo.list_books() if b.status == "draft")
    reservation_service.reserve_now(repo, bid)
    return bid


def test_worker_write_publishes_reserved_book():
    repo = get_repository()
    bid = _reserved_book_id(repo)
    res = client.post("/api/worker/write", json=_push(bid))
    assert res.status_code == 204
    assert repo.get_book(bid).status == "published"
    assert repo.get_book(bid).body


def test_worker_write_idempotent_on_duplicate_push():
    repo = get_repository()
    bid = _reserved_book_id(repo)
    assert client.post("/api/worker/write", json=_push(bid)).status_code == 204
    repo.upsert_book(repo.get_book(bid).model_copy(update={"body": "SENTINEL"}))
    # 二重 push → 再処理しない（published のまま・SENTINEL 不変）。
    assert client.post("/api/worker/write", json=_push(bid)).status_code == 204
    assert repo.get_book(bid).body == "SENTINEL"


def test_worker_write_bad_message_acks():
    assert client.post("/api/worker/write", json={"message": {}}).status_code == 204
    assert client.post("/api/worker/write", json={}).status_code == 204
