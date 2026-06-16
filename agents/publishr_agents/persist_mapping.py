"""C4結線: モードA v2出力 → shared-schema Book/Persona マッピング（純粋・決定的）。

run_mode_a の (plan, shelved, personas) を、書店UIが読む Book（shelf=arrivals・status=draft・
ownerUid付き）＋ Persona（生成著者）へ変換する。永続化（upsert）は呼び出し側（seed/BFF）が担う。
正本: docs/design/api-contract.md / agent-io-contract.md §5-2a。
"""

from __future__ import annotations

import re
from typing import Any, Optional, Protocol

from publishr_schema import (
    AgendaItem,
    Book,
    GeneratedPersona,
    Persona,
    PersonaDetail,
    PlanProposal,
)

# 既存 b_* / _sakura と衝突しない入荷本の接頭辞。run トークン（入荷時刻）を挟んで
# **run ごとにユニーク**にする（arr_<YYYYMMDDHHMMSS>_<personaId>）＝自律入荷を重ねても
# 過去の本を上書きせず書庫に積み上がる。著者IDにも同じトークンを付け、本→著者の参照を保つ。
_BOOK_ID_PREFIX = "arr_"
_MINUTES_PER_CHAPTER = 8


def _run_token(created_at: str) -> str:
    """入荷時刻(ISO)から ID 用の run トークン（YYYYMMDDHHMMSS）。空なら "0"。"""
    digits = re.sub(r"\D", "", created_at or "")
    return digits[:14] if digits else "0"


def _agenda(raw: list[dict[str, Any]]) -> list[AgendaItem]:
    return [
        AgendaItem(no=f"{i:02d}", title=e.get("chapter", f"第{i}章"), desc=e.get("summary", ""))
        for i, e in enumerate(raw or [], 1)
    ]


def _book(
    plan_id: str, theme_kind: str, owner_uid: str, entry: dict[str, Any], created_at: str,
    run_token: str,
) -> Book:
    bd = entry.get("bookDraft", {})
    agenda = _agenda(bd.get("agenda", []))
    persona_id = entry.get("personaId", "")
    uid = f"{run_token}_{persona_id}"  # run ごとにユニークな著者ID（本→著者の参照に使う）
    return Book(
        id=f"{_BOOK_ID_PREFIX}{uid}",
        plan_id=plan_id,
        status="draft",
        author_persona_id=uid,
        title=bd.get("title", "（無題）"),
        subtitle=bd.get("subtitle", ""),
        cover_variant=entry.get("coverVariant", "b1"),
        cover_url=entry.get("coverUrl"),
        shelf="arrivals",
        estimated_chapters=len(agenda),
        estimated_minutes=len(agenda) * _MINUTES_PER_CHAPTER,
        preface_sample=bd.get("prefaceSample", ""),
        agenda=agenda,
        owner_uid=owner_uid,
        kind=theme_kind,
        delivery_reason=bd.get("deliveryReason", ""),
        problem_to_solve=bd.get("problemToSolve", ""),
        core_message=bd.get("coreMessage", ""),
        created_at=created_at,
    )


def _persona(gp: GeneratedPersona, run_token: str) -> Persona:
    desc = gp.persona or ""
    monogram = gp.name.strip()[:1] if gp.name.strip() else "著"
    return Persona(
        id=f"{run_token}_{gp.persona_id}",  # 本の author_persona_id と一致させる（run ごと）
        name=gp.name,
        name_reading="",
        monogram=monogram,
        style=gp.voice_style,
        title=gp.format,
        persona=PersonaDetail(
            career=desc,
            style_note=f"{gp.voice_style} × {gp.format}",
            thought=desc,
            signature=[],
            themes=list(gp.expertise),
        ),
        expertise=list(gp.expertise),
        past_books=[],
        voice_style=gp.voice_style,
        format=gp.format,
        from_favorite=gp.from_favorite,
        ephemeral=gp.ephemeral,
    )


def map_mode_a_to_books(
    plan: PlanProposal,
    shelved: list[dict[str, Any]],
    personas: list[GeneratedPersona],
    *,
    owner_uid: str,
    plan_id: Optional[str] = None,
    created_at: str = "",
) -> tuple[list[Book], list[Persona]]:
    """モードA成果を (Book[], Persona[]) に変換。Book は arrivals/draft、Persona は使用著者のみ。

    created_at は入荷時刻（ISO8601）。書店UIの「今朝の入荷」ラベル・新着ソートに使う。
    """
    pid = plan_id or plan.proposal_id or "plan_arrivals"
    theme_kind = str(plan.theme_kind or "honmei")
    token = _run_token(created_at)  # run ごとに本/著者IDをユニーク化＝書庫に積み上げ（上書きしない）

    books = [_book(pid, theme_kind, owner_uid, e, created_at, token) for e in shelved]

    by_id = {p.persona_id: p for p in personas}
    out_personas = [
        _persona(by_id[i], token) for i in (e.get("personaId") for e in shelved) if i in by_id
    ]
    # 重複著者は1人に（personaId 単位）。
    seen: set[str] = set()
    deduped: list[Persona] = []
    for p in out_personas:
        if p.id not in seen:
            seen.add(p.id)
            deduped.append(p)

    return books, deduped


class _BookPersonaRepo(Protocol):
    def upsert_book(self, book: Book) -> Book: ...
    def upsert_persona(self, persona: Persona) -> Persona: ...


def persist_arrivals(repo: _BookPersonaRepo, books: list[Book], personas: list[Persona]) -> int:
    """生成著者→入荷本の順で repo に upsert（著者を先に＝Bookのauthor参照が解決可能に）。

    repo は RepositoryProtocol 互換（upsert_book / upsert_persona）。返り値＝投入Book数。冪等。
    """
    for persona in personas:
        repo.upsert_persona(persona)
    for book in books:
        repo.upsert_book(book)
    return len(books)
