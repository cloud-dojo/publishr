"""STEP3 キャスティングの決定的オフライン実装（PUBLISHR_LLM=mock・既定）。

承認企画から架空著者5人を voiceStyle×format の2軸で分散生成する（canned）。本格的な
人格生成は実Vertex（vertex_agent）が担う。
"""

from __future__ import annotations

from typing import Any, Optional

from publishr_schema import (
    AuthorCasting,
    GeneratedPersona,
    GeneratedPersonaSet,
    PlanProposal,
    ReaderProfile3Layer,
)

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


# ── STEP3 author_casting（v3・4テーマ）: 1企画＝3候補生成→1選抜（AuthorCasting）──
# 出版社モデルの新STEP3。GeneratedPersonaSet（5著者・選択肢）とは別形＝担当が3案出して最適1人に絞る。
def _author_candidate(plan: PlanProposal, axis: tuple[str, str, str, str], n: int, expertise: list[str], theme: str) -> GeneratedPersona:
    voice, fmt, name, seed = axis
    return GeneratedPersona(
        # plan スコープのIDで4冊間の衝突を防ぐ（book id = arr_<personaId>）。
        persona_id=f"cast_{plan.proposal_id or 'plan'}_{n}",
        name=name,
        voice_style=voice,
        format=fmt,
        persona=f"{seed} テーマ「{theme}」を {voice} の語り口で {fmt} として書く。",
        expertise=expertise,
        past_books=[],
        from_favorite=False,
        ephemeral=True,
    )


def cast_author_deterministic(
    plan: PlanProposal,
    *,
    reader_profile: Optional[ReaderProfile3Layer] = None,
    favorite_authors: Optional[list[dict[str, Any]]] = None,
) -> AuthorCasting:
    """承認1企画に対し架空著者3候補を生成し、最適1人を chosen に選ぶ（決定的）。

    候補3軸は plan ごとに開始オフセットをずらし、4冊で主著者が散るようにする（編集長の多様性設計を補強）。
    chosen は候補先頭（offset 先頭＝企画の bookRole に寄せた軸）。実選抜の機微は実Vertexが担う。
    """
    favorite_authors = favorite_authors or []
    theme = plan.tentative_title or plan.core_message or plan.theme or "本テーマ"
    expertise = (list(plan.recommended_author_types) or ["実務"])[:2]
    offset = sum(ord(c) for c in (plan.proposal_id or "plan")) % len(_AXES)
    candidates = [
        _author_candidate(plan, _AXES[(offset + k) % len(_AXES)], k + 1, expertise, theme)
        for k in range(3)
    ]
    if favorite_authors:
        fav = favorite_authors[0]
        candidates[0] = GeneratedPersona(
            # 登録お気に入りIDを保持＝persist 後も front の favorites.has(id) と一致（★継続）。
            persona_id=fav.get("personaId") or f"cast_{plan.proposal_id or 'plan'}_fav",
            name=fav.get("name", "お気に入り著者"),
            voice_style=candidates[0].voice_style,
            format=candidates[0].format,
            persona=f"読者のお気に入り著者として再登板。テーマ「{theme}」を持ち味の語りで書く。",
            expertise=expertise,
            past_books=[],
            from_favorite=True,
            ephemeral=True,
        )
    chosen = candidates[0]
    style = ""
    if reader_profile and reader_profile.reading_behavior:
        style = reader_profile.reading_behavior.style_preference or ""
    reason = (
        f"企画の bookRole={plan.book_role or '—'}・emotionalTone={plan.emotional_tone or '—'} に最も合うのは"
        f"{chosen.name}（{chosen.voice_style}×{chosen.format}）。他2候補は寄せ方が異なり、この企画の核から距離がある。"
    )
    if style:
        reason += f"読者の stylePreference『{style}』とも整合。"
    return AuthorCasting(
        plan_id=plan.proposal_id,
        candidates=candidates,
        chosen=chosen,
        selection_reason=reason,
    )
