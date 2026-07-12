"""表紙の決定的オフライン装丁（PUBLISHR_LLM=mock・既定）。

現行メインパイプラインの表紙処理は `assign_cover_variants`＝coverVariant（globals.css の
cover--b1..b40）を決定的に付与するだけ（coverUrl=None・オフライン・ゼロコスト・画像生成なし）。

色は 40 色（寒色20 + 暖色20）でシンプルに決定的割当（パターンなし）。

⚠️ 画像生成（Imagen 用 coverPrompt 生成・実画像）は今回スコープ外で park（将来実装予定）。
   下部 PARKED セクション（_VOICE_VISUAL / _cover_prompt / design_covers_deterministic）は
   将来の装丁（画像生成）用に温存し、現行メインパイプラインからは呼ばれない（cover/vertex_agent.py・
   imagen.py と対で再結線する）。
"""

from __future__ import annotations

from typing import Any, Optional

from publishr_schema import GeneratedPersona

# 40色パレット（寒色20 + 暖色20）
_COOL_COLORS = [
    "#2E4053", "#3D5A80", "#4B5A7C", "#4A7C7E", "#4D3E7B",  # row 1
    "#3B6A8F", "#42677C", "#3F5F70", "#456B7A", "#384D6B",  # row 2
    "#5B7F8C", "#4A6A7A", "#516D7F", "#4C7B8D", "#5A6B7E",  # row 3
    "#3A5C7F", "#445A72", "#506F8A", "#527B8C", "#3D5A75",  # row 4
]
_WARM_COLORS = [
    "#9E8BA5", "#B8896E", "#C9845A", "#D97F4A", "#E5704A",  # row 1 (purple → warm)
    "#A67B7D", "#BA8560", "#C89050", "#D99847", "#E59052",  # row 2
    "#9B7A82", "#B87564", "#C68552", "#D9934A", "#E5874F",  # row 3
    "#A7855F", "#BA8B6E", "#C89565", "#D9A35C", "#E5A855",  # row 4
]
_PALETTE = _COOL_COLORS + _WARM_COLORS


def cover_variant_for(index: int) -> str:
    """globals.css の cover--b1..b40 に対応する決定的 variant 割当。色40（パターンなし）。"""
    return f"b{(index % 40) + 1}"


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
