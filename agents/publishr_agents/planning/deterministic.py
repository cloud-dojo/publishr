"""STEP2 企画3階層の決定的オフライン実装（PUBLISHR_LLM=mock・既定）。

ReaderProfile から仮テーマを立て、3観点の調査サブ（canned）→企画担当者（PlanProposal 8項目）
→企画リーダー（スコア差し戻しループ）を決定的に回し、reject→再提出→approve の証跡を残す。
本格的な grounding・採点は実Vertex（vertex_agent）が担う。返り値は miniloop と同形の dict。
正本: docs/design/agent-io-contract.md §4 / packages/prompts/step2_*.md。
"""

from __future__ import annotations

from typing import Any, Optional

from publishr_schema import (
    EditorialIntent,
    LeaderVerdict,
    PerPlanScore,
    PlanProposal,
    PlanSet,
    PlanSetVerdict,
    PortfolioScore,
    ReaderProfile3Layer,
    SubMarket,
    SubReaderContext,
    SubThemeInsight,
    SubTrendInsight,
    ThemeAssignment,
    ThemeAssignmentSet,
    ThemeSpec,
    TrendPoint,
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
    """関心の"隣"へずらした off-axis テーマ（距離2設計・2026-06-12検証で確定）。

    設計原則: テーマ文字列に読者の challenges 語彙（リーダーシップ/意思決定/マネジメント等の
    能力名詞）を含めず、主語を素材側（歴史・人物・出来事）に置く。局面との接点は
    サブA（同型対応）と owner（章立ての内部材料）が後段で架けるため、テーマが先回りしない。
    読者ごとの個人化（関心グラフからの導出）はハッカソン後スコープ。
    """
    return "国や組織は、なぜ栄え、なぜ滅びるのか——興亡の歴史に学ぶ（教養としての一冊）"


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


# ══════════════════════════════════════════════════════════════════════════
# v3 4テーマ1-1-1-1 セット企画（決定的・予約制廃止改定 2026-06-23）
#   editor_chief_themes(4テーマ) → 各チーム[調査トリオ(今/市場/普遍)→plan] → editor_chief_gate(セット採点)
#   旧 run_planning_deterministic（単一テーマ）は温存。本関数は additive な新パス。
# ══════════════════════════════════════════════════════════════════════════

# 4テーマの多様性4軸（theme/形式/効用/トーン）を決定的に散らす（axisSpread=4 を作る）。
_ROLES_4 = ["主軸", "実務補助", "視座替え", "回復・内省"]
_BOOK_ROLES_4 = ["ハンドブック", "ケース・ストーリー", "対話", "内省エッセイ"]
_UTILITIES_4 = ["すぐ使える", "すぐ使える", "視座が広がる", "抱え込みがほどける"]
_TONES_4 = ["冷静な緊張感", "覚悟を促す現実直視", "知的で俯瞰的", "静かな内省"]
# セット総合スコア（round1<70=弱い冊を差し戻し → round2 で承認。棚を空にしない）。
_SET_SCORES = [61, 84]


def derive_theme_set(profile: ReaderProfile3Layer, theme_kind: str = "honmei") -> ThemeAssignmentSet:
    """ReaderProfile から4サブテーマ（1-1-1-1）と編集意図を決定的に立てる。

    honmei は activeWorkThemes 先頭を主軸に据え、上位4件を4チームへ割当（不足は derive_theme で補完）。
    多様性4軸（role/形式/効用/トーン）を散らす設計は配本属性側（_plan_set_item）で担保する。
    """
    cw = profile.current_work
    src = list(cw.active_work_themes) if cw and cw.active_work_themes else []
    src += list(cw.challenges) if cw and cw.challenges else []
    names: list[str] = []
    for s in src:                       # 重複しない4テーマを確保（antiDuplication）
        if s and s not in names:
            names.append(s)
    while len(names) < 4:
        names.append(f"{_niche(profile)}の局面{len(names) + 1}")
    names = names[:4]
    assignments = [
        ThemeAssignment(
            team_id=team,
            theme=ThemeSpec(
                theme_id=f"theme_{team}",
                name=name,
                role=_ROLES_4[i],
                target_reader=_niche(profile),
                value=f"{name}に対して『{_UTILITIES_4[i]}』を届ける",
                forbidden_overlap="他チームに割り当てられたテーマ領域は主題にしない",
            ),
        )
        for i, (team, name) in enumerate(zip("ABCD", names))
    ]
    intent = EditorialIntent(
        shelf_concept=(
            f"『{_niche(profile)}』の複数局面を、すぐ使える型・一段引いた視座・抱え込みをほどく内省を"
            "混ぜて立体的に考えさせる棚（裏は一貫・表は多様）"
        ),
        reader_experience="明日すぐ使える型を1つ持ち帰りつつ、視座の転換と少しの落ち着きが残る",
        anti_duplication=[
            "同じ問題設定を2テーマ以上の主題にしない",
            "ハウツー偏重を避け、視座替えと内省・回復を必ず混ぜる",
        ],
        balance_constraints=[
            "効用は『すぐ使える』と『視座が広がる/抱え込みがほどける』を必ず両方入れる",
            "感情トーンは同一を3テーマ以上続けない",
            "4テーマがテーマ/形式/効用/トーンの4軸で最低3軸はバラける",
        ],
    )
    return ThemeAssignmentSet(theme_kind=theme_kind, editorial_intent=intent, assignments=assignments)


def _research_trio(profile: ReaderProfile3Layer, theme: str) -> dict[str, dict]:
    """調査トリオ（今＝SubTrendInsight / 市場＝SubMarket / 普遍＝SubThemeInsight）を決定的に返す。"""
    sub_trend = SubTrendInsight(
        theme=theme,
        queries=[f"{theme} トレンド 2025", f"{theme} 最近 動向"],
        trends=[TrendPoint(point=f"{theme}を取り巻く前提が直近で変わり、関心が高まっている", source="")],
        era_shift=f"{theme}の捉え方が『個人の頑張り』から『構造で解く』へ移りつつある",
    )
    sub_market = SubMarket(
        theme=theme,
        queries=[f"{theme} 書籍 2025 売れ筋", f"{theme} 事例 本"],
        findings=[
            {
                "title": "（市販の一般向け実践書）",
                "point": f"{theme}を一般論で扱い、対象は限定しない",
                "source": "",
            }
        ],
        market_gap=f"売れ筋は一般論。本書は『{_niche(profile)}』の固有局面に絞る＝差別化余地",
    )
    sub_theme = SubThemeInsight(
        theme=theme,
        key_points=[
            {"point": f"{theme}の本質＝段階を構造で設計すること（古典的原理）", "source": ""},
            {"point": "相手の経験・立場に応じた関わり方の調整（歴史的に繰り返される本質）", "source": ""},
        ],
    )
    return {
        "subTrend": sub_trend.model_dump(by_alias=True),
        "subMarket": sub_market.model_dump(by_alias=True),
        "subThemeInsight": sub_theme.model_dump(by_alias=True),
    }


def _plan_set_item(
    profile: ReaderProfile3Layer, assignment: ThemeAssignment, idx: int, theme_kind: str, rnd: int, market_gap: str
) -> PlanProposal:
    cw = profile.current_work
    ts = assignment.theme
    upcoming = cw.upcoming_key_events[0].title if cw and cw.upcoming_key_events else ts.name
    situation = cw.current_situation if cw and cw.current_situation else f"{ts.name}に直面する局面"
    return PlanProposal(
        proposal_id=f"plan_det_{assignment.team_id}",
        theme_kind=theme_kind,  # type: ignore[arg-type]
        round=rnd,
        theme=ts.name,
        theme_role=ts.role,
        book_role=_BOOK_ROLES_4[idx],
        utility=_UTILITIES_4[idx],
        emotional_tone=_TONES_4[idx],
        target_segment=ts.target_reader,
        tentative_title=f"{ts.name}——いま、どこから手をつけるか",
        reader_situation=situation,
        why_now_for_you=f"いま「{upcoming}」を控え、{ts.name}の判断軸が要るから。",
        core_message=f"{ts.name}を『型』として持ち、迷いを判断に変える。",
        diff_from_market=f"{market_gap}（subMarket の marketGap を反映）",
        key_insights=[f"{ts.name}の段階設計", "経験・立場に応じた関わり方の調整"],
        agenda_outline=["現状の言語化", "型の提示", "局面別の適用", "次の一歩"],
        recommended_author_types=["実務家タイプ", "対話・コーチング型"],
    )


def _gate_set(plans: list[PlanProposal], *, approve: bool, threshold: int, rnd: int) -> PlanSetVerdict:
    """編集長セットゲート（決定的）。round1=弱い1冊を差し戻し、round2=全冊承認。

    portfolio は配本属性が4軸で散る前提で axisSpread=4・allocation_ok=True を立てる。
    """
    if approve:
        per_plan = [
            PerPlanScore(
                plan_id=p.proposal_id, score=[88, 82, 80, 79][i],
                score_breakdown={"relevance": 22, "differentiation": 20, "researchUse": 20, "titleHook": 18},
                below_floor=False, decision="approve",
            )
            for i, p in enumerate(plans)
        ]
        score = _SET_SCORES[1]
        return PlanSetVerdict(
            round=rnd, per_plan=per_plan,
            portfolio=PortfolioScore(axis_spread=4, constraints_ok=True, intent_alignment=22, allocation_ok=True),
            score=score, decision="approve", rejection_feedback=None, approved_plans=plans,
        )
    # round1: 4冊目を弱く（足切り）→ セット差し戻し（弱い冊のみ revise・健全冊は温存）
    per_plan = [
        PerPlanScore(
            plan_id=p.proposal_id, score=[72, 70, 68, 41][i],
            score_breakdown=(
                {"relevance": 8, "differentiation": 11, "researchUse": 11, "titleHook": 11} if i == 3
                else {"relevance": 19, "differentiation": 17, "researchUse": 18, "titleHook": 18}
            ),
            below_floor=(i == 3), decision=("revise" if i == 3 else "approve"),
        )
        for i, p in enumerate(plans)
    ]
    return PlanSetVerdict(
        round=rnd, per_plan=per_plan,
        portfolio=PortfolioScore(axis_spread=4, constraints_ok=True, intent_alignment=20, allocation_ok=True),
        score=_SET_SCORES[0], decision="revise",
        rejection_feedback=(
            f"4冊目（{plans[3].proposal_id}）の①読者局面の的中が足切り（8点）。"
            "割当テーマの固有局面に踏み込み、③marketGap を引いて差別化を作り直すこと。他3冊は採用可。"
        ),
        approved_plans=None,
    )


def run_planning_set_deterministic(
    profile: ReaderProfile3Layer,
    *,
    theme_kind: str = "honmei",
    threshold: int = _DEFAULT_THRESHOLD,
) -> dict[str, Any]:
    """4テーマ1-1-1-1のセット企画を決定的に回す（オフライン土台）。

    返り値: themeAssignmentSet / planSet / planSetVerdict / research（テーマ別トリオ）/
    rounds / verdictHistory / rejectLog（却下→再提出→承認の証跡）。
    """
    tas = derive_theme_set(profile, theme_kind)
    research = {a.team_id: _research_trio(profile, a.theme.name) for a in tas.assignments}
    market_gaps = {tid: r["subMarket"]["marketGap"] for tid, r in research.items()}

    verdict_history: list[dict] = []
    reject_log: list[dict] = []
    approved_plans: Optional[list[PlanProposal]] = None
    final_verdict: Optional[PlanSetVerdict] = None
    rounds = 0

    for rnd in (1, 2):
        rounds = rnd
        plans = [
            _plan_set_item(profile, a, i, theme_kind, rnd, market_gaps[a.team_id])
            for i, a in enumerate(tas.assignments)
        ]
        approve = _SET_SCORES[rnd - 1] >= threshold
        verdict = _gate_set(plans, approve=approve, threshold=threshold, rnd=rnd)
        final_verdict = verdict
        verdict_history.append({"round": rnd, "score": verdict.score, "decision": verdict.decision})
        if approve:
            approved_plans = plans
            break
        reject_log.append({
            "round": rnd,
            "rejectionFeedback": verdict.rejection_feedback,
            "belowFloor": [pp.plan_id for pp in verdict.per_plan if pp.below_floor],
        })

    plan_set = PlanSet(
        theme_kind=theme_kind,  # type: ignore[arg-type]
        editorial_intent=tas.editorial_intent,
        themes=[a.theme for a in tas.assignments],
        plans=approved_plans or [],
        allocation="1-1-1-1",
        portfolio_reason="多様性4軸（テーマ/形式/効用/トーン）で分散し、A社更新等の最重要案件は主題1テーマに限定",
    )
    return {
        "themeKind": theme_kind,
        "rounds": rounds,
        "verdictHistory": verdict_history,
        "rejectLog": reject_log,
        "themeAssignmentSet": tas.model_dump(by_alias=True),
        "planSet": plan_set.model_dump(by_alias=True),
        "planSetVerdict": final_verdict.model_dump(by_alias=True) if final_verdict else None,
        "research": research,
    }
