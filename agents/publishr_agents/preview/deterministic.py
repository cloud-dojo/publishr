"""STEP4 プレビュー編集の決定的オフライン実装（PUBLISHR_LLM=mock・既定）。

各著者が BookDraft(7項目)を書き、編集長が3観点で採点（1冊だけ1R改稿を実演）→棚5冊draft。
本格的な執筆・採点は実Vertex（vertex_agent）が担う。
"""

from __future__ import annotations

from typing import Any, Optional

from publishr_schema import (
    AgendaEntry,
    BookDraft,
    EditorVerdict,
    GeneratedPersona,
    PlanProposal,
    PreviewScoreBreakdown,
    ReaderProfile3Layer,
)


def _draft(plan: PlanProposal, persona: GeneratedPersona, profile: Optional[ReaderProfile3Layer]) -> BookDraft:
    cw = profile.current_work if profile else None
    challenge = (cw.challenges[0] if cw and cw.challenges else "いまの局面")
    outline = plan.agenda_outline or ["現状の言語化", "型の提示", "局面別の適用"]
    is_serendipity = (plan.theme_kind or "") == "serendipity"

    if is_serendipity:
        # serendipity: 棚書き文法＝課題を直撃しない。関心の接続として書く。
        intellectual_territory = plan.theme or plan.tentative_title
        delivery_reason = (
            f"読者の関心の隣に「{intellectual_territory}」という知的領域がある。"
            f"好奇心の接続として、この一冊を。"
        )
        problem_to_solve = f"{plan.core_message}（{persona.voice_style}の切り口で）"
        preface_sample = (
            f"著者 {persona.name} より。{persona.format} で、"
            f"「{intellectual_territory}」という知的境界を越える体験の「はじめに」。"
        )
    else:
        # honmei: 課題直撃・観測局面に名指しで踏み込む
        delivery_reason = f"観測から「{challenge[:28]}」という局面が見えたため、いまこの一冊を。"
        problem_to_solve = f"{challenge}（{persona.voice_style}の視点で解く）"
        preface_sample = (
            f"著者 {persona.name} より。{persona.format} で、"
            f"あなたの『{challenge[:18]}』に名指しで寄り添う「はじめに」。"
        )

    agenda = [AgendaEntry(chapter="はじめに", summary="読者の局面に入り、この本の問いを開く")]
    agenda.extend(AgendaEntry(chapter=f"{i}章 {s}", summary=s) for i, s in enumerate(outline, 1))
    agenda.append(AgendaEntry(chapter="おわりに", summary="本全体を振り返り、明日からの最初の一歩へつなぐ"))

    return BookDraft(
        title=f"{plan.tentative_title}（{persona.name}）",
        subtitle=plan.core_message or plan.diff_from_market,
        delivery_reason=delivery_reason,
        problem_to_solve=problem_to_solve,
        # ⑤ coreMessage（voiceStyle を前面に＝②観点）
        core_message=f"{plan.core_message}—{persona.voice_style}で迷いを判断に変える。",
        # ⑥ agenda（はじめに＋章＋おわりに）
        agenda=agenda,
        preface_sample=preface_sample,
    )


def run_preview_deterministic(
    plan: PlanProposal,
    personas: list[GeneratedPersona],
    *,
    reader_profile: Optional[ReaderProfile3Layer] = None,
    limit: Optional[int] = None,
) -> list[dict[str, Any]]:
    selected = personas[:limit] if limit else personas
    results: list[dict[str, Any]] = []
    for i, persona in enumerate(selected):
        draft = _draft(plan, persona, reader_profile)
        if i == 1:
            # 2人目で1R改稿を実演（round1 不足→改稿→round2 採用）。
            verdict = EditorVerdict(
                round=2,
                score=60,
                score_breakdown=PreviewScoreBreakdown(raw_insight=21, persona_forward=20, catchiness=19),
                decision="approve",
                editor_feedback=None,
            )
            edit_rounds = 2
        else:
            verdict = EditorVerdict(
                round=1,
                score=62,
                score_breakdown=PreviewScoreBreakdown(raw_insight=21, persona_forward=21, catchiness=20),
                decision="approve",
                editor_feedback=None,
            )
            edit_rounds = 1
        results.append(
            {
                "personaId": persona.persona_id,
                "bookDraft": draft.model_dump(by_alias=True),
                "verdict": verdict.model_dump(by_alias=True),
                "editRounds": edit_rounds,
            }
        )
    return results
