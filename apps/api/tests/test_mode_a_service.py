"""BFF モードAサービス（観測→…→装丁→arrivals永続）のテスト。

mock LLM 既定＝決定的・課金ゼロ。書店「入荷(arrivals/draft)」へ永続し、
企画会議の却下→採用の証跡（reject_log）を返すことを押さえる。
"""

from __future__ import annotations

import pytest
from publishr_api.errors import NotFoundError
from publishr_api.repositories.mock_repository import MockRepository
from publishr_api.services import mode_a_service


def test_run_writes_books_published_with_body_and_returns_reject_log():
    """企画したら本文まで自動執筆（mock は同期）＝ books は published＋body 付きで入荷される。"""
    repo = MockRepository()
    result = mode_a_service.run(repo, "u_sakura", owner_uid="uid_demo")

    assert len(result.books) >= 1
    for book in result.books:
        b = book.model_dump(by_alias=True)
        assert b["shelf"] == "arrivals"
        assert b["status"] == "published"  # 自動執筆で draft→published
        assert b["body"]  # 本文が書かれている（手動予約なし）
        assert b["ownerUid"] == "uid_demo"

    # 永続（冪等 upsert）されている＝ get_book で published・body 付きで引ける。
    first = result.books[0]
    persisted = repo.get_book(first.id)
    assert persisted.id == first.id and persisted.status == "published" and persisted.body

    # 採用企画ID と本の planId が整合。
    assert result.approved_plan_ids
    book_plan_ids = {bk.model_dump(by_alias=True)["planId"] for bk in result.books}
    assert book_plan_ids <= set(result.approved_plan_ids)

    # 却下→採用の証跡（基準1の画）。
    assert any(e.round == 1 and e.verdict == "却下" for e in result.reject_log)
    assert any(e.round == 2 and e.verdict == "採用" for e in result.reject_log)


def test_run_owner_uid_defaults_to_user_id():
    repo = MockRepository()
    result = mode_a_service.run(repo, "u_sakura")
    assert all(b.model_dump(by_alias=True)["ownerUid"] == "u_sakura" for b in result.books)


def test_run_is_deterministic_in_mock():
    r1 = mode_a_service.run(MockRepository(), "u_sakura", owner_uid="u")
    r2 = mode_a_service.run(MockRepository(), "u_sakura", owner_uid="u")
    assert [b.title for b in r1.books] == [b.title for b in r2.books]


def test_run_unknown_user_raises():
    with pytest.raises(NotFoundError):
        mode_a_service.run(MockRepository(), "u_does_not_exist")


# ── v3 4テーマ配本（予約制廃止改定 2026-06-23・既定 set_pipeline=True）──
def test_run_set_pipeline_yields_four_books():
    repo = MockRepository()
    result = mode_a_service.run(repo, "u_sakura", owner_uid="uid_demo")
    assert len(result.books) == 4                       # 4テーマ＝4冊（1-1-1-1）
    assert len(set(result.approved_plan_ids)) == 4      # 4企画が承認
    assert len({b.id for b in result.books}) == 4       # book id が4冊で別
    # セットゲートの差し戻し→承認（編集長）の証跡。
    assert any(e.round == 1 and e.verdict == "却下" and e.persona == "編集長" for e in result.reject_log)
    assert any(e.round == 2 and e.verdict == "採用" for e in result.reject_log)


def test_run_set_pipeline_books_are_published_with_body():
    """予約制廃止改定: set pipeline は全4冊を本文付き published で配本する（予約不要・一気通貫）。"""
    repo = MockRepository()
    result = mode_a_service.run(repo, "u_sakura", owner_uid="uid_demo")
    for book in result.books:
        assert book.status == "published", f"{book.id}: status should be published, got {book.status}"
        assert book.body, f"{book.id}: body should be non-empty"
        assert book.edit_round >= 1, f"{book.id}: edit_round should be >= 1"
    # repo に格納された本も published になっている（persist は after publish）
    for book in result.books:
        stored = repo.get_book(book.id)
        assert stored is not None
        assert stored.status == "published"
        assert stored.body


