"""モードB 本文編集ループの決定的（mock）実装。

著者が agenda から3〜5章を執筆 → 編集長が本文5観点で採点（弱章を1つ検出）→ 弱章のみ改稿 →
再採点で承認。改稿は弱章だけ差し替え、他章は不変（全文再生成しない＝コスト抑制）。
すべて決定的・課金ゼロ。実Pro 版は vertex_agent。
"""

from __future__ import annotations

from typing import Any, Optional

from publishr_schema import Book, Persona
from publishr_schema.agent_io import BodyScoreBreakdown, BodyVerdict

_REVISE_MARK = "（改稿）"
_MAX_CHAPTERS = 5


def _select_chapters(book: Book) -> list[tuple[str, str, str]]:
    """agenda から最大5章を採用（手動1冊スライス）。(no, title, desc)。"""
    return [(a.no, a.title, a.desc) for a in (book.agenda or [])[:_MAX_CHAPTERS]]


def _author_text(
    persona: Optional[Persona], no: str, title: str, desc: str, *, revised: bool
) -> str:
    """著者ペルソナを着た章本文（canned・決定的）。revised で弱章の改稿版。"""
    voice = persona.name if persona else "担当作家"
    text = (
        f"## {no} {title}\n\n"
        f"{desc or title}。この章では、いま現場で起きていることを言語化し、次の一歩へ落とす。\n\n"
        f"――{voice} は、読者の局面に即して具体例を重ねていく。\n"
    )
    if revised:
        text += (
            f"\n{_REVISE_MARK}手順を3ステップに分解し、明日から試せるチェックリストと"
            f"つまずきやすい失敗例の回避策を加えた（掴みと実践性の補強）。\n"
        )
    return text


def _weak_index(n: int) -> int:
    """決定的に弱章を1つ選ぶ（1-indexed）。3章以上なら3章目、少なければ最終章。"""
    return 3 if n >= 3 else max(n, 1)


def run_body_loop_deterministic(
    book: Book,
    *,
    persona: Optional[Persona] = None,
    reader_profile: Any = None,
    rounds: int = 1,
):
    from . import BodyResult

    sel = _select_chapters(book)
    n = len(sel)
    chapters: list[dict[str, Any]] = [
        {"no": no, "title": title, "text": _author_text(persona, no, title, desc, revised=False)}
        for (no, title, desc) in sel
    ]

    weak = _weak_index(n)
    verdicts: list[dict[str, Any]] = []

    # スコアは決定的なキャンド: 64=承認閾値(70)未満で差し戻し、80=改稿後に承認。
    # 弱い軸は hook(掴み)11→16・actionability(実践性)8→16 が持ち上がる物語。
    # round1: 弱章ありで差し戻し（編集長が著者を採点）。
    v1 = BodyVerdict(
        score=64,
        score_breakdown=BodyScoreBreakdown(
            coherence=16, hook=11, relevance=15, persona_consistency=14, actionability=8
        ),
        decision="revise",
        weak_chapters=[weak],
        editor_feedback=(
            f"第{weak}章の掴み(hook)と実践性(actionability)が弱い。"
            "手順を具体化し、行動に落ちる形へ書き直して再提出。"
        ),
    )
    verdicts.append(v1.model_dump(by_alias=True))

    revised_chapters: list[int] = []
    edit_rounds = 1

    if rounds >= 1 and n >= 1:
        # 弱章のみ改稿（他章は不変＝全文再生成しない）。
        i = weak - 1
        no, title, desc = sel[i]
        chapters[i] = {
            "no": no,
            "title": title,
            "text": _author_text(persona, no, title, desc, revised=True),
        }
        revised_chapters = [weak]
        edit_rounds = 2
        v2 = BodyVerdict(
            score=80,
            score_breakdown=BodyScoreBreakdown(
                coherence=17, hook=16, relevance=16, persona_consistency=15, actionability=16
            ),
            decision="approve",
            weak_chapters=[],
            editor_feedback=None,
        )
        verdicts.append(v2.model_dump(by_alias=True))

    body = "\n\n".join(ch["text"] for ch in chapters)
    return BodyResult(
        book_id=book.id,
        chapters=chapters,
        body=body,
        verdicts=verdicts,
        body_verdict=verdicts[-1],
        edit_rounds=edit_rounds,
        revised_chapters=revised_chapters,
    )
