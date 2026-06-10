"""モードB 本文編集ループの実Vertex実装（PUBLISHR_LLM=vertex・隔離・課金あり）。

著者(modeb_author・章本文MD)→編集長(modeb_editor→BodyVerdict)を InMemoryRunner で実行。
編集長が revise なら **弱章のみ** 著者が改稿→再採点（手動スライスは最高1R）。本文=読者が読む唯一の成果物。
プロンプト/モデルは既存の prompts registry（modeb_author/modeb_editor）＋ model_for（pro）を結線。
実行は live ゲート作業（`PUBLISHR_RUN_VERTEX=1`）。offline はエージェント構築のみ検証する。
"""

from __future__ import annotations

import asyncio
import logging
import os
import warnings
from typing import Any, Optional

warnings.filterwarnings("ignore", category=DeprecationWarning, module="google.adk")

from google.adk.agents import LlmAgent  # noqa: E402
from google.adk.runners import InMemoryRunner  # noqa: E402
from google.genai import types  # noqa: E402
from publishr_schema import Book, Persona  # noqa: E402
from publishr_schema.agent_io import BodyVerdict  # noqa: E402

from ..llm.provider import model_for  # noqa: E402
from ..prompts import render  # noqa: E402

_APP = "publishr_modeb"
_BODY_VERDICT_KEY = "bodyVerdict"
_DEFAULT_MAX_CHAPTERS = 5

logger = logging.getLogger(__name__)


def _max_chapters() -> int:
    """採用章数の上限。既定5（mock/テスト互換）。本番100pは PUBLISHR_BODY_MAX_CHAPTERS で増やす。"""
    try:
        return max(1, int(os.environ.get("PUBLISHR_BODY_MAX_CHAPTERS", str(_DEFAULT_MAX_CHAPTERS))))
    except ValueError:
        return _DEFAULT_MAX_CHAPTERS


def _target_chars_hint() -> str:
    """各章の目標文字数ヒント（PUBLISHR_BODY_CHARS_PER_CHAPTER・本番100p用）。未設定なら空。"""
    n = os.environ.get("PUBLISHR_BODY_CHARS_PER_CHAPTER", "").strip()
    return f"この章を **{n}字程度** でしっかり執筆する（具体例・手順・小見出しを使い、水増しせず密度高く）。" if n else ""


_AUTHOR_INPUTS = """# 本(agenda/coreMessage/title)
{{bookDraft}}
# 著者ペルソナ
{{persona}}
# 読者プロファイル
{{readerProfile}}
# 対象章
{{targetChapter}}
# 直前章の要約（無ければ無視）
{{prevChapterSummary}}
# 編集長フィードバック（改稿時のみ・無ければ無視）
{{editorFeedback}}
# 目標分量（指定があればその文字数程度で・無ければ無視）
{{targetChars}}
対象章の本文（Markdown・`## 見出し` から）だけを出力せよ。"""

_EDITOR_INPUTS = """# 本文（全章結合）
{{body}}
# 読者プロファイル
{{readerProfile}}
# 著者ペルソナ
{{persona}}
BodyVerdict のJSONのみを出力せよ（弱い章は weakChapters に章番号=1始まりで列挙）。"""


def build_author_agent() -> LlmAgent:
    def instruction(ctx: Any) -> str:
        base = render.build_system_text("modeb_author", ctx.state)
        return base + "\n\n# 入力\n" + render.render_template(_AUTHOR_INPUTS, ctx.state)

    return LlmAgent(name="modeb_author", model=model_for("modeb_author"), instruction=instruction)


def build_editor_agent() -> LlmAgent:
    def instruction(ctx: Any) -> str:
        base = render.build_system_text("modeb_editor", ctx.state)
        return base + "\n\n# 入力\n" + render.render_template(_EDITOR_INPUTS, ctx.state)

    return LlmAgent(
        name="modeb_editor",
        model=model_for("modeb_editor"),
        instruction=instruction,
        output_schema=BodyVerdict,
        output_key=_BODY_VERDICT_KEY,
    )


def _norm_verdict(raw: Any) -> Optional[BodyVerdict]:
    if raw is None:
        return None
    try:
        data = raw.model_dump(by_alias=True) if hasattr(raw, "model_dump") else dict(raw)
        return BodyVerdict.model_validate(data)
    except Exception as exc:  # noqa: BLE001 — live 歩留まりのため真因を残す
        logger.warning("BodyVerdict normalize failed: %s / raw=%.200s", exc, repr(raw))
        return None


