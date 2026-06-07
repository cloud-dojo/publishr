"""STEP2 企画3階層の決定的オフライン実装（PUBLISHR_LLM=mock・既定）。

ReaderProfile から仮テーマを立て、3観点の調査サブ（canned）→企画担当者（PlanProposal 8項目）
→企画リーダー（スコア差し戻しループ）を決定的に回し、reject→再提出→approve の証跡を残す。
本格的な grounding・採点は実Vertex（vertex_agent）が担う。返り値は miniloop と同形の dict。
正本: docs/design/agent-io-contract.md §4 / packages/prompts/step2_*.md。
"""

from __future__ import annotations

from typing import Any, Optional

from publishr_schema import (
    LeaderVerdict,
    PlanProposal,
    ReaderProfile3Layer,
    SubMarket,
    SubReaderContext,
    SubThemeInsight,
)

# 決定的なラウンド別スコア（round1<70=差し戻し → round2 で到達）。閾値で承認/強制を分岐。
_SCORES = [65, 82, 90]
_MAX_ROUNDS = 3
_DEFAULT_THRESHOLD = 70


def derive_theme(profile: ReaderProfile3Layer, theme_kind: str = "honmei") -> str:
    """ReaderProfile から仮テーマ（tentativeTheme）を立てる。

    honmei は currentWork の中心テーマ、serendipity は「関心の隣」（教養・歴史・哲学等）の
    関心外だが刺さりうるテーマを選ぶ（契約 §4・同一構造で themeKind 切替）。
    """
    if theme_kind == "serendipity":
        return _serendipity_theme(profile)
    cw = profile.current_work
    if cw and cw.active_work_themes:
        return cw.active_work_themes[0]
    if cw and cw.challenges:
        return cw.challenges[0]
    if profile.base and profile.base.position:
        return profile.base.position
    return "マネジメント"


def _serendipity_theme(profile: ReaderProfile3Layer) -> str:
    """関心の"隣"へずらした off-axis テーマ（橋渡し理由は owner が書く）。"""
    return "意思決定とリーダーシップを古典・歴史から問い直す（教養としての一冊）"


def _niche(profile: ReaderProfile3Layer) -> str:
    b = profile.base
    parts = [p for p in [b.industry if b else "", b.position if b else ""] if p]
    return "・".join(parts) or "この読者の局面"


def _subs(profile: ReaderProfile3Layer, theme: str) -> dict[str, dict]:
    cw = profile.current_work
    challenges = list(cw.challenges) if cw else []
    sub_reader = SubReaderContext(
        theme=theme,
        pain_points=challenges[:2] or [f"{theme}の実践で手が止まる具体ポイント"],
        decisions=[e.title for e in (cw.upcoming_key_events if cw else [])][:2],
        evidence=list(cw.evidence) if cw else [],
    )
    sub_market = SubMarket(
        theme=theme,
        queries=[f"{theme} 書籍 2025 売れ筋", f"{theme} 事例 本"],
        findings=[
            {
                "title": "（市販のマネジメント実践書・一般向け）",
                "point": f"{theme}を一般論で扱い、対象は一般のマネージャー全般",
                "source": "",
            }
        ],
        market_gap=f"売れ筋は一般論。本書は『{_niche(profile)}』の局面に限定して具体化＝差別化余地",
    )
    sub_theme = SubThemeInsight(
        theme=theme,
        key_points=[
            {"point": f"{theme}の段階設計（報告のみ／相談の上で実行／完全委任）", "source": ""},
            {"point": "相手の経験・立場に応じた関わり方の調整", "source": ""},
        ],
    )
    return {
        "subReaderContext": sub_reader.model_dump(by_alias=True),
        "subMarket": sub_market.model_dump(by_alias=True),
        "subThemeInsight": sub_theme.model_dump(by_alias=True),
    }


def _plan(profile: ReaderProfile3Layer, theme: str, theme_kind: str, rnd: int, market_gap: str) -> dict:
    cw = profile.current_work
    situation = (cw.current_situation if cw and cw.current_situation else f"{theme}に直面する局面")
    upcoming = cw.upcoming_key_events[0].title if cw and cw.upcoming_key_events else theme
    plan = PlanProposal(
        proposal_id=f"plan_det_{rnd}",
        theme_kind=theme_kind,  # type: ignore[arg-type]
        round=rnd,
        tentative_title=f"{theme}の設計図",
        reader_situation=situation,
        why_now_for_you=f"いま「{upcoming}」を控え、{theme}の判断軸が必要だから。",
        core_message=f"{theme}を『型』として持ち、迷いを判断に変える。",
        diff_from_market=f"{market_gap}（subMarket の marketGap を反映）",
        key_insights=[f"{theme}の段階設計", "経験・立場に応じた関わり方の調整"],
        agenda_outline=["現状の言語化", "型の提示", "局面別の適用", "次の一歩"],
        recommended_author_types=["実務家タイプ", "対話・コーチング型"],
    )
    return plan.model_dump(by_alias=True)


def run_planning_deterministic(
    profile: ReaderProfile3Layer,
    *,
    theme: Optional[str] = None,
    theme_kind: str = "honmei",
    threshold: int = _DEFAULT_THRESHOLD,
) -> dict[str, Any]:
    theme = theme or derive_theme(profile, theme_kind)
    subs = _subs(profile, theme)
    market_gap = subs["subMarket"]["marketGap"]

    verdict_history: list[dict] = []
    rejection_feedback: Optional[str] = None
    approved_plan: Optional[dict] = None
    forced_approve = False
    rounds = 0

    for rnd in range(1, _MAX_ROUNDS + 1):
        rounds = rnd
        score = _SCORES[rnd - 1]
        plan = _plan(profile, theme, theme_kind, rnd, market_gap)

        approve = score >= threshold
        if approve or rnd >= _MAX_ROUNDS:
            decision = "approve"
            forced_approve = not approve
            approved_plan = plan
            verdict_history.append({"round": rnd, "score": score, "decision": decision})
            break

        decision = "revise"
        if rejection_feedback is None:
            rejection_feedback = (
                "差別化(diffFromMarket)が弱い。subMarket の marketGap を引いて"
                "『市販本が構造的に出せない差分』を、この読者の固有局面に寄せて具体化して再提出。"
            )
        verdict_history.append({"round": rnd, "score": score, "decision": decision})

    return {
        "theme": theme,
        "themeKind": theme_kind,
        "rounds": rounds,
        "verdictHistory": verdict_history,
        "approvedPlan": approved_plan,
        "rejectionFeedback": rejection_feedback,
        "forced_approve": forced_approve,
        **subs,
    }
