"""公開デモの書き込み封鎖・入力検証・trigger日次上限のバイパス封じ（P0ハードニング）のテスト。

無認証ショーケース公開中（リポジトリも公開）に、共有棚の汚染（★1000・巨大annotations・
dropped注入）・学習ループへの注入・実Vertex課金の第三者連打を防ぐ。
既定（ローカル/mock）は従来挙動不変＝フラグON/キャップ0で全て素通し。
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from publishr_api.config import settings
from publishr_api.deps import get_repository
from publishr_api.main import app
from publishr_api.routers import api as api_router
from publishr_api.routers.api import trigger_guard
from publishr_api.services.demo_rate_limit import DemoRateLimiter, InMemoryDemoRateStore

client = TestClient(app)


@pytest.fixture(autouse=True)
def _fresh():
    get_repository.cache_clear()
    trigger_guard.reset()
    yield
    get_repository.cache_clear()
    trigger_guard.reset()


def _first_book_id() -> str:
    return client.get("/books").json()[0]["id"]


# ── ① feedback / reading-state の封鎖（fail-closed フラグ）──────────────
def test_feedback_writes_blocked_when_flag_off(monkeypatch):
    monkeypatch.setattr(settings, "allow_feedback_writes", False)
    bid = _first_book_id()
    assert client.post(f"/books/{bid}/feedback", json={"rating": 5}).status_code == 403
    assert (
        client.post(f"/books/{bid}/reading-state", json={"granularity": "full"}).status_code
        == 403
    )
    # 共有棚の書き換え（匿名 uid→demo_uid フォールバックで所有者チェックを通過する口）も同フラグで封鎖。
    assert client.post(f"/api/books/{bid}/move-to-library").status_code == 403


def test_feedback_writes_open_by_default():
    """既定（ローカル/mock/smoke）は従来どおり書ける＝挙動不変。"""
    bid = _first_book_id()
    assert client.post(f"/books/{bid}/feedback", json={"rating": 5}).status_code == 200
    assert (
        client.post(f"/books/{bid}/reading-state", json={"granularity": "full"}).status_code
        == 200
    )


# ── ① 入力検証（表示崩し・巨大ペイロードの拒否）─────────────────────
def test_feedback_rejects_out_of_range_values():
    bid = _first_book_id()
    # BookCard が「★×rating」を描くため範囲必須（rating=1000 でトップ一覧が崩れる）。
    assert client.post(f"/books/{bid}/feedback", json={"rating": 1000}).status_code == 422
    assert client.post(f"/books/{bid}/feedback", json={"rating": 0}).status_code == 422
    assert client.post(f"/books/{bid}/feedback", json={"readPercent": 200}).status_code == 422
    assert client.post(f"/books/{bid}/feedback", json={"readPercent": -1}).status_code == 422


def test_reading_reaction_sanitized_and_capped():
    """readingReaction も impression 同様にサニタイズ（制御文字除去＋200字カット）。"""
    bid = _first_book_id()
    raw = "good:\x00\x01" + "あ" * 500
    res = client.post(f"/books/{bid}/feedback", json={"readingReaction": raw})
    assert res.status_code == 200
    rr = res.json()["feedback"]["readingReaction"]
    assert "\x00" not in rr
    assert len(rr) <= 200
    assert rr.startswith("good:")


def test_annotations_count_and_length_limits():
    bid = _first_book_id()
    ann = {"id": "a1", "kind": "highlight", "paragraphIndex": 0, "text": "x"}
    # 件数上限200（巨大 annotations が GET /books で全訪問者へ配信されるのを防ぐ）。
    too_many = [dict(ann, id=f"a{i}") for i in range(201)]
    assert (
        client.post(f"/books/{bid}/reading-state", json={"annotations": too_many}).status_code
        == 422
    )
    # text/note は500字まで。
    assert (
        client.post(
            f"/books/{bid}/reading-state", json={"annotations": [dict(ann, text="x" * 501)]}
        ).status_code
        == 422
    )
    # 上限内は従来どおり保存できる。
    ok = [dict(ann, id=f"a{i}") for i in range(3)]
    res = client.post(f"/books/{bid}/reading-state", json={"annotations": ok})
    assert res.status_code == 200
    assert len(res.json()["annotations"]) == 3


def test_annotation_text_control_chars_sanitized():
    bid = _first_book_id()
    ann = {"id": "a1", "kind": "highlight", "paragraphIndex": 0, "text": "刺\x00さった", "note": "メ\x1fモ"}
    res = client.post(f"/books/{bid}/reading-state", json={"annotations": [ann]})
    assert res.status_code == 200
    saved = res.json()["annotations"][0]
    assert saved["text"] == "刺さった"
    assert saved["note"] == "メモ"


# ── ② /pipeline/run の本番非公開（dev専用の素の入口）──────────────────
def test_pipeline_run_blocked_when_flag_off(monkeypatch):
    monkeypatch.setattr(settings, "allow_pipeline_run", False)
    res = client.post("/pipeline/run", json={"userId": "u_sakura"})
    assert res.status_code == 403


# ── ② trigger の日次上限バイパス封じ（client_id 無しにも global を課す）────
def test_trigger_without_client_id_consumes_global_cap(monkeypatch):
    limiter = DemoRateLimiter(store=InMemoryDemoRateStore(), global_cap=1, per_client_cap=1)
    monkeypatch.setattr(api_router, "demo_rate_limiter", limiter)
    assert client.post("/api/trigger/planning", json={"userId": "u_sakura"}).status_code == 200
    trigger_guard.reset()  # 検証対象は連打ガードではなく日次上限
    res = client.post("/api/trigger/planning", json={"userId": "u_sakura"})
    assert res.status_code == 429
    assert "体験枠" in res.json()["detail"]


def test_trigger_server_calls_not_limited_by_per_client_cap(monkeypatch):
    """Scheduler/運用の複数回実行は per-client 3 に縛られず global まで使える。"""
    limiter = DemoRateLimiter(store=InMemoryDemoRateStore(), global_cap=7, per_client_cap=3)
    monkeypatch.setattr(api_router, "demo_rate_limiter", limiter)
    for _ in range(4):  # per-client 上限3を超える4回でも global 内なら通る
        trigger_guard.reset()
        assert (
            client.post("/api/trigger/planning", json={"userId": "u_sakura"}).status_code == 200
        )
