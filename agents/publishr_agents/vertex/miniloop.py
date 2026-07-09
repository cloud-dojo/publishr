"""P2/H2: ADK MiniLoop（実Vertex Gemini）— escalate ループの実証。

トポロジ:
  Sequential[ market_sub(Flash+google_search) →
              Loop(max_iterations=3)[ plan_owner(Flash→PlanProposal) →
                                      plan_leader(Pro→LeaderVerdict) →
                                      LoopBreakAgent(escalate) ] ]

- score < 閾値 → rejectionFeedback を書いて次ラウンド（owner が練り直す）
- score >= 閾値 → escalate でループ脱出
- round 3 で未承認なら強制承認（プロンプト帯＋コード帯＝棚を空にしない）

mock経路（build_pipeline）とは独立。**実LLM・課金あり**。STEP2フル化は P3。
"""

from __future__ import annotations

import asyncio
import warnings
from typing import Any, AsyncGenerator

# ADK 2.1 の Sequential/Loop は DeprecationWarning を出すが機能する。
warnings.filterwarnings("ignore", category=DeprecationWarning, module="google.adk")

from google.adk.agents import BaseAgent, LlmAgent, LoopAgent, SequentialAgent  # noqa: E402
from google.adk.agents.invocation_context import InvocationContext  # noqa: E402
from google.adk.events import Event, EventActions  # noqa: E402
from google.adk.tools import google_search  # noqa: E402
from google.adk.runners import InMemoryRunner  # noqa: E402
from google.genai import types  # noqa: E402
from publishr_schema import LeaderVerdict, PlanProposal  # noqa: E402

from ..llm.provider import model_for  # noqa: E402
from ..prompts import loader, render  # noqa: E402
from .. import state_keys as K  # noqa: E402

_APP = "publishr_miniloop"

# デモ読者（佐倉美咲・eval_set.yaml と整合の3層プロファイル要約）。
_READER_PROFILE: dict[str, Any] = {
    "base": {
        "industry": "食品・飲料メーカー",
        "jobType": "マーケティング・ブランド",
        "position": "課長・マネージャー（2026/04新任）",
        "orgScale": "部下7名（年上ベテランの佐藤健一42歳・経験19年を含む）",
        "readingGenres": ["すぐ使える実践書・ハウツー", "事例・ストーリーで学ぶ"],
    },
    "currentWork": {
        "currentSituation": (
            "新任2ヶ月。しずく天然水の春リニューアル判断と6/5役員中間報告を控え方針に自信が持てない／"
            "初の上期評価面談準備／年上部下マネジメントに戸惑い／会議過多で読書時間ゼロ"
        ),
        "activeWorkThemes": ["新任マネジメント", "任せ方・権限委譲", "上期評価面談", "会議ファシリテーション"],
        "challenges": [
            "年上で実力者の佐藤さんにどこまで・どう任せるかの距離感",
            "リニューアル方針に確信が持てず役員報告の根拠を固めきれない",
            "測りにくい仕事をどう評価するか",
        ],
    },
    "readingBehavior": {"serendipityTolerance": "mid", "stylePreference": "実務的・対話的"},
}

_THEME = "新任マネージャーの任せ方・権限委譲（年上の実力者部下を含む）"
_THEME_KIND = "honmei"
_THRESHOLD = 70

# leader には user template が無いので、入力ブロックを明示する。
_LEADER_INPUTS = """# 企画書(PlanProposal)
{{planDraft}}
# 読者プロファイル(3層)
{{readerProfile}}
# themeKind
{{themeKind}}
# threshold
{{threshold}}
# round（このラウンド番号）
{{round}}
注: round が 3 のときは、たとえ弱くても最良案を必ず decision="approve" とせよ（revise 禁止＝棚を空にしない）。
LeaderVerdict のJSONのみを出力せよ。"""

_SUB_INPUTS = """# テーマ
{{tentativeTheme}}
# 読者(base)
{{readerBase}}
出力: 売れ筋・既製本・marketGap を含む調査結果テキスト（可能な限り実在書名・出典URLを付す）。"""


def _market_sub() -> LlmAgent:
    system = loader.load_section_system("step2_research_subs", "市場・競合")

    def instruction(ctx) -> str:
        return render.render_template(system + "\n\n# 入力\n" + _SUB_INPUTS, ctx.state)

    return LlmAgent(
        name="market_sub",
        model=model_for("sub_market"),
        instruction=instruction,
        tools=[google_search],
        output_key=K.SUB_MARKET,
    )


def _plan_owner() -> LlmAgent:
    user_template = loader.load_prompt("step2_plan_owner").user_template or ""

    def instruction(ctx) -> str:
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
    def instruction(ctx) -> str:
        base = render.build_system_text("plan_leader", ctx.state)
        return base + "\n\n# 入力\n" + render.render_template(_LEADER_INPUTS, ctx.state)

    return LlmAgent(
        name="plan_leader",
        model=model_for("plan_leader"),
        instruction=instruction,
        output_schema=LeaderVerdict,
        output_key=K.LEADER_VERDICT,
    )


