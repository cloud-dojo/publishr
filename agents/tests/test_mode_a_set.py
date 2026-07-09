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
    publish_books_with_log,
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
    # 4テーマ＝4つの別企画。proposal_id は全て非None かつ一意（I-39: None だと
    # PipelineResult が落ち persona_id が cast_None になる＝決定的/vertex 両経路で担保）。
    plan_ids = [mb.plan.proposal_id for mb in res.books]
    assert all(plan_ids), f"proposal_id must be non-None: {plan_ids}"
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


def test_publish_books_with_log_editing_evidence():
    """publish_books_with_log が books に加え、冊ごとの編集ループ証跡（editing_log）を返す。

    Langfuse editing_loop 配線（C5.6 対立②）のライブ経路用: bookId/rounds/forcedApprove が
    write_body_loop の verdicts から冊ごとに残る。books は make_published_books と同一。
    """
    res = _run()
    books, personas = map_mode_a_set_to_books(res, owner_uid="u_x", created_at=NOW.isoformat())
    published = publish_books_with_log(books, personas, llm="mock", rounds=1)
    baseline = make_published_books(books, personas, llm="mock", rounds=1)
    assert [b.id for b in published.books] == [b.id for b in baseline]
    assert [b.body for b in published.books] == [b.body for b in baseline]
    assert len(published.editing_log) == 4
    for entry, book in zip(published.editing_log, published.books):
        assert entry["bookId"] == book.id
        assert entry["title"] == book.title
        assert entry["rounds"], f"{book.id}: 編集ループのラウンド証跡が必要"
        first_round = entry["rounds"][0]
        assert first_round["round"] == 1
        assert "score" in first_round and "decision" in first_round
        assert isinstance(entry["forcedApprove"], bool)
        assert entry["editRounds"] >= 1


def test_publish_books_with_log_passthrough_leaves_no_log():
    """既に published+body の本は編集ループを回さない＝証跡も残らない（冪等と整合）。"""
    res = _run()
    books, personas = map_mode_a_set_to_books(res, owner_uid="u_x", created_at=NOW.isoformat())
    first = publish_books_with_log(books, personas, llm="mock", rounds=1)
    second = publish_books_with_log(first.books, personas, llm="mock", rounds=1)
    assert [b.id for b in second.books] == [b.id for b in first.books]
    assert second.editing_log == []


# ── 決定性 ─────────────────────────────────────────────────
def test_set_pipeline_deterministic():
    a = map_mode_a_set_to_books(_run(), owner_uid="u_x", created_at=NOW.isoformat())[0]
    b = map_mode_a_set_to_books(_run(), owner_uid="u_x", created_at=NOW.isoformat())[0]
    assert [x.id for x in a] == [x.id for x in b]
    assert [x.title for x in a] == [x.title for x in b]


# ── お気に入り「配本ごと約25%で1冊」起用（確率ゲートは mode_a が握る） ────────────
_FAV = {
    "personaId": "fav_demo_1", "name": "推し 作家",
    "voiceStyle": "思想的・哲学的", "format": "エッセイ形式", "savedAt": "t",
}


def _user_with_favorite():
    return _user().model_copy(update={"favorite_authors": [_FAV]})


def test_favorite_featured_exactly_one_book_when_open():
    """当たり配本（pct=100）でも4冊中1冊だけがお気に入り＝占有しない。登録IDを保持（★継続）。"""
    res = run_mode_a_set_pipeline(
        _user_with_favorite(), source=FixtureObservationSource(), now=NOW, favorite_pct=100
    )
    fav_books = [mb for mb in res.books if mb.personas and mb.personas[0].from_favorite]
    assert len(fav_books) == 1
    assert fav_books[0].personas[0].persona_id == "fav_demo_1"  # 登録IDを保持
    # 4冊とも著者は別（お気に入り1＋通常3）
    author_ids = [mb.personas[0].persona_id for mb in res.books]
    assert len(set(author_ids)) == 4


def test_favorite_not_featured_when_closed():
    """外れ配本（pct=0）はお気に入りゼロ＝お気に入り未登録時と同じ4冊。"""
    res = run_mode_a_set_pipeline(
        _user_with_favorite(), source=FixtureObservationSource(), now=NOW, favorite_pct=0
    )
    assert all(not (mb.personas and mb.personas[0].from_favorite) for mb in res.books)
    author_ids = [mb.personas[0].persona_id for mb in res.books]
    assert len(set(author_ids)) == 4


def test_empty_favorites_zero_diff_from_baseline():
    """お気に入り未登録は従来どおり（4冊・全て通常著者・cast_<plan_id>）。"""
    res = run_mode_a_set_pipeline(_user(), source=FixtureObservationSource(), now=NOW)
    assert all(not (mb.personas and mb.personas[0].from_favorite) for mb in res.books)


def test_favorite_feature_deterministic_per_seed():
    u = _user_with_favorite()
    a = run_mode_a_set_pipeline(u, source=FixtureObservationSource(), now=NOW, seed="run-xyz")
    b = run_mode_a_set_pipeline(u, source=FixtureObservationSource(), now=NOW, seed="run-xyz")
    assert [mb.personas[0].persona_id for mb in a.books] == [mb.personas[0].persona_id for mb in b.books]


# ── C1.8 学習ループ: set 縦串にも past_books が届く（読者分析への配線） ──────────
def _past_published_book() -> Book:
    """過去配本の1冊に★5の反応が付いた体の published 本を作る。"""
    book = map_mode_a_set_to_books(_run(), owner_uid="u_x", created_at=NOW.isoformat())[0][0]
    fb = book.feedback.model_copy(update={"rating": 5})
    return book.model_copy(update={"status": "published", "feedback": fb})


def test_set_pipeline_feeds_past_books_to_reader(monkeypatch):
    """set 縦串でも過去本の反応が読者分析へ渡り、readingBehavior に織り込まれる（C1.8）。"""
    import publishr_agents.reader as reader_mod

    captured: dict = {}
    orig = reader_mod.analyze_reader

    def spy(observation, **kwargs):
        profile = orig(observation, **kwargs)
        captured["past_books"] = kwargs.get("past_books")
        captured["profile"] = profile
        return profile

    monkeypatch.setattr(reader_mod, "analyze_reader", spy)
    past = [_past_published_book()]
    run_mode_a_set_pipeline(_user(), source=FixtureObservationSource(), now=NOW, past_books=past)

    assert captured["past_books"] == past
    behavior = captured["profile"].reading_behavior
    assert "過去1冊の反応" in behavior.feedback_summary  # 反応サマリが織り込まれる
    assert behavior.recent_reads == [past[0].title]      # 既読＝次サイクルの被り回避材料