def test_run_set_pipeline_passes_past_feedback_books_to_reader(monkeypatch):
    """C1.8 学習ループ: 既定の set 経路でも repo の反応付き published 本が読者分析へ渡る。

    反応の無い本は除外・他 owner の本も除外（旧・単一テーマ経路と同じ絞り込み）。
    """
    from publishr_agents.reader.preferences import has_feedback

    repo = MockRepository()
    first = mode_a_service.run(repo, "u_sakura", owner_uid="uid_demo")
    target = first.books[0]
    fb = target.feedback.model_copy(update={"rating": 5})
    repo.upsert_book(target.model_copy(update={"feedback": fb}))
    # 他 owner の反応付き本は絞り込みで除外される。
    repo.upsert_book(
        target.model_copy(update={"id": "b_other_owner", "owner_uid": "uid_other", "feedback": fb})
    )

    captured: dict = {}
    orig = mode_a_service.run_mode_a_set_pipeline

    def spy(user, **kwargs):
        captured["past_books"] = kwargs.get("past_books")
        return orig(user, **kwargs)

    monkeypatch.setattr(mode_a_service, "run_mode_a_set_pipeline", spy)
    mode_a_service.run(repo, "u_sakura", owner_uid="uid_demo")

    past = captured.get("past_books") or []
    assert any(b.id == target.id for b in past), "反応が付いた自分の本が読者分析へ渡る"
    assert all(b.id != "b_other_owner" for b in past), "他 owner の本は渡らない"
    assert all(has_feedback(b) for b in past), "反応の無い本は含めない"


def test_run_set_pipeline_includes_annotation_only_books(monkeypatch):
    """C1.8: 反応ゼロでもハイライト/しおりが付いた本は past_books に含まれる。"""
    from publishr_schema import ReadingAnnotation

    repo = MockRepository()
    first = mode_a_service.run(repo, "u_sakura", owner_uid="uid_demo")
    annotated = first.books[0].model_copy(update={
        "annotations": [
            ReadingAnnotation(id="a1", kind="highlight", paragraph_index=0, text="刺さった一文")
        ],
    })
    repo.upsert_book(annotated)

    captured: dict = {}
    orig = mode_a_service.run_mode_a_set_pipeline

    def spy(user, **kwargs):
        captured["past_books"] = kwargs.get("past_books")
        return orig(user, **kwargs)

    monkeypatch.setattr(mode_a_service, "run_mode_a_set_pipeline", spy)
    mode_a_service.run(repo, "u_sakura", owner_uid="uid_demo")

    past = captured.get("past_books") or []
    assert any(b.id == annotated.id for b in past), "注釈のみの本も学習対象に入る"


def test_run_set_pipeline_past_books_recency_order_and_cap(monkeypatch):
    """C1.8: past_books は新しい順（last_read_at 優先）・上限 _PAST_BOOKS_MAX で渡す。"""
    repo = MockRepository()
    first = mode_a_service.run(repo, "u_sakura", owner_uid="uid_demo")
    fb = lambda b, ts: b.feedback.model_copy(update={"rating": 4, "last_read_at": ts})  # noqa: E731
    oldest = first.books[0].model_copy(
        update={"feedback": fb(first.books[0], "2026-06-20T00:00:00+09:00")}
    )
    older = first.books[1].model_copy(
        update={"feedback": fb(first.books[1], "2026-07-01T00:00:00+09:00")}
    )
    newer = first.books[2].model_copy(
        update={"feedback": fb(first.books[2], "2026-07-08T00:00:00+09:00")}
    )
    for b in (oldest, older, newer):
        repo.upsert_book(b)

    captured: dict = {}
    orig = mode_a_service.run_mode_a_set_pipeline

    def spy(user, **kwargs):
        captured["past_books"] = kwargs.get("past_books")
        return orig(user, **kwargs)

    monkeypatch.setattr(mode_a_service, "run_mode_a_set_pipeline", spy)
    monkeypatch.setattr(mode_a_service, "_PAST_BOOKS_MAX", 2)
    mode_a_service.run(repo, "u_sakura", owner_uid="uid_demo")

    past = captured["past_books"]
    assert [b.id for b in past] == [newer.id, older.id]  # 新しい順・上限2で oldest は落ちる


def test_run_legacy_flag_falls_back_to_single_theme(monkeypatch):
    """キルスイッチ PUBLISHR_SET_PIPELINE=0 で旧・単一テーマ経路に戻る（ロールバック可）。"""
    monkeypatch.setattr(mode_a_service.settings, "set_pipeline", False)
    result = mode_a_service.run(MockRepository(), "u_sakura", owner_uid="uid_demo")
    assert len(result.approved_plan_ids) == 1           # 旧経路＝単一企画
    assert all(b.model_dump(by_alias=True)["shelf"] == "arrivals" for b in result.books)


