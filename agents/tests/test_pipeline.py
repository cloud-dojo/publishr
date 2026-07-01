"""企画会議パイプラインのテスト（オフライン・決定的）。"""

from __future__ import annotations

from publishr_agents import canned
from publishr_agents.authoring import write_body
from publishr_agents.pipeline import run_pipeline


def test_pipeline_produces_arrivals():
    result = run_pipeline("u_sakura")
    assert len(result.books) >= 2
    assert all(b.status == "draft" for b in result.books)
    assert all(b.shelf == "arrivals" for b in result.books)
    assert {p.id for p in result.plans} == set(result.approved_plan_ids)
    assert {b.plan_id for b in result.books} == set(result.approved_plan_ids)


def test_pipeline_exposes_reader_analysis():
    result = run_pipeline("u_sakura")
    assert result.observation.note_count > 0
    assert "年上部下との距離感" in result.observation.signals
    assert "マーケティング課長" in result.reader_profile.role
    assert "7名" in result.reader_profile.situation


def test_reject_then_resubmit_logged():
    """基準1: 全却下→再提出が1回起き、再提出後に採用が出るログが残る。"""
    result = run_pipeline("u_sakura")
    round1 = [e for e in result.reject_log if e.round == 1]
    round2 = [e for e in result.reject_log if e.round == 2]
    assert round1, "R1のログがある"
    assert all(e.verdict == "却下" for e in round1), "R1は全却下"
    assert any(e.verdict == "採用" for e in round2), "R2で採用が出る"


def test_selection_uses_planning_candidates():
    result = run_pipeline("u_sakura")
    candidate_names = {c.candidate for c in result.candidates}
    assert len(candidate_names) == 3
    assert {e.candidate for e in result.reject_log} == candidate_names
    assert set(result.approved_plan_ids) == {
        c.plan_id for c in result.candidates if c.plan_id and c.candidate in {
            e.candidate for e in result.reject_log if e.round == 2 and e.verdict == "採用"
        }
    }


def test_hero_plan_approved():
    result = run_pipeline("u_sakura")
    assert any(p.id == "plan_makase" for p in result.plans)


def test_deterministic():
    """同じ入力で同じ出力（再現可能）。"""
    a = run_pipeline("u_sakura")
    b = run_pipeline("u_sakura")
    assert [e.verdict for e in a.reject_log] == [e.verdict for e in b.reject_log]
    assert {bk.id for bk in a.books} == {bk.id for bk in b.books}


def test_authoring_body_for_hero():
    result = run_pipeline("u_sakura")
    hero = next(b for b in result.books if b.id == "b_makasekata")
    body = write_body(hero)
    assert "権限の設計図" in body
    assert len(body) > 100


def test_author_agenda_uses_plan_and_persona_voice():
    result = run_pipeline("u_sakura")
    toi = next(b for b in result.books if b.plan_id == "plan_toi")
    assert "現場に答えがある" in toi.preface_sample
    assert [item.no for item in toi.agenda] == ["はじめに", "1章", "2章", "3章", "4章", "おわりに"]
    assert [item.title for item in toi.agenda] == [
        "はじめに",
        "「問い」の三つの型",
        "朝会を、問いの場に変える",
        "フィードバックを問いに変える",
        "任せる問いをチームに残す",
        "おわりに",
    ]


def test_cover_variant_assigned_from_plan_and_persona():
    assert canned.cover_variant_for("plan_makase", "p_kirishima", "30人を、ひとりで背負わない。") == "b1"
    assert canned.cover_variant_for("plan_toi", "p_azumi", '"問い"で動かす現場') == "b2"
    fallback = canned.cover_variant_for("plan_unknown", "p_unknown", "未知の本")
    assert fallback.startswith("b") and 1 <= int(fallback[1:]) <= 10
    result = run_pipeline("u_sakura")
    variants = {b.plan_id: b.cover_variant for b in result.books}
    assert variants == {"plan_makase": "b1", "plan_toi": "b2"}
