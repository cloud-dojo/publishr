"""STEP2 企画3階層（C1.3・必然性の本丸）。

ReaderProfile → 調査サブ×3 → 企画担当者(PlanProposal) → 企画リーダー(スコア差し戻し→escalate)。
既定はオフライン決定的（PUBLISHR_LLM=mock）。実分析は PUBLISHR_LLM=vertex（3サブgrounding＋Pro）。
"""

from __future__ import annotations

import os
from typing import Any, Optional

from publishr_schema import ReaderProfile3Layer

from .deterministic import derive_theme, run_planning_deterministic


def run_planning(
    profile: ReaderProfile3Layer,
    *,
    theme: Optional[str] = None,
    theme_kind: str = "honmei",
    threshold: int = 70,
    llm: Optional[str] = None,
) -> dict[str, Any]:
    """STEP2 の入口。llm 未指定なら PUBLISHR_LLM で解決（mock=決定的 / vertex=実Pro）。"""
    mode = (llm or os.environ.get("PUBLISHR_LLM", "mock")).lower()
    if mode == "mock":
        return run_planning_deterministic(
            profile, theme=theme, theme_kind=theme_kind, threshold=threshold
        )
    if mode == "vertex":
        from .vertex_agent import run_planning_vertex

        return run_planning_vertex(profile, theme=theme, theme_kind=theme_kind, threshold=threshold)
    raise ValueError(f"unknown PUBLISHR_LLM={mode!r}")


__all__ = ["run_planning", "run_planning_deterministic", "derive_theme"]
