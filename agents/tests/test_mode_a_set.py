"""モードA 4テーマ縦串（予約制廃止改定 2026-06-23・本丸）の決定的オフラインテスト。

observe → reader → run_planning_set(4テーマ) → 各テーマ[キャスティング→プレビュー→装丁]
→ 棚に4冊（1冊/テーマ・著者は4冊で散る）。基準1（reject→採用の証跡）はセット版で担保。
全mock・実LLMなし・決定的。
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from publishr_schema import Book, load_users

from publishr_agents.mode_a import (
    make_published_books,
    map_mode_a_set_to_books,
    run_mode_a_set_pipeline,
)
from publishr_agents.observe import FixtureObservationSource
from publishr_api.repositories.mock_repository import MockRepository
from publishr_agents.persist_mapping import persist_arrivals

JST = timezone(timedelta(hours=9))
NOW = datetime(2026, 6, 3, 6, 0, tzinfo=JST)


def _user():
    users = {u.id: u for u in load_users()}
    return users["u_sakura"]


def _run():
    return run_mode_a_set_pipeline(_user(), source=FixtureObservationSource(), now=NOW)


# ── 4冊縦串（1-1-1-1） ──────────────────────────────────────
def test_set_pipeline_produces_four_books():
    res = _run()
    assert len(res.books) == 4
    # 4テーマ＝4つの別企画
    plan_ids = [mb.plan.proposal_id for mb in res.books]
    assert len(set(plan_ids)) == 4
    # 各冊に装丁付きBookDraftが1つ
    for mb in res.books:
        assert len(mb.shelved) == 1
        assert mb.shelved[0]["bookDraft"]["title"]


def test_authors_are_diverse_across_books():
    """著者が4冊で散る（1テーマ=1著者・personaId 衝突なし＝book id 衝突回避）。"""
    res = _run()
    author_ids = [mb.personas[0].persona_id for mb in res.books]
    assert len(set(author_ids)) == 4


def test_set_planning_has_reject_then_approve_trace():
    """セットゲートの差し戻し→採用＋reject_log 証跡（基準1の核・セット版）。"""
    res = _run()
    planning = res.planning
    assert planning["planSetVerdict"]["decision"] == "approve"
    assert planning["rejectLog"], "却下証跡（reject_log）が残る"
    history = planning["verdictHistory"]
    assert history[0]["decision"] == "revise" and history[-1]["decision"] == "approve"


# ── 永続化マッピング（4冊→Book/Persona・arrivals/draft）────────
def test_set_maps_to_four_arrivals():
    res = _run()
    books, personas = map_mode_a_set_to_books(res, owner_uid="u_x", created_at=NOW.isoformat())
    assert len(books) == 4
    assert all(isinstance(b, Book) for b in books)
    assert len({b.id for b in books}) == 4              # book id が4冊で別
    assert all(b.shelf == "arrivals" and b.status == "draft" for b in books)
    assert all(b.owner_uid == "u_x" and b.created_at for b in books)
    # 著者が4冊ぶん解決できる
    assert len(personas) == 4


def test_set_persist_to_repo_idempotent():
    res = _run()
    books, personas = map_mode_a_set_to_books(res, owner_uid="u_x", created_at=NOW.isoformat())
    repo = MockRepository()  # 既存デモ本が seed 済みなので「増えない＋自分の4冊が居る」で検証
    n = persist_arrivals(repo, books, personas)
    assert n == 4
    before = len(repo.list_books(status="draft", shelf="arrivals"))
    persist_arrivals(repo, books, personas)  # 再upsert（同一ID）
    after = len(repo.list_books(status="draft", shelf="arrivals"))
    assert before == after  # 冪等（再upsertで増えない）
    arrival_ids = {b.id for b in repo.list_books(status="draft", shelf="arrivals")}
    assert {b.id for b in books} <= arrival_ids  # 投入した4冊が棚に居る


# ── 本文生成・published 仕上げ ────────────────────────────────
def test_make_published_books_all_published_with_body():
    """予約制廃止改定: make_published_books が全4冊を本文付き published にする（一気通貫の仕上げ）。"""
    res = _run()
    books, personas = map_mode_a_set_to_books(res, owner_uid="u_x", created_at=NOW.isoformat())
    # 変換直後はまだ draft（マッピング層は変更なし）。
    assert all(b.status == "draft" for b in books)

    published = make_published_books(books, personas, llm="mock", rounds=1)
    assert len(published) == 4
    for b in published:
        assert b.status == "published", f"{b.id}: expected published"
        assert b.body, f"{b.id}: body must be non-empty"
        assert b.edit_round >= 1


def test_make_published_books_idempotent():
    """すでに published+body な本は素通しされる（冪等）。"""
    res = _run()
    books, personas = map_mode_a_set_to_books(res, owner_uid="u_x", created_at=NOW.isoformat())
    first_pass = make_published_books(books, personas, llm="mock", rounds=1)
    second_pass = make_published_books(first_pass, personas, llm="mock", rounds=1)
    assert [b.id for b in first_pass] == [b.id for b in second_pass]
    assert [b.body for b in first_pass] == [b.body for b in second_pass]


# ── 決定性 ─────────────────────────────────────────────────
def test_set_pipeline_deterministic():
    a = map_mode_a_set_to_books(_run(), owner_uid="u_x", created_at=NOW.isoformat())[0]
    b = map_mode_a_set_to_books(_run(), owner_uid="u_x", created_at=NOW.isoformat())[0]
    assert [x.id for x in a] == [x.id for x in b]
    assert [x.title for x in a] == [x.title for x in b]
