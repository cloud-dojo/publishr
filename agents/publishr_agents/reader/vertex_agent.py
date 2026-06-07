"""STEP1 読者分析の実Vertex実装（PUBLISHR_LLM=vertex・Gemini Pro・隔離）。

miniloop と同じ ADK LlmAgent + InMemoryRunner パターン。step1_reader_analyst プロンプトを
結線し、ObservationBundle/prevProfile/initialProfile を state に入れて Pro に渡す。
出力は output_schema=ReaderProfile3Layer で構造化。**実LLM・課金あり**。
"""

from __future__ import annotations

import asyncio
import logging
import warnings
from typing import Any, Optional

# ADK 2.1 の一部 Agent は DeprecationWarning を出すが機能する。
warnings.filterwarnings("ignore", category=DeprecationWarning, module="google.adk")

from google.adk.agents import LlmAgent  # noqa: E402
from google.adk.runners import InMemoryRunner  # noqa: E402
from google.genai import types  # noqa: E402
from publishr_schema import ObservationBundle, ReaderProfile3Layer, User  # noqa: E402

from .. import state_keys as K  # noqa: E402
from ..llm.provider import model_for  # noqa: E402
from ..prompts import loader, render  # noqa: E402

_APP = "publishr_reader"

logger = logging.getLogger(__name__)


def build_reader_agent() -> LlmAgent:
    """STEP1 読者分析 LlmAgent（Pro・ReaderProfile3Layer 構造化出力）を組む。"""
    user_template = loader.load_prompt("step1_reader_analyst").user_template or ""

    def instruction(ctx: Any) -> str:
        base = render.build_system_text("reader_analyst", ctx.state)
        return base + "\n\n# 入力\n" + render.render_template(user_template, ctx.state)

    return LlmAgent(
        name="reader_analyst",
        model=model_for("reader_analyst"),
        instruction=instruction,
        output_schema=ReaderProfile3Layer,
        output_key=K.READER_PROFILE,
    )


def _norm(raw: Any) -> Optional[ReaderProfile3Layer]:
    """ADK が state に入れた出力（pydantic / dict・snake|camel）を ReaderProfile3Layer に正規化。"""
    if raw is None:
        return None
    try:
        data = raw.model_dump(by_alias=True) if hasattr(raw, "model_dump") else dict(raw)
        return ReaderProfile3Layer.model_validate(data)
    except Exception as exc:  # noqa: BLE001 — live 検証の歩留まり用に真因を残す
        logger.warning("reader output normalize failed: %s / raw=%.300s", exc, repr(raw))
        return None


def _init_state(
    observation: ObservationBundle,
    user: Optional[User],
    prev_profile: Optional[ReaderProfile3Layer],
) -> dict[str, Any]:
    initial = user.initial_profile if user else None
    return {
        "observationBundle": observation.model_dump(by_alias=True),
        "prevProfile": prev_profile.model_dump(by_alias=True) if prev_profile else None,
        "initialProfile": initial.model_dump(by_alias=True) if initial else None,
    }


async def analyze_reader_vertex_async(
    observation: ObservationBundle,
    *,
    user: Optional[User] = None,
    prev_profile: Optional[ReaderProfile3Layer] = None,
) -> ReaderProfile3Layer:
    root = build_reader_agent()
    runner = InMemoryRunner(agent=root, app_name=_APP)
    uid = user.id if user else "reader"
    session = await runner.session_service.create_session(
        app_name=_APP, user_id=uid, state=_init_state(observation, user, prev_profile)
    )
    message = types.Content(
        role="user", parts=[types.Part(text="観測データから読者プロファイル(3層)を作成してください")]
    )
    async for _event in runner.run_async(user_id=uid, session_id=session.id, new_message=message):
        pass
    final = await runner.session_service.get_session(
        app_name=_APP, user_id=uid, session_id=session.id
    )
    profile = _norm(final.state.get(K.READER_PROFILE)) if final else None
    if profile is None:
        raise RuntimeError("reader_analyst が ReaderProfile を返しませんでした")
    return profile


def analyze_reader_vertex(
    observation: ObservationBundle,
    *,
    user: Optional[User] = None,
    prev_profile: Optional[ReaderProfile3Layer] = None,
) -> ReaderProfile3Layer:
    """同期ラッパー（CLI/テストから）。**実Vertex・課金あり**。"""
    return asyncio.run(
        analyze_reader_vertex_async(observation, user=user, prev_profile=prev_profile)
    )
