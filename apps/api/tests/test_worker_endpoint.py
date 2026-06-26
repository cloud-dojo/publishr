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


def test_worker_runs_blocking_asyncio_job_without_nested_loop(monkeypatch):
    """process_write_job が内部で asyncio.run（実Vertex本文生成）を呼んでも、async worker の
    実行中ループとネストせず 204 を返す（threadpool 実行）。直接呼ぶと RuntimeError になる回帰を防ぐ。"""
    import asyncio

    called = {"ok": False}

    def fake_job(repo, book_id):  # vertex 経路の run_body_loop_vertex と同じ asyncio.run 状況を再現
        asyncio.run(asyncio.sleep(0))
        called["ok"] = True
        return None

    monkeypatch.setattr(reservation_service, "process_write_job", fake_job)
    res = client.post("/api/worker/write", json=_push("b_any"))
    assert res.status_code == 204
    assert called["ok"] is True


# --- 滞留防止: 本文生成失敗時の再配信制御（transient=nack / 非transient=ack）-------


def test_worker_write_transient_failure_nacks_and_keeps_reserved(monkeypatch):
    """transient（429/timeout/503）失敗は 5xx で nack＝Pub/Sub が再配信して後でリトライ。

    本は writing で取り残さず reserved に戻る（process_write_job のロールバック）。
    """
    repo = get_repository()
    bid = _reserved_book_id(repo)

    def boom(_repo, _book):
        raise RuntimeError("vertex 429 resource exhausted")  # is_transient=True

    monkeypatch.setattr(reservation_service, "_generate_body", boom)
    res = client.post("/api/worker/write", json=_push(bid))
    assert res.status_code >= 500  # nack → 再配信（自動リトライ）
    assert repo.get_book(bid).status == "reserved"  # writing で滞留しない


def test_worker_write_permanent_failure_acks_and_keeps_reserved(monkeypatch):
    """非transient（スキーマ違反等）は 204 で ack＝再配信ストームを止めて手動再実行に委ねる。

    本は reserved に戻る（writing で取り残さない）。
    """
    repo = get_repository()
    bid = _reserved_book_id(repo)

    def boom(_repo, _book):
        raise ValueError("schema violation")  # is_transient=False

    monkeypatch.setattr(reservation_service, "_generate_body", boom)
    res = client.post("/api/worker/write", json=_push(bid))
    assert res.status_code == 204  # ack（storm 防止）
    assert repo.get_book(bid).status == "reserved"


# --- 企画(モードA)非同期 worker（/api/worker/plan）------------------------------

def _plan_push(user_id: str, owner: str | None = None, observe_uid: str = "") -> dict:
    payload = {"userId": user_id, "owner": owner or user_id, "observeUid": observe_uid}
    data = base64.b64encode(json.dumps(payload).encode()).decode()
    return {"message": {"data": data, "messageId": "p1"}, "subscription": "sub"}


def test_worker_plan_runs_mode_a_and_adds_arrivals():
    repo = get_repository()
    before = len(repo.list_books(shelf="arrivals"))
    res = client.post("/api/worker/plan", json=_plan_push("u_sakura"))
    assert res.status_code == 204
    assert len(repo.list_books(shelf="arrivals")) > before  # 入荷が増えた


def test_worker_plan_bad_or_missing_message_acks():
    # 壊れた data / userId 欠落 はどちらも 2xx で ack（再配信ループ防止）。
    assert client.post("/api/worker/plan", json={"message": {"data": "!!notb64"}}).status_code == 204
    missing = base64.b64encode(json.dumps({"owner": "x"}).encode()).decode()
    assert client.post("/api/worker/plan", json={"message": {"data": missing}}).status_code == 204
    assert client.post("/api/worker/plan", json={}).status_code == 204


def test_worker_plan_acks_even_on_run_failure(monkeypatch):
    """企画実行が失敗(例: Vertex 429)でも 204 で ack＝高価な企画の再配信ストームを防ぐ。"""
    from publishr_api.services import mode_a_service

    def boom(*args, **kwargs):
        raise RuntimeError("vertex exhausted")

    monkeypatch.setattr(mode_a_service, "run", boom)
    res = client.post("/api/worker/plan", json=_plan_push("u_sakura"))
    assert res.status_code == 204


