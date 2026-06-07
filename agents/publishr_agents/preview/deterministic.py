"""STEP4 プレビュー編集の決定的オフライン実装（PUBLISHR_LLM=mock・既定）。

各著者が BookDraft(7項目)を書き、編集長が3観点で採点（1冊だけ1R改稿を実演）→棚5冊draft。
本格的な執筆・採点は実Vertex（vertex_agent）が担う。正本: agent-io-contract.md §5-2。
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
    return BookDraft(
        title=f"{plan.tentative_title}（{persona.name}）",
        subtitle=plan.core_message or plan.diff_from_market,
        # ③ deliveryReason＝入荷理由（観測の局面に触れる）
        delivery_reason=f"観測から「{challenge[:28]}」という局面が見えたため、いまこの一冊を。",
        # ④ problemToSolve＝読者の課題を著者の言葉で
        problem_to_solve=f"{challenge}（{persona.voice_style}の視点で解く）",
        # ⑤ coreMessage（voiceStyle を前面に＝②観点）
        core_message=f"{plan.core_message}—{persona.voice_style}で迷いを判断に変える。",
        # ⑥ agenda（章＋一行サマリー）
        agenda=[AgendaEntry(chapter=f"第{i}章", summary=s) for i, s in enumerate(outline, 1)],
        # ⑦ prefaceSample（name/format を前面に・読者へ名指し）
        preface_sample=(
            f"著者 {persona.name} より。{persona.format} で、"
            f"あなたの『{challenge[:18]}』に名指しで寄り添う「はじめに」。"
        ),
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
