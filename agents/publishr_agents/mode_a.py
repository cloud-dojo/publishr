"""モードA 完全縦串の共有オーケストレーション（STEP0観測→1読者→2企画→3著者→4プレビュー→5装丁）。

CLI（run_mode_a.py / seed_arrivals.py）と BFF サービス（mode_a_service.py）が共通で使う単一の
入口。各 STEP は既存モジュールに委譲し、ここは「順番に呼んで成果をまとめる」だけ（mock挙動不変）。

`llm` 系は段階別に切替可（コスト制御）。既定は全 mock＝LLM 課金ゼロ・決定的。
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, NamedTuple, Optional

from publishr_schema import Book, GeneratedPersona, Persona, PlanProposal, User


class ModeAResult(NamedTuple):
    """モードAの成果一式（旧・単一テーマ）。"""

    plan: PlanProposal           # 採用企画
    shelved: list[dict[str, Any]]  # 装丁付き BookDraft（書店に並ぶ形）
    personas: list[Any]          # 使用した生成著者（GeneratedPersona）
    planning: dict[str, Any]     # 企画会議の生ログ（verdictHistory/rejectionFeedback 等＝却下→採用の証跡）


def run_mode_a_pipeline(
    user: User,
    *,
    source: Any,
    now: datetime,
    reader_llm: str = "mock",
    llm: str = "mock",
    preview_llm: str = "mock",
    cover_llm: str = "mock",
    enable_imagen: bool = False,
    theme: Optional[str] = None,
    theme_kind: str = "honmei",
    threshold: int = 70,
    limit: Optional[int] = None,
) -> ModeAResult:
    """観測→読者→企画→キャスティング→プレビュー→装丁 を一気通貫で回す。

    source は ObservationSource（FixtureObservationSource / GoogleObservationSource）。
    各 *_llm は "mock" | "vertex"。limit はプレビューで生成する冊数（コスト制御）。
    """
    from .casting import cast_personas
    from .cover import design_covers
    from .observe import collect_observation
    from .planning import run_planning
    from .preview import run_preview
    from .reader import analyze_reader

    bundle = collect_observation(user, now=now, source=source)
    profile = analyze_reader(bundle, user=user, llm=reader_llm)
    planning = run_planning(
        profile, theme=theme, theme_kind=theme_kind, threshold=threshold, llm=llm
    )
    plan = PlanProposal.model_validate(planning["approvedPlan"])
    persona_set = cast_personas(
        plan, reader_profile=profile, favorite_authors=list(user.favorite_authors or []), llm=llm
    )
    books = run_preview(plan, persona_set.personas, reader_profile=profile, limit=limit, llm=preview_llm)
    shelved = design_covers(books, persona_set.personas, llm=cover_llm, enable_imagen=enable_imagen)
    return ModeAResult(plan=plan, shelved=shelved, personas=list(persona_set.personas), planning=planning)


# ══════════════════════════════════════════════════════════════════════════
# v3 4テーマ1-1-1-1 縦串（予約制廃止改定 2026-06-23・本丸）
#   observe → reader → run_planning_set(4テーマ→4承認plan) →
#   各テーマ[キャスティング1著者 → プレビュー1冊 → 装丁] → 棚に4冊
#   旧 run_mode_a_pipeline（単一テーマ）は温存。本関数は additive な新パス。
# ══════════════════════════════════════════════════════════════════════════
class ModeABook(NamedTuple):
    """1テーマ＝1冊の成果（4テーマで4つ）。"""

    plan: PlanProposal                  # この冊の承認企画
    shelved: list[dict[str, Any]]       # 装丁付き BookDraft（新モデルは1冊）
    personas: list[GeneratedPersona]    # この冊の著者（1人）


class ModeASetResult(NamedTuple):
    """モードA セット成果（4テーマ・1-1-1-1）。"""

    books: list[ModeABook]       # 4テーマ＝4冊（1冊/テーマ）
    planning: dict[str, Any]     # セット企画ログ（themeAssignmentSet/planSetVerdict/rejectLog＝却下→採用の証跡）


def run_mode_a_set_pipeline(
    user: User,
    *,
    source: Any,
    now: datetime,
    reader_llm: str = "mock",
    llm: str = "mock",
    preview_llm: str = "mock",
    cover_llm: str = "mock",
    enable_imagen: bool = False,
    theme_kind: str = "honmei",
    threshold: int = 70,
) -> ModeASetResult:
    """観測→読者→セット企画(4テーマ)→各テーマ[キャスティング→プレビュー→装丁] を回し、棚に4冊並べる。

    各 *_llm は "mock" | "vertex"。1テーマ=1著者=1冊（多様性は配本属性＋テーマ別著者で担保）。
    """
    from .casting import cast_author
    from .cover import design_covers
    from .observe import collect_observation
    from .planning import run_planning_set
    from .preview import run_preview
    from .reader import analyze_reader

    bundle = collect_observation(user, now=now, source=source)
    profile = analyze_reader(bundle, user=user, llm=reader_llm)
    planning = run_planning_set(profile, theme_kind=theme_kind, threshold=threshold, llm=llm)
    plans = [PlanProposal.model_validate(p) for p in planning["planSet"]["plans"]]

    favorites = list(user.favorite_authors or [])
    out: list[ModeABook] = []
    for plan in plans:
        # 1テーマ=1冊：author_casting で3候補→1選抜。
        casting = cast_author(plan, reader_profile=profile, favorite_authors=favorites, llm=llm)
        chosen = []
        if casting.chosen:
            # vertex casting は候補IDを c1/c2/c3 等で返し4冊間で衝突する。plan スコープに再id し、
            # book id = arr_<personaId> の4冊一意性を保証（mock/vertex どちらでも安全）。
            chosen = [casting.chosen.model_copy(update={"persona_id": f"cast_{plan.proposal_id}"})]
        drafts = run_preview(plan, chosen, reader_profile=profile, limit=1, llm=preview_llm)
        shelved = design_covers(drafts, chosen, llm=cover_llm, enable_imagen=enable_imagen)
        out.append(ModeABook(plan=plan, shelved=shelved, personas=chosen))
    return ModeASetResult(books=out, planning=planning)


def map_mode_a_set_to_books(
    result: ModeASetResult, *, owner_uid: str, created_at: str = ""
) -> tuple[list[Book], list[Persona]]:
    """セット成果（4冊）を (Book[], Persona[]) に集約。各テーマ冊を既存 map_mode_a_to_books で変換し統合。"""
    from .persist_mapping import map_mode_a_to_books

    all_books: list[Book] = []
    all_personas: list[Persona] = []
    seen: set[str] = set()
    for mb in result.books:
        bks, ps = map_mode_a_to_books(
            mb.plan, mb.shelved, mb.personas, owner_uid=owner_uid, created_at=created_at
        )
        all_books.extend(bks)
        for p in ps:
            if p.id not in seen:
                seen.add(p.id)
                all_personas.append(p)
    return all_books, all_personas