# --- I-38: 再配信冪等（runId ロック・決定的ID）----------------------------------

def _plan_push_run(user_id: str, run_id: str, message_id: str = "p1") -> dict:
    payload = {"userId": user_id, "owner": user_id, "observeUid": "", "runId": run_id}
    data = base64.b64encode(json.dumps(payload).encode()).decode()
    return {"message": {"data": data, "messageId": message_id}, "subscription": "sub"}


def test_planning_envelope_parses_run_id():
    """payload.runId を最優先・無ければ messageId にフォールバック（worker の冪等鍵）。"""
    from publishr_api.routers.worker import _planning_job_from_envelope

    job = _planning_job_from_envelope(_plan_push_run("u_sakura", "run-123"))
    assert job and job["run_id"] == "run-123"
    # runId 無し → messageId フォールバック
    job2 = _planning_job_from_envelope(_plan_push("u_sakura"))  # messageId="p1"
    assert job2 and job2["run_id"] == "p1"


def test_begin_planning_run_is_idempotent():
    """MockRepository: 同一 run_id は初回 True・2回目 False（complete/fail で状態更新）。"""
    repo = get_repository()
    assert repo.begin_planning_run("r1", "u_sakura", "u_sakura") is True
    assert repo.begin_planning_run("r1", "u_sakura", "u_sakura") is False  # 再配信は skip
    repo.complete_planning_run("r1", ["arr_x_a", "arr_x_b"])
    assert repo.begin_planning_run("r1", "u_sakura", "u_sakura") is False  # completed も skip


def test_worker_plan_skips_redelivery_same_run_id(monkeypatch):
    """同一 runId の再配信では mode_a_service.run は1回だけ＝重複入荷ストームを止める。"""
    import types

    from publishr_api.services import mode_a_service

    calls = {"n": 0}

    def counting_run(*args, **kwargs):
        calls["n"] += 1
        return types.SimpleNamespace(books=[])

    monkeypatch.setattr(mode_a_service, "run", counting_run)
    env = _plan_push_run("u_sakura", "run-dup")
    assert client.post("/api/worker/plan", json=env).status_code == 204
    assert client.post("/api/worker/plan", json=env).status_code == 204  # 再配信
    assert calls["n"] == 1, "同一 run_id の2回目はロックで skip される"


def test_worker_plan_redelivery_does_not_increase_books():
    """同一 runId を2回 push しても入荷数は増えない（ロックで2回目 skip・決定的IDも保険）。"""
    repo = get_repository()
    before = len(repo.list_books(shelf="arrivals"))
    env = _plan_push_run("u_sakura", "run-once")
    assert client.post("/api/worker/plan", json=env).status_code == 204
    after_first = len(repo.list_books(shelf="arrivals"))
    assert after_first > before  # 初回は入荷
    assert client.post("/api/worker/plan", json=env).status_code == 204  # 再配信
    assert len(repo.list_books(shelf="arrivals")) == after_first  # 増えない


def test_enqueue_planning_puts_run_id_in_pubsub_payload(monkeypatch):
    """pubsub 経路は runId を payload に載せる（再配信で同一→冪等鍵になる）。mock 経路は載せない。"""
    from publishr_api.config import settings
    from publishr_api.services import pubsub_queue, write_queue

    captured = {}
    monkeypatch.setattr(settings, "queue", "pubsub")
    monkeypatch.setattr(pubsub_queue, "publish_planning_job", lambda payload: captured.update(payload) or "mid")
    write_queue.enqueue_planning(
        get_repository(), user_id="u_sakura", owner_uid="u_sakura",
        observe_uid=None, theme_kind="honmei", run_id="run-xyz",
    )
    assert captured.get("runId") == "run-xyz"
    assert captured.get("themeKind") == "honmei"
