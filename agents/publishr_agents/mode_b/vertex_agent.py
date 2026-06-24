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
from ..llm.resilience import RetryPolicy, run_with_retry_async  # noqa: E402
from ..prompts import render  # noqa: E402

_APP = "publishr_modeb"
_BODY_VERDICT_KEY = "bodyVerdict"
_DEFAULT_MAX_CHAPTERS = 5

logger = logging.getLogger(__name__)


def _on_retry(attempt: int, err: BaseException, delay: float) -> None:
    """transient な Vertex エラーのリトライをログに残す（C5.9）。"""
    logger.warning(
        "vertex transient error (retry %d in %.1fs): %s: %s",
        attempt,
        delay,
        type(err).__name__,
        err,
    )


def _max_chapters() -> int:
    """採用章数の上限。既定5（mock/テスト互換）。本番100pは PUBLISHR_BODY_MAX_CHAPTERS で増やす。"""
    try:
        return max(1, int(os.environ.get("PUBLISHR_BODY_MAX_CHAPTERS", str(_DEFAULT_MAX_CHAPTERS))))
    except ValueError:
        return _DEFAULT_MAX_CHAPTERS


def _resolve_volume(n_chapters: int) -> tuple[str, str]:
    """本全体の目安と各章の目標文字数を解決する（I-35・パラメータ化）。

    優先順位:
      1. `PUBLISHR_BODY_CHARS_PER_CHAPTER`（章単位の明示指定・CLI run_full_book 互換）。
         指定時は本全体＝章数×章単位 で逆算する。
      2. 実行プロファイル（dev/prod）の `body_char_target`（本全体・既定の制御ノブ）。
         `PUBLISHR_BODY_CHAR_TARGET` で上書き可。各章＝本全体÷採用章数 で導出。

    返り値: (body_volume＝system へ注入する本全体目安, per_chapter_hint＝入力ブロックの章ヒント)。
    """
    chapters = max(1, n_chapters)
    per_chapter_env = os.environ.get("PUBLISHR_BODY_CHARS_PER_CHAPTER", "").strip()
    if per_chapter_env:
        try:
            per_chapter = max(1, int(per_chapter_env))
        except ValueError:
            per_chapter = 0
        if per_chapter:
            total = per_chapter * chapters
            return _volume_str(total), _per_chapter_hint(per_chapter)

    # プロファイル既定（PUBLISHR_BODY_CHAR_TARGET 上書き可）。0/未満なら制御なし＝プロンプト既定に委ねる。
    from ..llm.runtime import profile_from_env

    total = profile_from_env().body_char_target
    if total <= 0:
        return "", ""
    per_chapter = max(1, total // chapters)
    return _volume_str(total), _per_chapter_hint(per_chapter)


def _volume_str(total: int) -> str:
    return f"{total:,}字"


def _per_chapter_hint(per_chapter: int) -> str:
    return (
        f"この章を **{per_chapter:,}字程度** でしっかり執筆する"
        "（具体例・手順・小見出しを使い、水増しせず密度高く）。"
    )


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
    # transient(タイムアウト/503/429)のみ指数バックオフでリトライ。各試行は新規runner/session（C5.9）。
    async def _once() -> str:
        runner = InMemoryRunner(agent=agent, app_name=_APP)
        session = await runner.session_service.create_session(
            app_name=_APP, user_id="modeb", state=init_state
        )
        message = types.Content(role="user", parts=[types.Part(text="本文を書いてください")])
        text = ""
        async for event in runner.run_async(
            user_id="modeb", session_id=session.id, new_message=message
        ):
            content = getattr(event, "content", None)
            if content and content.parts:
                for part in content.parts:
                    if getattr(part, "text", None):
                        text = part.text
        return text.strip()

    return await run_with_retry_async(_once, policy=RetryPolicy.from_env(), on_retry=_on_retry)


async def _run_verdict(agent: LlmAgent, init_state: dict[str, Any]) -> Optional[BodyVerdict]:
    async def _once() -> Optional[BodyVerdict]:
        runner = InMemoryRunner(agent=agent, app_name=_APP)
        session = await runner.session_service.create_session(
            app_name=_APP, user_id="modeb", state=init_state
        )
        message = types.Content(role="user", parts=[types.Part(text="本文を採点してください")])
        async for _event in runner.run_async(
            user_id="modeb", session_id=session.id, new_message=message
        ):
            pass
        final = await runner.session_service.get_session(
            app_name=_APP, user_id="modeb", session_id=session.id
        )
        return _norm_verdict(final.state.get(_BODY_VERDICT_KEY) if final else None)

    return await run_with_retry_async(_once, policy=RetryPolicy.from_env(), on_retry=_on_retry)


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
    body_volume, target_chars = _resolve_volume(len(sel))
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
                # system プロンプト({{body_volume}})を生かす本全体の目安（I-35）。
                "body_volume": body_volume,
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
