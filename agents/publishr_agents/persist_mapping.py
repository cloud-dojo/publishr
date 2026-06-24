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


def _persona_uid(gp: GeneratedPersona, run_token: str) -> str:
    """著者IDの安定化方針。
    - お気に入り再登板（from_favorite）＝run をまたいで **同一ID** を保つ。casting が
      `persona_id` に登録時のお気に入りIDをそのまま入れるので、run-token を付けずに維持すれば
      毎runの再登板でも `favorites.has(id)` が一致し「お気に入り作家が書き続ける」が成立する。
    - それ以外＝run ごとユニーク（書庫に積み上げ・上書きしない）。
    """
    return gp.persona_id if gp.from_favorite else f"{run_token}_{gp.persona_id}"


def _agenda(raw: list[dict[str, Any]]) -> list[AgendaItem]:
    return [
        AgendaItem(no=f"{i:02d}", title=e.get("chapter", f"第{i}章"), desc=e.get("summary", ""))
        for i, e in enumerate(raw or [], 1)
    ]


def _book(
    plan_id: str, theme_kind: str, owner_uid: str, entry: dict[str, Any], created_at: str,
    run_token: str, author_uid: str,
) -> Book:
    bd = entry.get("bookDraft", {})
    agenda = _agenda(bd.get("agenda", []))
    persona_id = entry.get("personaId", "")
    return Book(
        # 本IDは run ごとユニーク＝積み上げ（お気に入り著者でも毎runの本は別冊）。
        id=f"{_BOOK_ID_PREFIX}{run_token}_{persona_id}",
        plan_id=plan_id,
        status="draft",
        # 著者参照はお気に入りなら安定ID（run またぎで同一）・それ以外は run-unique。
        author_persona_id=author_uid,
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
        id=_persona_uid(gp, run_token),  # 本の author_persona_id と一致（お気に入りは安定ID）
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
    run_token: Optional[str] = None,
) -> tuple[list[Book], list[Persona]]:
    """モードA成果を (Book[], Persona[]) に変換。Book は arrivals/draft、Persona は使用著者のみ。

    created_at は入荷時刻（ISO8601）。書店UIの「今朝の入荷」ラベル・新着ソートに使う。
    run_token（I-38）は book/persona ID 用の run 識別子。指定時はこれを ID トークンに使い、
    Pub/Sub 再配信（同一 run_id）でも **同じ book ID に upsert**＝重複入荷を防ぐ。未指定なら
    従来どおり created_at 由来（wall-clock）＝mock/直呼びは zero-diff。
    """
    pid = plan_id or plan.proposal_id or "plan_arrivals"
    theme_kind = str(plan.theme_kind or "honmei")
    # run ごとに本/著者IDをユニーク化。run_token 明示時は決定的（再配信で同一ID）、無指定は created_at 由来。
    token = run_token or _run_token(created_at)

    by_id = {p.persona_id: p for p in personas}

    def _author_uid(entry: dict[str, Any]) -> str:
        # 本の著者ID。お気に入り再登板は安定ID・それ以外は run-unique（persona と一致させる）。
        gp = by_id.get(entry.get("personaId", ""))
        return _persona_uid(gp, token) if gp is not None else f"{token}_{entry.get('personaId', '')}"

    books = [
        _book(pid, theme_kind, owner_uid, e, created_at, token, _author_uid(e)) for e in shelved
    ]
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
