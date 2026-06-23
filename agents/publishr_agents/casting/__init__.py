"""STEP3 キャスティング（C1.4）。承認企画 → 架空著者5人（voiceStyle×format 2軸）。

既定はオフライン決定的（PUBLISHR_LLM=mock）。実分析は PUBLISHR_LLM=vertex（Gemini Pro・1コール5人）。
"""

from __future__ import annotations

import os
from typing import Any, Optional

from publishr_schema import AuthorCasting, GeneratedPersonaSet, PlanProposal, ReaderProfile3Layer

from .deterministic import cast_author_deterministic, cast_personas_deterministic


def cast_personas(
    plan: PlanProposal,
    *,
    reader_profile: Optional[ReaderProfile3Layer] = None,
    favorite_authors: Optional[list[dict[str, Any]]] = None,
    llm: Optional[str] = None,
) -> GeneratedPersonaSet:
    """STEP3 の入口。llm 未指定なら PUBLISHR_LLM で解決（mock=決定的 / vertex=実Pro）。"""
    mode = (llm or os.environ.get("PUBLISHR_LLM", "mock")).lower()
    if mode == "mock":
        return cast_personas_deterministic(
            plan, reader_profile=reader_profile, favorite_authors=favorite_authors
        )
    if mode == "vertex":
        from .vertex_agent import cast_personas_vertex

        return cast_personas_vertex(
            plan, reader_profile=reader_profile, favorite_authors=favorite_authors
        )
    raise ValueError(f"unknown PUBLISHR_LLM={mode!r}")


def cast_author(
    plan: PlanProposal,
    *,
    reader_profile: Optional[ReaderProfile3Layer] = None,
    favorite_authors: Optional[list[dict[str, Any]]] = None,
    persona_inspiration: Optional[str] = None,
    llm: Optional[str] = None,
) -> AuthorCasting:
    """STEP3 author_casting（v3・4テーマ）の入口。1企画＝3候補→1選抜（AuthorCasting）。

    llm 未指定なら PUBLISHR_LLM で解決（mock=決定的 / vertex=実Pro）。
    """
    mode = (llm or os.environ.get("PUBLISHR_LLM", "mock")).lower()
    if mode == "mock":
        return cast_author_deterministic(
            plan, reader_profile=reader_profile, favorite_authors=favorite_authors
        )
    if mode == "vertex":
        from .vertex_agent import cast_author_vertex

        return cast_author_vertex(
            plan,
            reader_profile=reader_profile,
            favorite_authors=favorite_authors,
            persona_inspiration=persona_inspiration,
        )
    raise ValueError(f"unknown PUBLISHR_LLM={mode!r}")


__all__ = [
    "cast_personas",
    "cast_personas_deterministic",
    "cast_author",
    "cast_author_deterministic",
]
