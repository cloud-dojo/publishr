"""表紙処理パッケージ。

現行メインパイプラインの表紙は CSS variant のみ（`assign_cover_variants`・オフライン決定的・
coverUrl=None・画像生成なし）。

⚠️ 画像生成（Imagen）による装丁 `design_covers` は今回スコープ外で park（将来実装予定）。
   PUBLISHR_LLM=vertex で Flash が coverPrompt を生成し ENABLE_IMAGEN=true で実画像を作る
   フルパイプラインは温存する（削除しない）が、現行メインパイプライン（mode_a）からは呼ばれない。
   再結線するときは mode_a の `assign_cover_variants` 呼び出しを `design_covers` に戻す。
"""

from __future__ import annotations

import os
from typing import Any, Optional

from publishr_schema import GeneratedPersona

from .deterministic import assign_cover_variants, design_covers_deterministic


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
    plan: Optional[Any] = None,
) -> list[dict[str, Any]]:
    """⚠️ PARKED（将来実装・画像生成）: 現行メインパイプライン未接続。

    表紙の画像/ロゴ生成（Imagen）を含むフル装丁の入口。llm 未指定なら PUBLISHR_LLM で解決
    （mock=決定的 / vertex=Flash＋任意Imagen）。今回はスコープ外で main からは呼ばれない
    （main は `assign_cover_variants`＝CSS variant のみ）。将来再結線用に温存する。
    """
    mode = (llm or os.environ.get("PUBLISHR_LLM", "mock")).lower()
    if mode == "mock":
        return design_covers_deterministic(books, personas)
    if mode == "vertex":
        from .vertex_agent import design_covers_vertex

        return design_covers_vertex(
            books, personas, enable_imagen=_imagen_enabled(enable_imagen), plan=plan
        )
    raise ValueError(f"unknown PUBLISHR_LLM={mode!r}")


__all__ = ["assign_cover_variants", "design_covers", "design_covers_deterministic"]
