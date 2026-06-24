"""STEP2 4テーマ・セット企画の実Vertex実装（PUBLISHR_LLM=vertex・PR-5）。

予約制廃止改定 2026-06-23 の 4テーマ1-1-1-1 配本を実LLMで回す：

  editor_chief_themes(Pro→ThemeAssignmentSet・4テーマ割当) →
    各チーム[ Parallel[sub_trend / sub_competitors / sub_classics（Google検索 grounding）]
             → plan_owner(Pro→PlanProposal) ] →
  editor_chief_gate(Pro→PlanSetVerdict・セット採点) →
    差し戻し時は弱い冊のみ再立案（最高3R・Python制御＝棚を空にしない）

`vertex_agent.py`（単一テーマ）は不変。再利用部品（plan_owner）は import のみ。
オフライン土台は `deterministic.run_planning_set_deterministic`。**実LLM・課金あり**。
正本: docs/design/agent-io-contract.md §4 / packages/prompts/step2_*.md。
"""

from __future__ import annotations

import asyncio
import warnings
from typing import Any, Optional

warnings.filterwarnings("ignore", category=DeprecationWarning, module="google.adk")

from google.adk.agents import LlmAgent, ParallelAgent, SequentialAgent  # noqa: E402
from google.adk.runners import InMemoryRunner  # noqa: E402
from google.adk.tools import google_search  # noqa: E402
from google.genai import types  # noqa: E402
from publishr_schema import (  # noqa: E402
    PlanProposal,
    PlanSet,
    PlanSetVerdict,
    ReaderProfile3Layer,
    ThemeAssignmentSet,
)

from .. import state_keys as K  # noqa: E402
from ..llm.provider import model_for  # noqa: E402
from ..prompts import loader, render  # noqa: E402
from .deterministic import _DEFAULT_THRESHOLD  # noqa: E402 — 既定閾値の単一情報源
from .vertex_agent import _plan_owner  # noqa: E402 — owner は新 step2_plan_owner テンプレ準拠で再利用

_APP_THEMES = "publishr_set_themes"
_APP_RESEARCH = "publishr_set_research"
_APP_OWNER = "publishr_set_owner"
_APP_GATE = "publishr_set_gate"
_MAX_ROUNDS = 3
# grounding（google_search）は生テキストが巨大になりうる。owner へ渡す前に各観点をこの上限で切り、
# プロンプトのトークン爆発（実測 153k tok で 400 INVALID_ARGUMENT）を防ぐ。
_MAX_RESEARCH_CHARS = 6000

_THEMES_INPUTS = """# 読者プロファイル(3層＋週次インサイト)
{{readerProfile}}
# themeKind
{{themeKind}}
ThemeAssignmentSet（editorialIntent / assignments[4]）のJSONのみを出力せよ。"""

# 調査トリオ（今/市場/普遍）の入力。assignedTheme は ThemeSpec、readerBase は業界・職種・役職。
_RESEARCH_INPUTS = """# テーマ
{{assignedTheme}}
# 読者の属性(業界・職種・役職)
{{readerBase}}
調査結果のJSONのみを出力せよ（実在URLを可能な限り付す）。"""

_GATE_INPUTS = """# 4企画書（チームA/B/C/D）
{{planSet}}
# 読者プロファイル(3層＋週次インサイト・relevance採点の照合元)
{{readerProfile}}
# 編集意図（棚コンセプト＋制約）
{{editorialIntent}}
# 閾値 / ラウンド
threshold={{threshold}} / round={{round}}
PlanSetVerdict（per_plan[4] / portfolio / score / decision / rejectionFeedback / approvedPlans）のJSONのみを出力せよ。"""


# ── エージェント定義 ─────────────────────────────────────────
def _themes_agent() -> LlmAgent:
    def instruction(ctx: Any) -> str:
        base = render.build_system_text("editor_chief_themes", ctx.state)
        return base + "\n\n# 入力\n" + render.render_template(_THEMES_INPUTS, ctx.state)

    return LlmAgent(
        name="editor_chief_themes",
        model=model_for("editor_chief_themes"),
        instruction=instruction,
        output_schema=ThemeAssignmentSet,
        output_key=K.THEME_ASSIGNMENT_SET,
    )


def _research_agent(role: str, name: str, output_key: str) -> LlmAgent:
    # grounding（google_search）＋output_schema は併用しない＝text出力（miniloop で実証済の安定構成）。
    def instruction(ctx: Any) -> str:
        base = render.build_system_text(role, ctx.state)
        return base + "\n\n# 入力\n" + render.render_template(_RESEARCH_INPUTS, ctx.state)

    return LlmAgent(
        name=name,
        model=model_for(role),
        instruction=instruction,
        tools=[google_search],
        output_key=output_key,
    )


