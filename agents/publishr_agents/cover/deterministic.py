"""STEP5 装丁の決定的オフライン実装（PUBLISHR_LLM=mock・ENABLE_IMAGEN off・既定）。

プレビュー結果に装丁を付与: coverVariant（globals.css の cover--b1..b10）＋ coverPrompt
（Imagen用英語・文字を焼かない）＋ coverUrl=None（dev は画像生成しない）。
本格的な方針生成は Flash（vertex_agent）、実画像は Imagen（imagen.py）。正本: agent-io-contract §6。
"""

from __future__ import annotations

from typing import Any, Optional

from publishr_schema import GeneratedPersona

# voiceStyle → ビジュアル方針（決定的）。
_VOICE_VISUAL: dict[str, str] = {
    "ロジカル・構造化": "geometric precision, generous negative space, calm off-white with deep navy and slate accents",
    "感覚的・情緒的": "soft watercolor texture, warm muted tones, a single evocative motif, gentle light",
    "学術的": "clean editorial grid, restrained palette, abstract diagram motif",
    "泥臭い・現場": "tactile paper texture, earthy tones, hand-drawn motif, honest and grounded",
    "思想的・哲学的": "quiet chiaroscuro, abstract shapes, deep contrast, contemplative",
}
_FALLBACK_VISUAL = "minimalist editorial business-book cover, restrained palette, one symbolic motif"


def cover_variant_for(index: int) -> str:
    """globals.css の cover--b1..b10 に対応する決定的 variant 割当。"""
    return f"b{(index % 10) + 1}"


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