def test_autowrite_failure_degrades_to_draft(monkeypatch):
    """自動執筆の投入失敗（cap 超過等）は握って draft のまま＝企画全体は成功する（旧単一テーマ経路）。"""
    from publishr_api.errors import ConflictError
    from publishr_api.services import reservation_service

    monkeypatch.setattr(mode_a_service.settings, "set_pipeline", False)

    def boom(*args, **kwargs):
        raise ConflictError("同時予約上限")

    monkeypatch.setattr(reservation_service, "reserve_now", boom)
    repo = MockRepository()
    result = mode_a_service.run(repo, "u_sakura", owner_uid="u")
    assert len(result.books) >= 1  # 企画自体は成功
    assert repo.get_book(result.books[0].id).status == "draft"  # 執筆未投入＝draft 据え置き


# --- C1.1: 観測ソースの選択（実Google ⇄ fixture フォールバック）-------------------

from publishr_schema import ConnectedSources, DriveConnection, User, load_users  # noqa: E402


def _user_with_drive(folder_ids: list[str]) -> User:
    base = next(u for u in load_users() if u.id == "u_sakura")
    cs = ConnectedSources(drive=DriveConnection(enabled=True, folder_ids=folder_ids))
    return base.model_copy(update={"connected_sources": cs})


def _user_no_sources() -> User:
    base = next(u for u in load_users() if u.id == "u_sakura")
    return base.model_copy(update={"connected_sources": None})


def test_source_is_fixture_by_default(monkeypatch):
    from publishr_api import config

    monkeypatch.setattr(config.settings, "observe", "fixture")
    src = mode_a_service._observation_source(_user_with_drive(["f1"]), "uid1")
    assert type(src).__name__ == "FixtureObservationSource"  # 既定は常に fixture（mock不変）


def test_source_is_google_when_connected_with_token(monkeypatch):
    from publishr_api import config

    monkeypatch.setattr(config.settings, "observe", "google")
    monkeypatch.setattr(mode_a_service, "_google_credentials", lambda uid: object())
    src = mode_a_service._observation_source(_user_with_drive(["f1"]), "uid1")
    assert type(src).__name__ == "GoogleObservationSource"


def test_source_falls_back_to_fixture_without_token(monkeypatch):
    from publishr_api import config

    monkeypatch.setattr(config.settings, "observe", "google")
    monkeypatch.setattr(mode_a_service, "_google_credentials", lambda uid: None)  # 連携トークン無し
    src = mode_a_service._observation_source(_user_with_drive(["f1"]), "uid1")
    assert type(src).__name__ == "FixtureObservationSource"


def test_source_falls_back_to_fixture_when_not_connected(monkeypatch):
    from publishr_api import config

    monkeypatch.setattr(config.settings, "observe", "google")
    monkeypatch.setattr(mode_a_service, "_google_credentials", lambda uid: object())
    src = mode_a_service._observation_source(_user_no_sources(), "uid1")
    assert type(src).__name__ == "FixtureObservationSource"  # 未接続→fixture


def test_source_falls_back_when_no_observe_uid(monkeypatch):
    from publishr_api import config

    monkeypatch.setattr(config.settings, "observe", "google")
    src = mode_a_service._observation_source(_user_with_drive(["f1"]), None)
    assert type(src).__name__ == "FixtureObservationSource"  # uid 無し→fixture


def test_run_emits_langfuse_pipeline_trace(monkeypatch):
    """企画 run が Langfuse の trace_pipeline を planning_rounds（差し戻し→採用の証跡）付きで呼ぶ（旧単一テーマ経路）。"""
    import publishr_agents.observability as obs

    monkeypatch.setattr(mode_a_service.settings, "set_pipeline", False)

    captured: dict = {}

    def fake_trace(payload, **_kw):
        captured["payload"] = payload
        return "sent"

    monkeypatch.setattr(obs, "trace_pipeline", fake_trace)
    mode_a_service.run(MockRepository(), "u_sakura", owner_uid="u")
    assert "payload" in captured  # 計装が結線されている
    p = captured["payload"]
    assert p["approved"] is True
    assert isinstance(p["planning_rounds"], list) and len(p["planning_rounds"]) >= 1
