"""STEP3 キャスティングの決定的オフライン実装（PUBLISHR_LLM=mock・既定）。

承認企画から架空著者5人を voiceStyle×format の2軸で分散生成する（canned）。本格的な
人格生成は実Vertex（vertex_agent）が担う。正本: docs/design/agent-io-contract.md §5-3a。
"""

from __future__ import annotations

from typing import Any, Optional

from publishr_schema import GeneratedPersona, GeneratedPersonaSet, PlanProposal, ReaderProfile3Layer

# (voiceStyle, format, name, persona_seed) — 2軸を5通りに分散（同じ組合せを重ねない）。
_AXES: list[tuple[str, str, str, str]] = [
    ("ロジカル・構造化", "ストレートな自己啓発書", "神崎 玄一郎",
     "元・大手メーカーの事業部長。権限を表で設計する手法に行き着いた。口癖は『で、それは誰の意思決定？』。"),
    ("感覚的・情緒的", "小説・物語形式", "里見 ほたる",
     "元・地方百貨店フロア長から作家へ。一人称の語りで読者を主人公に重ねる。『正しさより、まず隣に立つ』。"),
    ("学術的", "対話・問答形式", "藤波 一誠",
     "組織論の研究者。問いを重ねて読者自身に答えを見つけさせる。"),
    ("泥臭い・現場", "エッセイ形式", "工藤 鉄平",
     "叩き上げの元工場長。任せて失敗した生々しい現場談を率直に綴る。"),
    ("思想的・哲学的", "問答形式", "白川 玄道",
     "東洋思想に学ぶリーダー論。問答で本質へ降りる。"),
]


def cast_personas_deterministic(
    plan: PlanProposal,
    *,
    reader_profile: Optional[ReaderProfile3Layer] = None,
    favorite_authors: Optional[list[dict[str, Any]]] = None,
) -> GeneratedPersonaSet:
    favorite_authors = favorite_authors or []
    theme = plan.tentative_title or plan.core_message or "本テーマ"
    expertise = (list(plan.recommended_author_types) or ["実務"])[:2]

    personas = [
        GeneratedPersona(
            persona_id=f"p{i + 1}",
            name=name,
            voice_style=voice,
            format=fmt,
            persona=f"{seed} テーマ「{theme}」を {voice} の語り口で {fmt} として書く。",
            expertise=expertise,
            past_books=[],
            from_favorite=False,
            ephemeral=True,
        )
        for i, (voice, fmt, name, seed) in enumerate(_AXES)
    ]

    # favoriteAuthors があれば1枠を採用（15%相当を決定的に1枠へ）。員数5は厳守。
    if favorite_authors:
        fav = favorite_authors[0]
        personas[0] = GeneratedPersona(
            persona_id=fav.get("personaId") or "fav_1",
            name=fav.get("name", "お気に入り著者"),
            # slot0 の2軸は保持（5通り分散を崩さない＝契約「同じ組合せを重ねない」）。
            voice_style=personas[0].voice_style,
            format=personas[0].format,
            persona=f"読者のお気に入り著者として再登板。テーマ「{theme}」を持ち味の語りで書く。",
            expertise=expertise,
            past_books=[],
            from_favorite=True,
            ephemeral=True,
        )

    reason = (
        "voiceStyle×format を5通りに散らした（ロジカル×自己啓発／感覚×小説／"
        "学術×対話／現場×エッセイ／思想×問答）。"
    )
    if favorite_authors:
        reason += "読者のお気に入り著者を1枠に採用。"
    if reader_profile and reader_profile.reading_behavior and reader_profile.reading_behavior.style_preference:
        reason += f"主軸は読者の stylePreference『{reader_profile.reading_behavior.style_preference}』に寄せた。"

    return GeneratedPersonaSet(
        plan_id=plan.proposal_id,
        theme_kind=plan.theme_kind,
        personas=personas,
        reason=reason,
    )
