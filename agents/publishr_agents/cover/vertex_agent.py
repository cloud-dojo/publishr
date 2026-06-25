"""STEP5 装丁の実Vertex実装（PUBLISHR_LLM=vertex・隔離）。

Flash 軽エージェントが各本の coverPrompt（Imagen用英語・文字焼かない）を生成。coverVariant は
決定的(CSS)。ENABLE_IMAGEN=true なら imagen.py で実画像を生成して coverUrl を埋める。
step5_cover プロンプトを結線。**実LLM・課金あり**（Imagen は画像課金）。
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
from publishr_schema import GeneratedPersona  # noqa: E402

from ..llm.provider import model_for  # noqa: E402
from ..prompts import loader, render  # noqa: E402
from .deterministic import cover_variant_for

_APP = "publishr_cover"
_COVER_PROMPT_KEY = "coverPrompt"

logger = logging.getLogger(__name__)


def build_cover_prompt_agent() -> LlmAgent:
    """coverPrompt（英語）を生成する Flash 軽エージェント。"""
    user_template = loader.load_prompt("step5_cover").user_template or ""

    def instruction(ctx: Any) -> str:
        base = render.build_system_text("cover", ctx.state)
        return base + "\n\n# 入力\n" + render.render_template(user_template, ctx.state)

    return LlmAgent(
        name="cover",
        model=model_for("cover"),
        instruction=instruction,
        output_key=_COVER_PROMPT_KEY,  # 構造化せず英語プロンプト文字列
    )


async def _run_prompt(agent: LlmAgent, state: dict[str, Any]) -> str:
    runner = InMemoryRunner(agent=agent, app_name=_APP)
    session = await runner.session_service.create_session(app_name=_APP, user_id="cover", state=state)
    message = types.Content(role="user", parts=[types.Part(text="この本の表紙プロンプトを生成してください")])
    async for _event in runner.run_async(user_id="cover", session_id=session.id, new_message=message):
        pass
    final = await runner.session_service.get_session(app_name=_APP, user_id="cover", session_id=session.id)
    value = final.state.get(_COVER_PROMPT_KEY) if final else None
    return str(value).strip() if value else ""


async def design_covers_vertex_async(
    books: list[dict[str, Any]],
    personas: list[GeneratedPersona],
    *,
    enable_imagen: bool = False,
) -> list[dict[str, Any]]:
    agent = build_cover_prompt_agent()
    pmap = {p.persona_id: p for p in personas}
    results: list[dict[str, Any]] = []
    for i, book in enumerate(books):
        persona = pmap.get(book.get("personaId"))
        # 1冊ぶんの企画書（STEP2 PlanProposal の確定版）を state に載せる＝表紙は企画書ベースの1対1。
        # 後方互換: plan / approvedPlan が無ければ {} で素通し（title/coreMessage で従来通り動く）。
        state = {
            "bookDraft": book.get("bookDraft", {}),
            "plan": book.get("plan") or book.get("approvedPlan") or {},
            "persona": persona.model_dump(by_alias=True) if persona else {},
        }
        prompt = await _run_prompt(agent, state)
        variant = cover_variant_for(i)

        cover_url: Optional[str] = None
        if enable_imagen and prompt:
            from .imagen import generate_cover_image

            book_id = book.get("bookDraft", {}).get("bookId") or f"book_{book.get('personaId', i)}"
            try:
                cover_url = generate_cover_image(prompt, book_id=book_id)
            except Exception as exc:  # noqa: BLE001 — 画像失敗は coverUrl=None に縮退（棚は空にしない）
                logger.warning("Imagen 生成失敗（%s）: %s", book_id, exc)

        results.append({**book, "coverVariant": variant, "coverPrompt": prompt, "coverUrl": cover_url})
    return results


def design_covers_vertex(
    books: list[dict[str, Any]],
    personas: list[GeneratedPersona],
    *,
    enable_imagen: bool = False,
) -> list[dict[str, Any]]:
    """同期ラッパー（CLI/テストから）。**実LLM・課金あり**（Imagen は画像課金）。"""
    return asyncio.run(design_covers_vertex_async(books, personas, enable_imagen=enable_imagen))