async def _run_text(agent: LlmAgent, init_state: dict[str, Any]) -> str:
    runner = InMemoryRunner(agent=agent, app_name=_APP)
    session = await runner.session_service.create_session(app_name=_APP, user_id="modeb", state=init_state)
    message = types.Content(role="user", parts=[types.Part(text="本文を書いてください")])
    text = ""
    async for event in runner.run_async(user_id="modeb", session_id=session.id, new_message=message):
        content = getattr(event, "content", None)
        if content and content.parts:
            for part in content.parts:
                if getattr(part, "text", None):
                    text = part.text
    return text.strip()


async def _run_verdict(agent: LlmAgent, init_state: dict[str, Any]) -> Optional[BodyVerdict]:
    runner = InMemoryRunner(agent=agent, app_name=_APP)
    session = await runner.session_service.create_session(app_name=_APP, user_id="modeb", state=init_state)
    message = types.Content(role="user", parts=[types.Part(text="本文を採点してください")])
    async for _event in runner.run_async(user_id="modeb", session_id=session.id, new_message=message):
        pass
    final = await runner.session_service.get_session(app_name=_APP, user_id="modeb", session_id=session.id)
    return _norm_verdict(final.state.get(_BODY_VERDICT_KEY) if final else None)


async def run_body_loop_vertex_async(
    book: Book,
    *,
    persona: Optional[Persona] = None,
    reader_profile: Any = None,
    rounds: int = 1,
):
    from . import BodyResult

    author = build_author_agent()
    editor = build_editor_agent()
    persona_dump = persona.model_dump(by_alias=True) if persona else None
    profile_dump = reader_profile.model_dump(by_alias=True) if reader_profile else None
    sel = list((book.agenda or [])[:_max_chapters()])
    target_chars = _target_chars_hint()
    book_dump = {
        "title": book.title,
        "coreMessage": book.core_message,
        "agenda": [a.model_dump(by_alias=True) for a in sel],
    }

    async def _write(target: Any, feedback: Optional[str], prev_summary: Optional[str]) -> str:
        return await _run_text(
            author,
            {
                "bookDraft": book_dump,
                "persona": persona_dump,
                "readerProfile": profile_dump,
                "targetChapter": target.model_dump(by_alias=True),
                "prevChapterSummary": prev_summary,
                "editorFeedback": feedback,
                "targetChars": target_chars,
            },
        )

    chapters: list[dict[str, Any]] = []
    prev: Optional[str] = None
    for a in sel:
        text = await _write(a, None, prev)
        chapters.append({"no": a.no, "title": a.title, "text": text})
        prev = text[:200] if text else None

    def _body(chs: list[dict[str, Any]]) -> str:
        return "\n\n".join(c["text"] for c in chs)

    verdicts: list[dict[str, Any]] = []
    revised: list[int] = []
    edit_rounds = 1

    v = await _run_verdict(editor, {"body": _body(chapters), "readerProfile": profile_dump, "persona": persona_dump})
    if v is not None:
        verdicts.append(v.model_dump(by_alias=True))

    # 編集長が revise の間、弱章のみ改稿→再採点を最高 rounds 回（§6-2「最高3R」）。
    # NOTE: 弱章が複数の場合、各章に同じ editor_feedback を渡し prev_summary=None で改稿する
    # （章ごとの個別フィードバック・継続文脈は未対応・将来拡張）。
    current = v
    revises = 0
    while (
        current is not None
        and current.decision == "revise"
        and current.weak_chapters
        and revises < rounds
    ):
        for ch_no in current.weak_chapters:
            idx = ch_no - 1
            if 0 <= idx < len(sel):
                text = await _write(sel[idx], current.editor_feedback, None)
                chapters[idx] = {"no": sel[idx].no, "title": sel[idx].title, "text": text}
                if ch_no not in revised:
                    revised.append(ch_no)
        revises += 1
        edit_rounds = 1 + revises
        current = await _run_verdict(
            editor, {"body": _body(chapters), "readerProfile": profile_dump, "persona": persona_dump}
        )
        if current is not None:
            verdicts.append(current.model_dump(by_alias=True))
        else:
            break

    return BodyResult(
        book_id=book.id,
        chapters=chapters,
        body=_body(chapters),
        verdicts=verdicts,
        body_verdict=verdicts[-1] if verdicts else {},
        edit_rounds=edit_rounds,
        revised_chapters=revised,
    )


def run_body_loop_vertex(
    book: Book,
    *,
    persona: Optional[Persona] = None,
    reader_profile: Any = None,
    rounds: int = 1,
):
    """同期ラッパー（CLI/テストから）。**実Vertex・課金あり**。"""
    return asyncio.run(
        run_body_loop_vertex_async(book, persona=persona, reader_profile=reader_profile, rounds=rounds)
    )
