"""企画会議パイプラインのテスト（オフライン・決定的）。"""

from __future__ import annotations

from publishr_agents.authoring import write_body
from publishr_agents.pipeline import run_pipeline


def test_pipeline_produces_arrivals():
    result = run_pipeline("u_tadokoro")
    assert len(result.books) >= 4
    assert all(b.status == "draft" for b in result.books)
    assert all(b.shelf == "arrivals" for b in result.books)
    assert len(result.plans) >= 4


def test_pipeline_exposes_reader_analysis():
    result = run_pipeline("u_tadokoro")
    assert result.observation.note_count > 0
    assert "管掌範囲の拡大" in result.observation.signals
    assert "製造課長" in result.reader_profile.role
    assert "30名規模" in result.reader_profile.situation


def test_reject_then_resubmit_logged():
    """基準1: 全却下→再提出が1回起き、再提出後に採用が出るログが残る。"""
    result = run_pipeline("u_tadokoro")
    round1 = [e for e in result.reject_log if e.round == 1]
    round2 = [e for e in result.reject_log if e.round == 2]
    assert round1, "R1のログがある"
    assert all(e.verdict == "却下" for e in round1), "R1は全却下"
    assert any(e.verdict == "採用" for e in round2), "R2で採用が出る"


def test_hero_plan_approved():
    result = run_pipeline("u_tadokoro")
    assert any(p.id == "plan_makase" for p in result.plans)


def test_deterministic():
    """同じ入力で同じ出力（再現可能）。"""
    a = run_pipeline("u_tadokoro")
    b = run_pipeline("u_tadokoro")
    assert [e.verdict for e in a.reject_log] == [e.verdict for e in b.reject_log]
    assert {bk.id for bk in a.books} == {bk.id for bk in b.books}


def test_authoring_body_for_hero():
    result = run_pipeline("u_tadokoro")
    hero = next(b for b in result.books if b.id == "b_makasekata")
    body = write_body(hero)
    assert "権限の設計図" in body
    assert len(body) > 100