def _as_dict(value: Any) -> dict:
    if value is None:
        return {}
    if hasattr(value, "model_dump"):
        return value.model_dump(by_alias=True)
    return dict(value)


def _norm(raw: Any, model) -> dict:
    """ADKがstateに入れた出力（pydantic / dict・snake|camel）を camelCase dict に正規化。"""
    if raw is None:
        return {}
    try:
        data = raw.model_dump(by_alias=True) if hasattr(raw, "model_dump") else dict(raw)
        return model.model_validate(data).model_dump(by_alias=True)
    except Exception:
        return _as_dict(raw)


class LoopBreakAgent(BaseAgent):
    """leaderVerdict を見て、承認なら escalate（脱出）、却下なら feedback を書いて次ラウンドへ。"""

    threshold: int = _THRESHOLD

    async def _run_async_impl(self, ctx: InvocationContext) -> AsyncGenerator[Event, None]:
        st = ctx.session.state
        verdict = _norm(st.get(K.LEADER_VERDICT), LeaderVerdict)
        rnd = int(st.get(K.ROUND, 1))
        score = int(verdict.get("score", 0) or 0)
        decision = verdict.get("decision", "revise")

        history = list(st.get("verdict_history", []))
        history.append({"round": rnd, "score": score, "decision": decision})
        st["verdict_history"] = history

        approve = decision == "approve" and score >= self.threshold
        if approve or rnd >= 3:
            plan = verdict.get("approvedPlan") or st.get(K.PLAN_DRAFT)
            st[K.APPROVED_PLAN] = plan
            forced = not approve
            if forced:
                st["forced_approve"] = True
            yield Event(
                author=self.name,
                actions=EventActions(
                    state_delta={
                        "verdict_history": history,
                        K.APPROVED_PLAN: plan,
                        "forced_approve": forced,
                    },
                    escalate=True,
                ),
            )
            return

        feedback = verdict.get("rejectionFeedback") or "弱い観点（的中度・差別化・調査反映・タイトル）を具体化して再提出。"
        st[K.REJECTION_FEEDBACK] = feedback
        st[K.ROUND] = rnd + 1
        yield Event(
            author=self.name,
            actions=EventActions(
                state_delta={"verdict_history": history, K.REJECTION_FEEDBACK: feedback, K.ROUND: rnd + 1},
                escalate=False,
            ),
        )


def build_miniloop(threshold: int = _THRESHOLD) -> SequentialAgent:
    planning_loop = LoopAgent(
        name="planning_loop",
        max_iterations=3,
        sub_agents=[_plan_owner(), _plan_leader(), LoopBreakAgent(name="loop_break", threshold=threshold)],
    )
    return SequentialAgent(name="miniloop_root", sub_agents=[_market_sub(), planning_loop])


async def run_miniloop_async(theme: str = _THEME, threshold: int = _THRESHOLD) -> dict[str, Any]:
    root = build_miniloop(threshold)
    runner = InMemoryRunner(agent=root, app_name=_APP)
    init_state: dict[str, Any] = {
        "readerProfile": _READER_PROFILE,
        "readerBase": _READER_PROFILE["base"],
        "themeKind": _THEME_KIND,
        "threshold": threshold,
        "tentativeTheme": theme,
        K.ROUND: 1,
        K.REJECTION_FEEDBACK: None,
        "verdict_history": [],
    }
    session = await runner.session_service.create_session(
        app_name=_APP, user_id="miniloop", state=init_state
    )
    message = types.Content(role="user", parts=[types.Part(text="今朝の企画会議を始めてください")])
    async for _event in runner.run_async(
        user_id="miniloop", session_id=session.id, new_message=message
    ):
        pass
    final = await runner.session_service.get_session(
        app_name=_APP, user_id="miniloop", session_id=session.id
    )
    st = final.state if final else {}
    return {
        "theme": theme,
        "rounds": int(st.get(K.ROUND, 1)),
        "verdict_history": st.get("verdict_history", []),
        "approvedPlan": _norm(st.get(K.APPROVED_PLAN), PlanProposal) or None,
        "planDraft": _norm(st.get(K.PLAN_DRAFT), PlanProposal) or None,
        "leaderVerdict": _norm(st.get(K.LEADER_VERDICT), LeaderVerdict) or None,
        "subMarket": st.get(K.SUB_MARKET),
        "forced_approve": bool(st.get("forced_approve", False)),
    }


def run_miniloop(theme: str = _THEME, threshold: int = _THRESHOLD) -> dict[str, Any]:
    """同期ラッパー（CLI/テストから）。"""
    return asyncio.run(run_miniloop_async(theme, threshold))
