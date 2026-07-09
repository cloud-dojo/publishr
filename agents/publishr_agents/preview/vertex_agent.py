"""STEP4 プレビュー編集の実Vertex実装（PUBLISHR_LLM=vertex・隔離）。

著者(author_preview→BookDraft)→編集長(editor_preview→EditorVerdict)を InMemoryRunner で実行し、
編集長が revise なら著者が1度だけ改稿→再採点（最高1R）。これを著者ごとに Python で回す。
limit で冊数を制御（live のコスト制御）。**実LLM・課金あり**。
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
    BookDraft,
    EditorVerdict,
    GeneratedPersona,
    PlanProposal,
    ReaderProfile3Layer,
)

from .. import state_keys as K  # noqa: E402
from ..llm.provider import model_for  # noqa: E402
from ..prompts import render  # noqa: E402

_APP = "publishr_preview"
_BOOK_DRAFT_KEY = "bookDraft"

logger = logging.getLogger(__name__)

_AUTHOR_INPUTS = """# 承認企画(PlanProposal・8項目)
{{approvedPlan}}
# 著者ペルソナ
{{persona}}
# 読者プロファイル(currentWork)
{{readerProfile}}
# 編集長フィードバック（差し戻し時のみ・無ければ無視）
{{editorFeedback}}
BookDraft（7項目: title/subtitle/deliveryReason/problemToSolve/coreMessage/agenda/prefaceSample）のJSONのみを出力せよ。"""

_EDITOR_INPUTS = """# 著者プレビュー(BookDraft)
{{bookDraft}}
# 読者プロファイル
{{readerProfile}}
# 著者ペルソナ
{{persona}}
EditorVerdict のJSONのみを出力せよ。"""


def build_author_agent() -> LlmAgent:
    def instruction(ctx: Any) -> str:
        base = render.build_system_text("author_preview", ctx.state)
        return base + "\n\n# 入力\n" + render.render_template(_AUTHOR_INPUTS, ctx.state)

    return LlmAgent(
        name="author_preview",
        model=model_for("author_preview"),
        instruction=instruction,
        output_schema=BookDraft,
        output_key=_BOOK_DRAFT_KEY,
    )


def build_editor_agent() -> LlmAgent:
    def instruction(ctx: Any) -> str:
        base = render.build_system_text("editor_preview", ctx.state)
        return base + "\n\n# 入力\n" + render.render_template(_EDITOR_INPUTS, ctx.state)

    return LlmAgent(
        name="editor_preview",
        model=model_for("editor_preview"),
        instruction=instruction,
        output_schema=EditorVerdict,
        output_key=K.EDITOR_VERDICT,
    )


def _norm(raw: Any, model_cls):
    if raw is None:
        return None
    try:
        data = raw.model_dump(by_alias=True) if hasattr(raw, "model_dump") else dict(raw)
        return model_cls.model_validate(data)
    except Exception as exc:  # noqa: BLE001 — live 検証の歩留まり用に真因を残す
        logger.warning("%s normalize failed: %s / raw=%.200s", model_cls.__name__, exc, repr(raw))
        return None


async def _run_once(agent: LlmAgent, init_state: dict[str, Any], output_key: str, model_cls):
    runner = InMemoryRunner(agent=agent, app_name=_APP)
    session = await runner.session_service.create_session(
        app_name=_APP, user_id="preview", state=init_state
    )
    message = types.Content(role="user", parts=[types.Part(text="プレビューを書いてください")])
    async for _event in runner.run_async(user_id="preview", session_id=session.id, new_message=message):
        pass
    final = await runner.session_service.get_session(
        app_name=_APP, user_id="preview", session_id=session.id
    )
    return _norm(final.state.get(output_key) if final else None, model_cls)


async def run_preview_vertex_async(
    plan: PlanProposal,
    personas: list[GeneratedPersona],
    *,
    reader_profile: Optional[ReaderProfile3Layer] = None,
    limit: Optional[int] = None,
) -> list[dict[str, Any]]:
    author = build_author_agent()
    editor = build_editor_agent()
    plan_dump = plan.model_dump(by_alias=True)
    profile_dump = reader_profile.model_dump(by_alias=True) if reader_profile else None
    selected = personas[:limit] if limit else personas

    results: list[dict[str, Any]] = []
    for persona in selected:
        persona_dump = persona.model_dump(by_alias=True)

        async def _author(feedback: Optional[str]) -> Optional[BookDraft]:
            return await _run_once(
                author,
                {
                    "approvedPlan": plan_dump,
                    "persona": persona_dump,
                    "readerProfile": profile_dump,
                    "editorFeedback": feedback,
                },
                _BOOK_DRAFT_KEY,
                BookDraft,
            )

        async def _editor(draft: BookDraft) -> Optional[EditorVerdict]:
            return await _run_once(
                editor,
                {
                    "bookDraft": draft.model_dump(by_alias=True),
                    "readerProfile": profile_dump,
                    "persona": persona_dump,
                },
                K.EDITOR_VERDICT,
                EditorVerdict,
            )

        draft = await _author(None)
        if draft is None:
            raise RuntimeError(f"author_preview が BookDraft を返しませんでした（{persona.persona_id}）")
        verdict = await _editor(draft)
        edit_rounds = 1
        # 編集長が revise なら著者が1度だけ改稿→再採点（最高1R）。
        if verdict is not None and verdict.decision == "revise":
            revised = await _author(verdict.editor_feedback)
            if revised is not None:
                draft = revised
                edit_rounds = 2
                verdict = await _editor(draft) or verdict
            else:
                # 再執筆に失敗。棚は空にしない（元 draft を出す）が、残った verdict は revise のまま。
                logger.warning("revise 後の再執筆に失敗（%s）。元 draft を棚に出す。", persona.persona_id)

        results.append(
            {
                "personaId": persona.persona_id,
                "bookDraft": draft.model_dump(by_alias=True),
                "verdict": verdict.model_dump(by_alias=True) if verdict else None,
                "editRounds": edit_rounds,
            }
        )
    return results


def run_preview_vertex(
    plan: PlanProposal,
    personas: list[GeneratedPersona],
    *,
    reader_profile: Optional[ReaderProfile3Layer] = None,
    limit: Optional[int] = None,
) -> list[dict[str, Any]]:
    """同期ラッパー（CLI/テストから）。**実Vertex・課金あり**。"""
    return asyncio.run(
        run_preview_vertex_async(plan, personas, reader_profile=reader_profile, limit=limit)
    )
