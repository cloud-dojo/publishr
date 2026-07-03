"""企画会議パイプラインの組み立てと実行。

SequentialAgent: observe → reader → ParallelAgent(企画3体) → 選抜ゲート
                 → 著者アジェンダ（表紙 CSS variant 付与）
実行後、セッション状態から PipelineResult を組み立てて返す。
表紙の画像生成（Imagen）は今回スコープ外で park（将来実装）。"""

from __future__ import annotations

import asyncio
import os
import warnings

# ADK 2.1 では Sequential/Parallel が deprecated 警告を出すが機能する。MVPでは抑制。
warnings.filterwarnings("ignore", category=DeprecationWarning, module="google.adk")

from google.adk.agents import ParallelAgent, SequentialAgent  # noqa: E402
from google.adk.runners import InMemoryRunner  # noqa: E402
from google.genai import types  # noqa: E402
from publishr_schema import Book, Observation, PlanningCandidate, ReaderProfile  # noqa: E402

from . import canned  # noqa: E402
from . import state_keys as K  # noqa: E402
from .agents import (  # noqa: E402
    AuthorAgendaAgent,
    ObserveAgent,
    PlanningAgent,
    ReaderAgent,
    SelectionGateAgent,
)
from .prompts import planning_prompts  # noqa: E402
from .result import PipelineResult, RejectLogEntry  # noqa: E402

_APP = "publishr"


def build_pipeline(user_id: str) -> SequentialAgent:
    """PUBLISHR_LLM で topology を分岐する dispatcher（P0bシーム）。

    mock=決定的canned（現行と同一木）／ vertex=実LLM topology（P2 ADK MiniLoop 以降）。
    """
    mode = os.environ.get("PUBLISHR_LLM", "mock").lower()
    if mode == "mock":
        return _build_mock_pipeline(user_id)
    if mode == "vertex":
        raise NotImplementedError(
            "PUBLISHR_LLM=vertex の実LLM topology は P2（ADK MiniLoop）以降で実装"
        )
    raise ValueError(f"unknown PUBLISHR_LLM={mode!r}")


def _build_mock_pipeline(user_id: str) -> SequentialAgent:
    pp = planning_prompts()
    names = {p["key"]: p["name"] for p in pp["planners"]}
    planners = [
        PlanningAgent(
            name=names.get(c["key"], f"planner_{c['key']}"),
            persona_key=c["key"],
            persona_label=c["persona"],
            candidate=c["candidate"],
            plan_id=c["planId"],
        )
        for c in canned.planning_candidates()
    ]
    planning_team = ParallelAgent(name="planning_team", sub_agents=planners)
    return SequentialAgent(
        name="editorial_pipeline",
        sub_agents=[
            ObserveAgent(name="observe", user_id=user_id),
            ReaderAgent(name="reader_analyst"),
            planning_team,
            SelectionGateAgent(name="selection_leader"),
            AuthorAgendaAgent(name="author_engine"),
        ],
    )


async def run_pipeline_async(user_id: str) -> PipelineResult:
    root = build_pipeline(user_id)
    runner = InMemoryRunner(agent=root, app_name=_APP)
    session = await runner.session_service.create_session(app_name=_APP, user_id=user_id)
    message = types.Content(role="user", parts=[types.Part(text="今朝の企画会議を始めてください")])
    async for _event in runner.run_async(
        user_id=user_id, session_id=session.id, new_message=message
    ):
        pass
    final = await runner.session_service.get_session(
        app_name=_APP, user_id=user_id, session_id=session.id
    )
    state = final.state if final else {}

    books = [Book.model_validate(b) for b in state.get(K.BOOKS, [])]
    candidates = [PlanningCandidate.model_validate(c) for c in state.get(K.CANDIDATES, [])]
    approved_plan_ids = list(state.get(K.APPROVED_PLAN_IDS, []))
    reject_log = [RejectLogEntry.model_validate(e) for e in state.get(K.REJECT_LOG, [])]
    observation = Observation.model_validate(state.get(K.OBSERVATION, {}))
    reader_profile = ReaderProfile.model_validate(state.get(K.READER_PROFILE, {}))
    plans = canned.arrival_plans(approved_plan_ids)
    return PipelineResult(
        plans=plans,
        books=books,
        observation=observation,
        reader_profile=reader_profile,
        candidates=candidates,
        approved_plan_ids=approved_plan_ids,
        reject_log=reject_log,
    )


def run_pipeline(user_id: str) -> PipelineResult:
    """同期ラッパー（BFF/CLIから呼ぶ）。"""
    return asyncio.run(run_pipeline_async(user_id))
