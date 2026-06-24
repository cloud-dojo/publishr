"""STEP3 キャスティングの実Vertex実装（PUBLISHR_LLM=vertex・Gemini Pro・隔離）。

step3_casting_editor プロンプトを結線し、承認企画＋読者プロファイル＋お気に入り著者を
state に入れて Pro に 5著者を生成させる（output_schema=GeneratedPersonaSet）。reader と同型。
**実LLM・課金あり**。
"""

from __future__ import annotations

import asyncio
import logging
import warnings
from typing import Any, Optional

warnings.filterwarnings("ignore", category=DeprecationWarning, module="google.adk")

from google.adk.agents import LlmAgent  # noqa: E402
from google.adk.runners import InMemoryRunner  # noqa: E402
from google.genai import types  # noqa: E402
from publishr_schema import (  # noqa: E402
    AuthorCasting,
    GeneratedPersonaSet,
    PlanProposal,
    ReaderProfile3Layer,
)

from .. import state_keys as K  # noqa: E402
from ..llm.provider import model_for  # noqa: E402
from ..prompts import loader, render  # noqa: E402

_APP = "publishr_casting"
_APP_AUTHOR = "publishr_author_casting"

logger = logging.getLogger(__name__)

# step3 プロンプトに user template が無いので入力ブロックを明示（miniloop の leader と同方式）。
_INPUTS = """# 承認企画(PlanProposal・8項目)
{{approvedPlan}}
# 読者プロファイル(stylePreference 参照)
{{readerProfile}}
# お気に入り著者（任意・約15%で1枠採用・空なら採用なし）
{{favoriteAuthors}}
GeneratedPersonaSet（personas[5]＋reason）のJSONのみを出力せよ。"""


def build_casting_agent() -> LlmAgent:
    def instruction(ctx: Any) -> str:
        base = render.build_system_text("persona_generator", ctx.state)
        return base + "\n\n# 入力\n" + render.render_template(_INPUTS, ctx.state)

    return LlmAgent(
        name="persona_generator",
        model=model_for("persona_generator"),
        instruction=instruction,
        output_schema=GeneratedPersonaSet,
        output_key=K.GENERATED_PERSONA_SET,
    )


def _norm(raw: Any) -> Optional[GeneratedPersonaSet]:
    if raw is None:
        return None
    try:
        data = raw.model_dump(by_alias=True) if hasattr(raw, "model_dump") else dict(raw)
        return GeneratedPersonaSet.model_validate(data)
    except Exception as exc:  # noqa: BLE001 — live 検証の歩留まり用に真因を残す
        logger.warning("casting output normalize failed: %s / raw=%.300s", exc, repr(raw))
        return None


async def cast_personas_vertex_async(
    plan: PlanProposal,
    *,
    reader_profile: Optional[ReaderProfile3Layer] = None,
    favorite_authors: Optional[list[dict[str, Any]]] = None,
) -> GeneratedPersonaSet:
    root = build_casting_agent()
    runner = InMemoryRunner(agent=root, app_name=_APP)
    init_state: dict[str, Any] = {
        "approvedPlan": plan.model_dump(by_alias=True),
        "readerProfile": reader_profile.model_dump(by_alias=True) if reader_profile else None,
        "favoriteAuthors": favorite_authors or [],
    }
    session = await runner.session_service.create_session(
        app_name=_APP, user_id="casting", state=init_state
    )
    message = types.Content(role="user", parts=[types.Part(text="この企画に合う著者を5人キャスティングしてください")])
    async for _event in runner.run_async(user_id="casting", session_id=session.id, new_message=message):
        pass
    final = await runner.session_service.get_session(
        app_name=_APP, user_id="casting", session_id=session.id
    )
    result = _norm(final.state.get(K.GENERATED_PERSONA_SET)) if final else None
    if result is None:
        raise RuntimeError("persona_generator が GeneratedPersonaSet を返しませんでした")
    return result


def cast_personas_vertex(
    plan: PlanProposal,
    *,
    reader_profile: Optional[ReaderProfile3Layer] = None,
    favorite_authors: Optional[list[dict[str, Any]]] = None,
) -> GeneratedPersonaSet:
    """同期ラッパー（CLI/テストから）。**実Vertex・課金あり**。"""
    return asyncio.run(
        cast_personas_vertex_async(
            plan, reader_profile=reader_profile, favorite_authors=favorite_authors
        )
    )


# ── STEP3 author_casting（v3・4テーマ）: 3候補→1選抜（AuthorCasting）の実Vertex ──
def build_author_casting_agent() -> LlmAgent:
    """step3_author_casting プロンプトを結線。1企画＝3候補生成→最適1人を chosen に。"""
    user_template = loader.load_prompt("step3_author_casting").user_template or ""

    def instruction(ctx: Any) -> str:
        base = render.build_system_text("author_casting", ctx.state)
        return base + "\n\n# 入力\n" + render.render_template(user_template, ctx.state)

    return LlmAgent(
        name="author_casting",
        model=model_for("author_casting"),
        instruction=instruction,
        output_schema=AuthorCasting,
        output_key=K.AUTHOR_CASTING,
    )


def _norm_casting(raw: Any) -> Optional[AuthorCasting]:
    if raw is None:
        return None
    try:
        data = raw.model_dump(by_alias=True) if hasattr(raw, "model_dump") else dict(raw)
        return AuthorCasting.model_validate(data)
    except Exception as exc:  # noqa: BLE001 — live 検証の歩留まり用に真因を残す
        logger.warning("author_casting output normalize failed: %s / raw=%.300s", exc, repr(raw))
        return None


async def cast_author_vertex_async(
    plan: PlanProposal,
    *,
    reader_profile: Optional[ReaderProfile3Layer] = None,
    favorite_authors: Optional[list[dict[str, Any]]] = None,
    persona_inspiration: Optional[str] = None,
) -> AuthorCasting:
    root = build_author_casting_agent()
    runner = InMemoryRunner(agent=root, app_name=_APP_AUTHOR)
    init_state: dict[str, Any] = {
        "approvedPlan": plan.model_dump(by_alias=True),
        "readerProfile": reader_profile.model_dump(by_alias=True) if reader_profile else None,
        "favoriteAuthors": favorite_authors or [],
        "personaInspiration": persona_inspiration,
    }
    session = await runner.session_service.create_session(
        app_name=_APP_AUTHOR, user_id="casting", state=init_state
    )
    message = types.Content(role="user", parts=[types.Part(text="この企画に最も合う著者を3案出して1人に絞ってください")])
    async for _event in runner.run_async(user_id="casting", session_id=session.id, new_message=message):
        pass
    final = await runner.session_service.get_session(
        app_name=_APP_AUTHOR, user_id="casting", session_id=session.id
    )
    result = _norm_casting(final.state.get(K.AUTHOR_CASTING)) if final else None
    if result is None:
        raise RuntimeError("author_casting が AuthorCasting を返しませんでした")
    return result


def cast_author_vertex(
    plan: PlanProposal,
    *,
    reader_profile: Optional[ReaderProfile3Layer] = None,
    favorite_authors: Optional[list[dict[str, Any]]] = None,
    persona_inspiration: Optional[str] = None,
) -> AuthorCasting:
    """同期ラッパー（CLI/テストから）。**実Vertex・課金あり**。"""
    return asyncio.run(
        cast_author_vertex_async(
            plan,
            reader_profile=reader_profile,
            favorite_authors=favorite_authors,
            persona_inspiration=persona_inspiration,
        )
    )