def _set_gate_agent() -> LlmAgent:
    def instruction(ctx: Any) -> str:
        base = render.build_system_text("editor_chief_gate", ctx.state)
        return base + "\n\n# 入力\n" + render.render_template(_GATE_INPUTS, ctx.state)

    return LlmAgent(
        name="editor_chief_gate",
        model=model_for("editor_chief_gate"),
        instruction=instruction,
        output_schema=PlanSetVerdict,
        output_key=K.PLAN_SET_VERDICT,
    )


# ── トポロジ（creds 不要で組める＝オフライン構造テスト対象）──────────
def build_research_trio() -> ParallelAgent:
    """調査トリオ（今=sub_trend / 市場=sub_competitors / 普遍=sub_classics）。"""
    return ParallelAgent(
        name="research_trio",
        sub_agents=[
            _research_agent("sub_trend", "sub_trend", K.SUB_TREND),
            _research_agent("sub_competitors", "sub_competitors", K.SUB_MARKET),
            _research_agent("sub_classics", "sub_classics", K.SUB_THEME_INSIGHT),
        ],
    )


def build_team_pipeline() -> SequentialAgent:
    """1チーム＝[調査トリオ → plan_owner(PlanProposal)]。テーマは init_state の assignedTheme。"""
    return SequentialAgent(
        name="team_pipeline",
        sub_agents=[build_research_trio(), _plan_owner()],
    )


def build_planning_set() -> dict[str, Any]:
    """セット企画の3フェーズ構成（テーマ設定 / チーム縦串 / セットゲート）を返す（構造検証用）。"""
    return {
        "themes": _themes_agent(),
        "team_pipeline": build_team_pipeline(),
        "set_gate": _set_gate_agent(),
    }


# ── ランタイム（実LLM・課金あり）─────────────────────────────
async def _run(root: Any, app: str, init_state: dict[str, Any]) -> dict[str, Any]:
    runner = InMemoryRunner(agent=root, app_name=app)
    session = await runner.session_service.create_session(
        app_name=app, user_id="planning_set", state=init_state
    )
    message = types.Content(role="user", parts=[types.Part(text="セット企画を進めてください")])
    async for _event in runner.run_async(
        user_id="planning_set", session_id=session.id, new_message=message
    ):
        pass
    final = await runner.session_service.get_session(
        app_name=app, user_id="planning_set", session_id=session.id
    )
    return final.state if final else {}


def _to_dict(value: Any) -> Any:
    if value is None:
        return None
    if hasattr(value, "model_dump"):
        try:
            return value.model_dump(by_alias=True)
        except Exception:
            return value
    return value


def _norm_plan(raw: Any) -> Optional[dict]:
    if raw is None:
        return None
    try:
        data = raw.model_dump(by_alias=True) if hasattr(raw, "model_dump") else dict(raw)
        return PlanProposal.model_validate(data).model_dump(by_alias=True)
    except Exception:
        return _to_dict(raw)


def _truncate_research(value: Any) -> Any:
    """grounding の生テキストを上限文字数で切る（トークン爆発防止）。dict/None はそのまま。"""
    if isinstance(value, str) and len(value) > _MAX_RESEARCH_CHARS:
        return value[:_MAX_RESEARCH_CHARS] + "\n…（調査本文は長文のため要約・以下省略）"
    return value


async def _run_team(
    profile: ReaderProfile3Layer, assignment: dict[str, Any], theme_kind: str, rejection_feedback: Optional[str]
) -> Optional[dict]:
    """1チームの縦串を実行し PlanProposal を返す。

    調査トリオと plan_owner を**別ランに分割**し、間で grounding 生テキストを上限で切ってから
    owner に渡す（同一ランだと巨大 grounding がそのまま owner プロンプトに入り 65k 超過で 400）。
    """
    base_state: dict[str, Any] = {
        "readerProfile": profile.model_dump(by_alias=True),
        "readerBase": profile.base.model_dump(by_alias=True) if profile.base else {},
        "assignedTheme": assignment.get("theme", {}),
        "themeKind": theme_kind,
    }
    # 1) 調査トリオ（grounding）
    research_state = await _run(build_research_trio(), _APP_RESEARCH, dict(base_state))
    subs = {
        K.SUB_TREND: _truncate_research(research_state.get(K.SUB_TREND)),
        K.SUB_MARKET: _truncate_research(research_state.get(K.SUB_MARKET)),
        K.SUB_THEME_INSIGHT: _truncate_research(research_state.get(K.SUB_THEME_INSIGHT)),
    }
    # 2) plan_owner（切り詰めた調査＋テーマ＋差し戻しを注入）
    owner_state = await _run(
        _plan_owner(),
        _APP_OWNER,
        {**base_state, **subs, K.REJECTION_FEEDBACK: rejection_feedback},
    )
    plan = _norm_plan(owner_state.get(K.PLAN_DRAFT))
    # I-39: LLM が proposalId を返さない場合があり、None のまま下流へ流れると
    # PipelineResult(approved_plan_ids) が pydantic で落ち、persona_id も "cast_None" になる。
    # 決定的経路（deterministic.py: plan_det_{team_id}）に倣い team_id で必ず採番する。
    if plan is not None and not plan.get("proposalId"):
        team_id = assignment.get("team_id") or assignment.get("theme", {}).get("theme_id") or "x"
        plan["proposalId"] = f"plan_vertex_{team_id}"
    return plan


