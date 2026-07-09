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
import re
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


def _is_intro(no: str, title: str) -> bool:
    return no in {"はじめに", "序章", "序", "まえがき"} or title in {"はじめに", "まえがき"}


def _is_outro(no: str, title: str) -> bool:
    return no in {"おわりに", "終章", "終", "あとがき", "最後に"} or title in {"おわりに", "あとがき", "最後に"}


def _display_no(no: str) -> str:
    raw = no.strip()
    if raw.isdigit():
        return f"{int(raw)}章"
    return raw


def _normalize_chapter(a: Any) -> Any:
    if _is_intro(a.no, a.title):
        return a.model_copy(update={"no": "はじめに", "title": a.title if a.title != "はじめに" else "はじめに"})
    if _is_outro(a.no, a.title):
        return a.model_copy(update={"no": "おわりに", "title": a.title if a.title != "おわりに" else "おわりに"})
    return a.model_copy(update={"no": _display_no(a.no)})


def _select_chapters(book: Book) -> list[Any]:
    """はじめに＋最大N番号章＋おわりにを採用する。Nは番号章だけに適用する。"""
    agenda = list(book.agenda or [])
    intro = [a for a in agenda if _is_intro(a.no, a.title)][:1]
    outro = [a for a in agenda if _is_outro(a.no, a.title)][:1]
    numbered = [a for a in agenda if not _is_intro(a.no, a.title) and not _is_outro(a.no, a.title)]
    return [_normalize_chapter(a) for a in (intro + numbered[:_max_chapters()] + outro)]


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
# 過去ラウンドの指摘（無ければ無視）
{{priorFeedback}}
BodyVerdict のJSONのみを出力せよ（弱い章は weakChapters に章番号=1始まりで列挙）。"""

# ── 機械チェック（B・7/1レビュー）: book.delivery_reason（固有の生情報に触れてよい唯一の場所）
# から本文に漏れてはいけない固有名詞候補を抽出する。単一英字+社/日付/氏名敬称の狭いパターンに
# 絞り、「他社」「弊社」等の一般語を誤検出しない（p1「A社」がそのまま本文に残った実例の再発防止）。
_COMPANY_PAT = re.compile(r"[A-Za-zＡ-Ｚａ-ｚ]社")
_DATE_PATS = [re.compile(r"\d{1,2}/\d{1,2}"), re.compile(r"\d{1,2}月\d{1,2}日")]
_PERSON_PAT = re.compile(r"[一-龠]{2,4}(?:さん|様|氏)")


def _extract_raw_terms(text: Optional[str]) -> list[str]:
    """delivery_reason から本文に漏れてはいけない固有名詞候補を抽出する。"""
    if not text:
        return []
    terms: set[str] = set()
    terms.update(_COMPANY_PAT.findall(text))
    for pat in _DATE_PATS:
        terms.update(pat.findall(text))
    terms.update(_PERSON_PAT.findall(text))
    return sorted(terms)


def _chapters_containing(chapters: list[dict[str, Any]], terms: list[str]) -> list[int]:
    """terms のいずれかを含む章のインデックス（1始まり）を返す。"""
    if not terms:
        return []
    hits: list[int] = []
    for i, ch in enumerate(chapters, start=1):
        if any(t in (ch.get("text") or "") for t in terms):
            hits.append(i)
    return hits


def _mechanical_override(
    verdict: Optional[BodyVerdict], chapters: list[dict[str, Any]], raw_terms: list[str]
) -> Optional[BodyVerdict]:
    """judge が approve でも、読者プロファイル由来の固有名詞が本文に残っていれば revise へ強制する。

    p1: 編集長R1が「A社」漏れを一度指摘したのに、R2で見逃して承認した実例の再発防止（7/1レビュー）。
    LLMの判定を全面的に信頼せず、この一点だけは決定的に照合する。
    """
    if verdict is None:
        return None
    hit_chapters = _chapters_containing(chapters, raw_terms)
    if not hit_chapters or set(hit_chapters) <= set(verdict.weak_chapters):
        return verdict
    note = f"[機械チェック] 読者プロファイル由来の固有情報が本文に残存: {raw_terms}（型へ一般化すること）"
    merged_weak = sorted(set(verdict.weak_chapters) | set(hit_chapters))
    feedback = f"{verdict.editor_feedback}\n{note}" if verdict.editor_feedback else note
    return verdict.model_copy(
        update={"decision": "revise", "weak_chapters": merged_weak, "editor_feedback": feedback}
    )


_MERMAID_BLOCK_PAT = re.compile(r"```mermaid\s*\n(.*?)```", re.DOTALL)
_FLOW_DIR_PAT = re.compile(r"flowchart\s+(TD|LR|TB|RL|BT)", re.IGNORECASE)
_NODE_ID_PAT = re.compile(r"\b([A-Za-z][A-Za-z0-9_]*)\s*[\[({]")
_SUBGRAPH_PAT = re.compile(r"^\s*subgraph\b", re.IGNORECASE | re.MULTILINE)


def _extract_mermaid_blocks(text: str) -> list[str]:
    """章本文から ```mermaid フェンス内のソースを抽出する（複数可）。"""
    return [m.strip() for m in _MERMAID_BLOCK_PAT.findall(text or "")]


def _mermaid_layout_violations(src: str) -> list[str]:
    """1つの mermaid ソースに対する規律違反理由を返す（空なら違反なし）。

    Mermaid はブラウザ専用ライブラリのためサーバ側でレンダリング検証はできない。
    正規表現による近似（ノードID数・方向・矢印数・subgraph数のカウント）に限定し、
    誤検出を許容してでも「明らかに複雑すぎる図」だけを弾く保守的な閾値にする
    （閾値は modeB_author_body.md の図解規律＝縦ステップ4〜8・総ノード7以内・subgraph1個以内と一致させる）。
    """
    reasons: list[str] = []
    dir_match = _FLOW_DIR_PAT.search(src)
    direction = dir_match.group(1).upper() if dir_match else "TD"
    # subgraph 宣言行はノードIDと誤カウントしやすいので除いてから数える。
    body_wo_subgraph = _SUBGRAPH_PAT.sub("", src)
    total_nodes = len(set(_NODE_ID_PAT.findall(body_wo_subgraph)))
    if total_nodes > 7:
        reasons.append(f"総ノード数{total_nodes}個（7個以内の規律超過）")
    if direction in ("LR", "RL") and total_nodes >= 4:
        reasons.append(f"{direction}方向で{total_nodes}ノードが横並び（横方向は最大3ノードの規律違反）")
    arrow_count = len(re.findall(r"-->", src))
    if direction in ("TD", "TB") and arrow_count > 8:
        reasons.append(f"矢印{arrow_count}本（縦ステップ4〜8の規律超過）")
    subgraph_count = len(_SUBGRAPH_PAT.findall(src))
    if subgraph_count > 1:
        reasons.append(f"subgraph{subgraph_count}個（1図につき1個以内の規律超過。横幅を過大に食う）")
    return reasons


def _mermaid_layout_override(
    verdict: Optional[BodyVerdict], chapters: list[dict[str, Any]]
) -> Optional[BodyVerdict]:
    """図解が規律（総ノード7以内・横3以内・縦8以内）を超過した章を weak_chapters に強制する。"""
    if verdict is None:
        return None
    hit: dict[int, list[str]] = {}
    for i, ch in enumerate(chapters, start=1):
        for block in _extract_mermaid_blocks(ch.get("text") or ""):
            reasons = _mermaid_layout_violations(block)
            if reasons:
                hit.setdefault(i, []).extend(reasons)
    hit_chapters = sorted(hit)
    if not hit_chapters or set(hit_chapters) <= set(verdict.weak_chapters):
        return verdict
    detail = "; ".join(f"第{i}章: {', '.join(rs)}" for i, rs in hit.items())
    note = f"[機械チェック] 図解が規律超過: {detail}（ノードを間引く/図を分割/箇条書きに置換すること）"
    merged_weak = sorted(set(verdict.weak_chapters) | set(hit_chapters))
    feedback = f"{verdict.editor_feedback}\n{note}" if verdict.editor_feedback else note
    return verdict.model_copy(
        update={"decision": "revise", "weak_chapters": merged_weak, "editor_feedback": feedback}
    )


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
    sel = _select_chapters(book)
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

    # 本文に漏れてはいけない固有名詞候補（delivery_reason 由来）。ラウンドをまたいだ機械チェックに使う。
    raw_terms = _extract_raw_terms(book.delivery_reason)
    # 過去ラウンドの editorFeedback 履歴（次ラウンドの judge に渡し、既出の指摘を再確認させる）。
    prior_feedback_lines: list[str] = []

    verdicts: list[dict[str, Any]] = []
    revised: list[int] = []
    edit_rounds = 1

    v = await _run_verdict(
        editor,
        {"body": _body(chapters), "readerProfile": profile_dump, "persona": persona_dump, "priorFeedback": None},
    )
    v = _mechanical_override(v, chapters, raw_terms)
    v = _mermaid_layout_override(v, chapters)
    if v is not None:
        verdicts.append(v.model_dump(by_alias=True))
        if v.editor_feedback:
            prior_feedback_lines.append(f"R1: {v.editor_feedback}")

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
        prior_feedback = "\n".join(prior_feedback_lines) if prior_feedback_lines else None
        current = await _run_verdict(
            editor,
            {
                "body": _body(chapters),
                "readerProfile": profile_dump,
                "persona": persona_dump,
                "priorFeedback": prior_feedback,
            },
        )
        current = _mechanical_override(current, chapters, raw_terms)
        current = _mermaid_layout_override(current, chapters)
        if current is not None:
            verdicts.append(current.model_dump(by_alias=True))
            if current.editor_feedback:
                prior_feedback_lines.append(f"R{edit_rounds}: {current.editor_feedback}")
        else:
            break

    # rounds を使い切っても current が revise のままなら「本当は未承認」（7/1レビューで実測・p2ケース）。
    # mock と違い vertex は decision を書き換えない＝ここで明示的に検出して残す。
    # _mechanical_override 済みの current を使うため、機械チェックでの residual もここに反映される。
    forced_approve = current is not None and current.decision != "approve"

    return BodyResult(
        book_id=book.id,
        chapters=chapters,
        body=_body(chapters),
        verdicts=verdicts,
        body_verdict=verdicts[-1] if verdicts else {},
        edit_rounds=edit_rounds,
        revised_chapters=revised,
        forced_approve=forced_approve,
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
