"""BFF モードAサービス（観測→…→装丁→arrivals永続）のテスト。

mock LLM 既定＝決定的・課金ゼロ。書店「入荷(arrivals/draft)」へ永続し、
企画会議の却下→採用の証跡（reject_log）を返すことを押さえる。
"""

from __future__ import annotations

import pytest
from publishr_api.errors import NotFoundError
from publishr_api.repositories.mock_repository import MockRepository
from publishr_api.services import mode_a_service


def test_run_persists_arrivals_and_returns_reject_log():
    repo = MockRepository()
    result = mode_a_service.run(repo, "u_sakura", owner_uid="uid_demo")

    assert len(result.books) >= 1
    for book in result.books:
        b = book.model_dump(by_alias=True)
        assert b["shelf"] == "arrivals"
        assert b["status"] == "draft"
        assert b["ownerUid"] == "uid_demo"

    # 永続（冪等 upsert）されている＝ get_book で引ける。
    first = result.books[0]
    assert repo.get_book(first.id).id == first.id

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


def test_run_legacy_flag_falls_back_to_single_theme(monkeypatch):
    """キルスイッチ PUBLISHR_SET_PIPELINE=0 で旧・単一テーマ経路に戻る（ロールバック可）。"""
    monkeypatch.setattr(mode_a_service.settings, "set_pipeline", False)
    result = mode_a_service.run(MockRepository(), "u_sakura", owner_uid="uid_demo")
    assert len(result.approved_plan_ids) == 1           # 旧経路＝単一企画
    assert all(b.model_dump(by_alias=True)["shelf"] == "arrivals" for b in result.books)
