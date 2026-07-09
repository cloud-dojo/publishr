"""STEP1 読者分析（C1.2）。ObservationBundle → ReaderProfile3Layer(§3)。

既定はオフライン決定的（PUBLISHR_LLM=mock）。実分析は PUBLISHR_LLM=vertex（Gemini Pro・隔離）。
PUBLISHR_LLM シーム（llm/provider・registry）に乗る。
"""

from __future__ import annotations

import os
from typing import Optional

from publishr_schema import Book, ObservationBundle, ReaderProfile3Layer, User

from .deterministic import analyze_reader_deterministic


def analyze_reader(
    observation: ObservationBundle,
    *,
    user: Optional[User] = None,
    prev_profile: Optional[ReaderProfile3Layer] = None,
    past_books: Optional[list[Book]] = None,
    llm: Optional[str] = None,
) -> ReaderProfile3Layer:
    """STEP1 の入口。llm 未指定なら PUBLISHR_LLM で解決（mock=決定的 / vertex=実Pro）。

    past_books＝ユーザの過去公開本（C1.8 学習ループ＝反応/選択を読者分析に反映）。無ければ no-op。
    """
    mode = (llm or os.environ.get("PUBLISHR_LLM", "mock")).lower()
    if mode == "mock":
        return analyze_reader_deterministic(
            observation, user=user, prev_profile=prev_profile, past_books=past_books
        )
    if mode == "vertex":
        from .vertex_agent import analyze_reader_vertex

        return analyze_reader_vertex(
            observation, user=user, prev_profile=prev_profile, past_books=past_books
        )
    raise ValueError(f"unknown PUBLISHR_LLM={mode!r}")


__all__ = ["analyze_reader", "analyze_reader_deterministic"]
