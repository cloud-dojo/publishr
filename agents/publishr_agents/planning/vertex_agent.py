"""STEP2 企画3階層の実Vertex実装（PUBLISHR_LLM=vertex・隔離）。

miniloop（C1.0.1）を本STEP2へ一般化:
  Sequential[ Parallel[sub_reader_context / sub_market(grounding) / sub_theme_insight(grounding)] →
              Loop(max3)[ plan_owner(Pro→PlanProposal) → plan_leader(Pro→LeaderVerdict) → LoopBreakAgent ] ]

- 調査3サブは初回のみ（owner/leader ループの外側）。B/C は google_search で grounding（text出力）。
- escalate ループ（差し戻し→再提出→承認/3R強制）は miniloop の LoopBreakAgent を再利用。
- 入力は C1.2 の実 ReaderProfile。miniloop.py（C1.0.1成果物）は不変。**実LLM・課金あり**。
- 【トークン爆発対策】research（grounding）と loop を別ランに分割し、間で grounding 生テキストを
  上限文字数で切り詰めてから owner/leader に渡す（生注入だと 65k 超過で 400＝memory
  publishr-vertex-grounding-token-cap）。build_planning() のトポロジ自体は不変。
"""

from __future__ import annotations

import asyncio
import warnings
from typing import Any, Optional

warnings.filterwarnings("ignore", category=DeprecationWarning, module="google.adk")

from google.adk.agents import LlmAgent, LoopAgent, ParallelAgent, SequentialAgent  # noqa: E402
from google.adk.runners import InMemoryRunner  # noqa: E402
from google.adk.tools import google_search  # noqa: E402
from google.genai import types  # noqa: E402
from publishr_schema import LeaderVerdict, PlanProposal, ReaderProfile3Layer, SubReaderContext  # noqa: E402

from .. import state_keys as K  # noqa: E402
from ..llm.provider import model_for  # noqa: E402
from ..prompts import loader, render  # noqa: E402
from ..vertex.miniloop import LoopBreakAgent  # noqa: E402 — escalate ループは再利用
from .deterministic import derive_theme  # noqa: E402

_APP = "publishr_planning"
# grounding（google_search）生テキストを owner/leader へ渡す前に切り詰める上限（vertex_set と同方針）。
_MAX_RESEARCH_CHARS = 6000

_SUB_READER_INPUTS = """# 読者プロファイル(3層・特に currentWork)
{{readerProfile}}
# themeKind
{{themeKind}}
# 仮テーマ
{{tentativeTheme}}
subReaderContext のJSONのみを出力せよ。"""

_SUB_MARKET_INPUTS = """# 仮テーマ
{{tentativeTheme}}
# 読者(base)
{{readerBase}}
出力: 売れ筋・既製本・marketGap を含む調査結果（実在書名・出典URLを可能な限り付す）。"""

_SUB_THEME_INPUTS = """# 仮テーマ
{{tentativeTheme}}
# 読者(base・ドメイン文脈＝業界/職種。テーマ語が曖昧なとき検索をこの圏に錨で留める)
{{readerBase}}
出力: 章立ての根拠になる keyPoints（出典URLを可能な限り付す）。"""

_LEADER_INPUTS = """# 企画書(PlanProposal)
{{planDraft}}
# 読者プロファイル(3層)
{{readerProfile}}
# 市場調査(subMarket・差別化と③調査反映の判定材料)
{{subMarket}}
# テーマ知見調査(subThemeInsight・③調査反映の論点反映の判定材料。空/拒否/一般論なら③を足切り)
{{subThemeInsight}}
# themeKind
{{themeKind}}
# threshold
{{threshold}}
# round（このラウンド番号）
{{round}}
注: round が 3 のときは、たとえ弱くても最良案を必ず decision="approve" とせよ（revise 禁止＝棚を空にしない）。
LeaderVerdict のJSONのみを出力せよ。"""


def _sub_reader_context() -> LlmAgent:
    system = loader.load_section_system("step2_research_subs", "読者局面")

    def instruction(ctx: Any) -> str:
        return render.render_template(system + "\n\n# 入力\n" + _SUB_READER_INPUTS, ctx.state)

    return LlmAgent(
        name="sub_reader_context",
        model=model_for("sub_reader_context"),
        instruction=instruction,
        output_schema=SubReaderContext,
        output_key=K.SUB_READER_CONTEXT,
    )


def _sub_market() -> LlmAgent:
    system = loader.load_section_system("step2_research_subs", "市場・競合")

    def instruction(ctx: Any) -> str:
        return render.render_template(system + "\n\n# 入力\n" + _SUB_MARKET_INPUTS, ctx.state)

    # grounding（google_search）＋output_schema は併用しない＝text出力（miniloop で実証済の安定構成）。
    return LlmAgent(
        name="sub_market",
        model=model_for("sub_market"),
        instruction=instruction,
        tools=[google_search],
        output_key=K.SUB_MARKET,
    )


def _sub_theme_insight() -> LlmAgent:
    system = loader.load_section_system("step2_research_subs", "テーマ知見")

    def instruction(ctx: Any) -> str:
        return render.render_template(system + "\n\n# 入力\n" + _SUB_THEME_INPUTS, ctx.state)

    return LlmAgent(
        name="sub_theme_insight",
        model=model_for("sub_theme_insight"),
        instruction=instruction,
        tools=[google_search],
        output_key=K.SUB_THEME_INSIGHT,
    )


