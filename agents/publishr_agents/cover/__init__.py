"""STEP5 装丁（C1.6）。プレビュー5冊に coverVariant(CSS)＋coverPrompt(Imagen用)＋coverUrl を付与。

既定はオフライン決定的（PUBLISHR_LLM=mock・coverUrl=None）。PUBLISHR_LLM=vertex で coverPrompt を
Flash 生成、さらに ENABLE_IMAGEN=true で実 Imagen 画像を生成して coverUrl を埋める（隔離・課金）。
"""

from __future__ import annotations

import os
from typing import Any, Optional

from publishr_schema import GeneratedPersona

from .deterministic import design_covers_deterministic


def _imagen_enabled(flag: Optional[bool]) -> bool:
    if flag is not None:
        return flag
    return os.environ.get("ENABLE_IMAGEN", "").lower() in ("1", "true", "yes")


def design_covers(
    books: list[dict[str, Any]],
    personas: list[GeneratedPersona],
    *,
    llm: Optional[str] = None,
    enable_imagen: Optional[bool] = None,
) -> list[dict[str, Any]]:
    """STEP5 の入口。llm 未指定なら PUBLISHR_LLM で解決（mock=決定的 / vertex=Flash＋任意Imagen）。"""
    mode = (llm or os.environ.get("PUBLISHR_LLM", "mock")).lower()
    if mode == "mock":
        return design_covers_deterministic(books, personas)
    if mode == "vertex":
        from .vertex_agent import design_covers_vertex

        return design_covers_vertex(books, personas, enable_imagen=_imagen_enabled(enable_imagen))
    raise ValueError(f"unknown PUBLISHR_LLM={mode!r}")


__all__ = ["design_covers", "design_covers_deterministic"]
