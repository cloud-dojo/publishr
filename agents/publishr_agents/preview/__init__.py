"""STEP4 プレビュー編集（C1.5）。承認企画＋著者5人 → 各 BookDraft(7項目)＋編集長1R → 棚5冊draft。

既定はオフライン決定的（PUBLISHR_LLM=mock）。実分析は PUBLISHR_LLM=vertex（著者/編集長 Pro・1Rループ）。
"""

from __future__ import annotations

import os
from typing import Any, Optional

from publishr_schema import GeneratedPersona, PlanProposal, ReaderProfile3Layer

from .deterministic import run_preview_deterministic


def run_preview(
    plan: PlanProposal,
    personas: list[GeneratedPersona],
    *,
    reader_profile: Optional[ReaderProfile3Layer] = None,
    limit: Optional[int] = None,
    llm: Optional[str] = None,
) -> list[dict[str, Any]]:
    """STEP4 の入口。llm 未指定なら PUBLISHR_LLM で解決（mock=決定的 / vertex=実Pro）。

    limit は処理する著者数の上限（live のコスト制御用）。
    """
    mode = (llm or os.environ.get("PUBLISHR_LLM", "mock")).lower()
    if mode == "mock":
        return run_preview_deterministic(plan, personas, reader_profile=reader_profile, limit=limit)
    if mode == "vertex":
        from .vertex_agent import run_preview_vertex

        return run_preview_vertex(plan, personas, reader_profile=reader_profile, limit=limit)
    raise ValueError(f"unknown PUBLISHR_LLM={mode!r}")


__all__ = ["run_preview", "run_preview_deterministic"]