def _plan_owner() -> LlmAgent:
    user_template = loader.load_prompt("step2_plan_owner").user_template or ""

    def instruction(ctx: Any) -> str:
        base = render.build_system_text("plan_owner", ctx.state)
        return base + "\n\n# 入力\n" + render.render_template(user_template, ctx.state)

    return LlmAgent(
        name="plan_owner",
        model=model_for("plan_owner"),
        instruction=instruction,
        output_schema=PlanProposal,
        output_key=K.PLAN_DRAFT,
    )


def _plan_leader() -> LlmAgent:
    def instruction(ctx: Any) -> str:
        base = render.build_system_text("plan_leader", ctx.state)
        return base + "\n\n# 入力\n" + render.render_template(_LEADER_INPUTS, ctx.state)

    return LlmAgent(
        name="plan_leader",
        model=model_for("plan_leader"),
        instruction=instruction,
        output_schema=LeaderVerdict,
        output_key=K.LEADER_VERDICT,
    )


def _research_subs() -> ParallelAgent:
    return ParallelAgent(
        name="research_subs",
        sub_agents=[_sub_reader_context(), _sub_market(), _sub_theme_insight()],
    )


def _planning_loop(threshold: int) -> LoopAgent:
    return LoopAgent(
        name="planning_loop",
        max_iterations=3,
        sub_agents=[_plan_owner(), _plan_leader(), LoopBreakAgent(name="loop_break", threshold=threshold)],
    )


def build_planning(threshold: int = 70) -> SequentialAgent:
    """論理トポロジ（research_subs → planning_loop）。構造テスト用。

    ランタイムは run_planning_vertex_async が research と loop を別ランに分け、間で grounding を
    切り詰める（トークン爆発対策）。トポロジ自体はこの合成と一致。
    """
    return SequentialAgent(name="planning_root", sub_agents=[_research_subs(), _planning_loop(threshold)])


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
    """grounding 生テキストを上限文字数で切る（トークン爆発防止）。dict/None はそのまま。"""
    if isinstance(value, str) and len(value) > _MAX_RESEARCH_CHARS:
        return value[:_MAX_RESEARCH_CHARS] + "\n…（調査本文は長文のため要約・以下省略）"
    return value


async def _run(root: Any, init_state: dict[str, Any]) -> dict[str, Any]:
    runner = InMemoryRunner(agent=root, app_name=_APP)
    session = await runner.session_service.create_session(
        app_name=_APP, user_id="planning", state=init_state
    )
    message = types.Content(role="user", parts=[types.Part(text="今朝の企画会議を始めてください")])
    async for _event in runner.run_async(
        user_id="planning", session_id=session.id, new_message=message
    ):
        pass
    final = await runner.session_service.get_session(
        app_name=_APP, user_id="planning", session_id=session.id
    )
    return final.state if final else {}


async def run_planning_vertex_async(
    profile: ReaderProfile3Layer,
    *,
    theme: Optional[str] = None,
    theme_kind: str = "honmei",
    threshold: int = 70,
) -> dict[str, Any]:
    """research（grounding）と owner/leader ループを別ランに分け、間で grounding を切り詰める。

    同一ランだと巨大 grounding がそのまま owner/leader プロンプトに入り 65k 超過で 400 になるため。
    """
    theme = theme or derive_theme(profile, theme_kind)
    base_state: dict[str, Any] = {
        "readerProfile": profile.model_dump(by_alias=True),
        "readerBase": profile.base.model_dump(by_alias=True) if profile.base else {},
        "themeKind": theme_kind,
        "tentativeTheme": theme,
        "threshold": threshold,
    }
    # 1) 調査3サブ（B/C は grounding）
    research_state = await _run(_research_subs(), dict(base_state))
    sub_reader = _to_dict(research_state.get(K.SUB_READER_CONTEXT))
    sub_market = _truncate_research(research_state.get(K.SUB_MARKET))
    sub_theme = _truncate_research(research_state.get(K.SUB_THEME_INSIGHT))
    # 2) owner/leader ループ（切り詰めた調査を注入。escalate は LoopBreakAgent が担う）
    loop_state = await _run(
        _planning_loop(threshold),
        {
            **base_state,
            K.SUB_READER_CONTEXT: sub_reader,
            K.SUB_MARKET: sub_market,
            K.SUB_THEME_INSIGHT: sub_theme,
            K.ROUND: 1,
            K.REJECTION_FEEDBACK: None,
            "verdict_history": [],
        },
    )
    return {
        "theme": theme,
        "themeKind": theme_kind,
        "rounds": int(loop_state.get(K.ROUND, 1)),
        "verdictHistory": loop_state.get("verdict_history", []),
        "approvedPlan": _norm_plan(loop_state.get(K.APPROVED_PLAN)),
        "rejectionFeedback": loop_state.get(K.REJECTION_FEEDBACK),
        "forced_approve": bool(loop_state.get("forced_approve", False)),
        "subReaderContext": sub_reader,
        "subMarket": sub_market,
        "subThemeInsight": sub_theme,
    }


def run_planning_vertex(
    profile: ReaderProfile3Layer,
    *,
    theme: Optional[str] = None,
    theme_kind: str = "honmei",
    threshold: int = 70,
) -> dict[str, Any]:
    """同期ラッパー（CLI/テストから）。**実Vertex・課金あり**。"""
    return asyncio.run(
        run_planning_vertex_async(profile, theme=theme, theme_kind=theme_kind, threshold=threshold)
    )
