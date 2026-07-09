"""v2 エージェントI/Oモデル（agent_io）の妥当性テスト（P0bシーム）。

プロンプト .md の良い出力例 JSON が camelCase で読め、snake_case でアクセスでき、
round-trip で camelCase に戻ることを確認する。
"""

from __future__ import annotations

from publishr_schema import (
    BodyVerdict,
    BookDraft,
    EditorVerdict,
    GeneratedPersonaSet,
    LeaderVerdict,
    PlanProposal,
    ReaderProfile3Layer,
    SubMarket,
)


def test_plan_proposal_camel_roundtrip():
    p = PlanProposal.model_validate(
        {
            "tentativeTitle": "T",
            "readerSituation": "S",
            "whyNowForYou": "W",
            "coreMessage": "C",
            "diffFromMarket": "D",
            "keyInsights": ["a"],
            "agendaOutline": ["x"],
            "recommendedAuthorTypes": ["y"],
        }
    )
    assert p.tentative_title == "T"
    assert p.diff_from_market == "D"
    assert p.model_dump(by_alias=True)["tentativeTitle"] == "T"


def test_leader_verdict_nested_alias_and_nested_plan():
    v = LeaderVerdict.model_validate(
        {
            "round": 1,
            "score": 86,
            "scoreBreakdown": {
                "relevance": 24,
                "differentiation": 22,
                "researchUse": 21,
                "titleHook": 19,
            },
            "belowFloor": False,
            "decision": "approve",
            "approvedPlan": {
                "tentativeTitle": "T",
                "readerSituation": "S",
                "whyNowForYou": "W",
                "coreMessage": "C",
                "diffFromMarket": "D",
            },
        }
    )
    assert v.score_breakdown.research_use == 21
    assert v.decision == "approve"
    assert v.approved_plan is not None
    assert v.approved_plan.tentative_title == "T"


def test_persona_set_and_book_draft_and_verdicts():
    s = GeneratedPersonaSet.model_validate(
        {
            "planId": "plan_misa_01",
            "themeKind": "honmei",
            "personas": [
                {"personaId": "p1", "name": "神崎 玄一郎", "voiceStyle": "ロジカル", "format": "自己啓発"}
            ],
            "reason": "2軸で散らした",
        }
    )
    assert s.personas[0].persona_id == "p1"
    assert s.personas[0].ephemeral is True

    b = BookDraft.model_validate(
        {"title": "X", "agenda": [{"chapter": "01", "summary": "s"}], "prefaceSample": "p"}
    )
    assert b.agenda[0].chapter == "01"
    assert b.preface_sample == "p"

    ev = EditorVerdict.model_validate(
        {
            "round": 1,
            "score": 70,
            "scoreBreakdown": {"rawInsight": 24, "personaForward": 23, "catchiness": 23},
            "decision": "approve",
        }
    )
    assert ev.score_breakdown.raw_insight == 24

    bv = BodyVerdict.model_validate(
        {
            "score": 84,
            "scoreBreakdown": {
                "coherence": 17,
                "hook": 16,
                "relevance": 18,
                "personaConsistency": 17,
                "actionability": 16,
            },
            "decision": "approve",
            "weakChapters": [],
        }
    )
    assert bv.score_breakdown.persona_consistency == 17
    assert bv.weak_chapters == []


def test_reader_profile_three_layers_and_submarket():
    r = ReaderProfile3Layer.model_validate(
        {
            "base": {"industry": "food", "jobType": "mkt", "orgScale": "7名"},
            "currentWork": {"currentSituation": "新任2ヶ月"},
            "readingBehavior": {"serendipityTolerance": "mid"},
        }
    )
    assert r.base.job_type == "mkt"
    assert r.current_work.current_situation == "新任2ヶ月"
    assert r.reading_behavior.serendipity_tolerance == "mid"

    m = SubMarket.model_validate(
        {
            "theme": "t",
            "queries": ["q"],
            "findings": [{"title": "a", "point": "b", "source": "u"}],
            "marketGap": "g",
        }
    )
    assert m.market_gap == "g"
    assert m.findings[0].source == "u"
