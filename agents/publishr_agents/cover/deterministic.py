"""表紙の決定的オフライン装丁（PUBLISHR_LLM=mock・既定）。

現行メインパイプラインの表紙処理は `assign_cover_variants`＝coverVariant（globals.css の
cover--b1..b10）を決定的に付与するだけ（coverUrl=None・オフライン・ゼロコスト・画像生成なし）。

⚠️ 画像生成（Imagen 用 coverPrompt 生成・実画像）は今回スコープ外で park（将来実装予定）。
   下部 PARKED セクション（_VOICE_VISUAL / _cover_prompt / design_covers_deterministic）は
   将来の装丁（画像生成）用に温存し、現行メインパイプラインからは呼ばれない（cover/vertex_agent.py・
   imagen.py と対で再結線する）。
"""

from __future__ import annotations

from typing import Any, Optional

from publishr_schema import GeneratedPersona


def cover_variant_for(index: int) -> str:
    """globals.css の cover--b1..b140 に対応する決定的 variant 割当。色20×パターン7。"""
    return f"b{(index % 140) + 1}"


def assign_cover_variants(
    books: list[dict[str, Any]],
    personas: Optional[list[GeneratedPersona]] = None,
) -> list[dict[str, Any]]:
    """プレビュー結果に表紙 CSS variant を決定的付与（装飾のみ・画像生成なし）＝現行メインの表紙処理。

    各 book に coverVariant（CSS）＋ coverUrl=None を付ける。personas は将来の画像生成用に
    受け取るが CSS variant の決定には使わない（後方互換のための任意引数）。入力は破壊しない。
    """
    return [
        {**book, "coverVariant": cover_variant_for(i), "coverUrl": None}
        for i, book in enumerate(books)
    ]


# ═══════════════════════════════════════════════════════════════════════════
# ⬇️ PARKED（将来実装・画像生成）: 現行メインパイプライン未接続。
#    表紙の画像/ロゴ生成（Imagen 用 coverPrompt）は今回スコープ外。将来 vertex_agent.py /
#    imagen.py と合わせて再結線するときのために温存する（削除しない）。
# ═══════════════════════════════════════════════════════════════════════════

# voiceStyle → ビジュアル方針（決定的）。※画像生成 park のため現行未使用。
_VOICE_VISUAL: dict[str, str] = {
    "ロジカル・構造化": "geometric precision, generous negative space, calm off-white with deep navy and slate accents",
    "感覚的・情緒的": "soft watercolor texture, warm muted tones, a single evocative motif, gentle light",
    "学術的": "clean editorial grid, restrained palette, abstract diagram motif",
    "泥臭い・現場": "tactile paper texture, earthy tones, hand-drawn motif, honest and grounded",
    "思想的・哲学的": "quiet chiaroscuro, abstract shapes, deep contrast, contemplative",
}
_FALLBACK_VISUAL = "minimalist editorial business-book cover, restrained palette, one symbolic motif"


def _cover_prompt(title: str, core_message: str, persona: Optional[GeneratedPersona]) -> str:
    voice = persona.voice_style if persona else ""
    fmt = persona.format if persona else ""
    visual = _VOICE_VISUAL.get(voice, _FALLBACK_VISUAL)
    return (
        f"Minimalist editorial business-book cover for the theme of {core_message or title}. "
        f"Style translated from voiceStyle={voice} / format={fmt}: {visual}. "
        "One symbolic motif only, modern and trustworthy, flat vector style, book-cover composition. "
        "No text, no lettering, no logos, no real human faces."
    )


def design_covers_deterministic(
    books: list[dict[str, Any]],
    personas: list[GeneratedPersona],
) -> list[dict[str, Any]]:
    """⚠️ PARKED（将来実装・画像生成）: 現行メインパイプライン未接続。

    将来の装丁（画像生成）用に coverVariant＋coverPrompt（Imagen用英語）＋coverUrl=None を付与。
    現行メインの表紙処理は上部 `assign_cover_variants`（CSS variant のみ）を使う。
    """
    pmap = {p.persona_id: p for p in personas}
    results: list[dict[str, Any]] = []
    for i, book in enumerate(books):
        persona = pmap.get(book.get("personaId"))
        draft = book.get("bookDraft", {})
        prompt = _cover_prompt(draft.get("title", ""), draft.get("coreMessage", ""), persona)
        # 入力を破壊しない（新しい dict を返す）。
        results.append(
            {
                **book,
                "coverVariant": cover_variant_for(i),
                "coverPrompt": prompt,
                "coverUrl": None,
            }
        )
    return results