async def _run_set_gate(
    profile: ReaderProfile3Layer, plans: list[dict], editorial_intent: Any, threshold: int, rnd: int
) -> Optional[dict]:
    init_state: dict[str, Any] = {
        K.PLAN_SET: plans,
        "planSet": plans,
        "readerProfile": profile.model_dump(by_alias=True),
        "editorialIntent": _to_dict(editorial_intent),
        "threshold": threshold,
        K.ROUND: rnd,
    }
    st = await _run(_set_gate_agent(), _APP_GATE, init_state)
    raw = st.get(K.PLAN_SET_VERDICT)
    try:
        return PlanSetVerdict.model_validate(_to_dict(raw)).model_dump(by_alias=True)
    except Exception:
        return _to_dict(raw)


async def run_planning_set_vertex_async(
    profile: ReaderProfile3Layer,
    *,
    theme_kind: str = "honmei",
    threshold: int = _DEFAULT_THRESHOLD,
) -> dict[str, Any]:
    """4テーマ・セット企画を実Vertexで回す。返り値は deterministic 版と同形。

    1) editor_chief_themes → 4テーマ
    2) 各チーム[調査トリオ→plan_owner] → 4 PlanProposal
    3) editor_chief_gate → PlanSetVerdict。revise なら弱い冊のみ再立案（最高3R）。
    """
    # 1) テーマ設定
    st = await _run(
        _themes_agent(),
        _APP_THEMES,
        {"readerProfile": profile.model_dump(by_alias=True), "themeKind": theme_kind},
    )
    tas_raw = _to_dict(st.get(K.THEME_ASSIGNMENT_SET)) or {}
    tas = ThemeAssignmentSet.model_validate(tas_raw)
    assignments = [a.model_dump(by_alias=True) for a in tas.assignments][:4]
    editorial_intent = tas.editorial_intent

    # 2) 初回：全チームを並行立案
    plans: list[Optional[dict]] = await asyncio.gather(
        *[_run_team(profile, a, theme_kind, None) for a in assignments]
    )

    verdict_history: list[dict] = []
    reject_log: list[dict] = []
    final_verdict: Optional[dict] = None
    rounds = 0

    # 3) セットゲート＋弱い冊のみ再立案（最高3R）
    for rnd in range(1, _MAX_ROUNDS + 1):
        rounds = rnd
        verdict = await _run_set_gate(profile, [p for p in plans if p], editorial_intent, threshold, rnd) or {}
        final_verdict = verdict
        verdict_history.append(
            {"round": rnd, "score": verdict.get("score"), "decision": verdict.get("decision")}
        )
        if verdict.get("decision") == "approve" or rnd >= _MAX_ROUNDS:
            break
        # 弱い冊（belowFloor または decision=revise）の index を集め、その冊だけ rejectionFeedback で再立案。
        feedback = verdict.get("rejectionFeedback") or ""
        weak_ids = {
            pp.get("planId")
            for pp in verdict.get("perPlan", [])
            if pp.get("belowFloor") or pp.get("decision") == "revise"
        }
        reject_log.append({"round": rnd, "rejectionFeedback": feedback, "belowFloor": list(weak_ids)})
        retries = [
            _run_team(profile, assignments[i], theme_kind, feedback)
            for i, p in enumerate(plans)
            if p and p.get("proposalId") in weak_ids
        ]
        retry_idx = [i for i, p in enumerate(plans) if p and p.get("proposalId") in weak_ids]
        if not retries:
            break
        redone = await asyncio.gather(*retries)
        for i, plan in zip(retry_idx, redone):
            if plan:
                plans[i] = plan

    approved = [p for p in plans if p] if (final_verdict or {}).get("decision") == "approve" else []
    plan_set = PlanSet(
        theme_kind=theme_kind,  # type: ignore[arg-type]
        editorial_intent=editorial_intent,
        themes=[a["theme"] for a in assignments],
        plans=[PlanProposal.model_validate(p) for p in approved],
        allocation="1-1-1-1",
    ).model_dump(by_alias=True)

    return {
        "themeKind": theme_kind,
        "rounds": rounds,
        "verdictHistory": verdict_history,
        "rejectLog": reject_log,
        "themeAssignmentSet": tas.model_dump(by_alias=True),
        "planSet": plan_set,
        "planSetVerdict": final_verdict,
    }


def run_planning_set_vertex(
    profile: ReaderProfile3Layer,
    *,
    theme_kind: str = "honmei",
    threshold: int = _DEFAULT_THRESHOLD,
) -> dict[str, Any]:
    """同期ラッパー（CLI/テストから）。**実Vertex・課金あり**。"""
    return asyncio.run(
        run_planning_set_vertex_async(profile, theme_kind=theme_kind, threshold=threshold)
    )
