"""STEP3 キャスティング（C1.4）の決定的オフラインテスト。

承認企画(PlanProposal) → 架空著者5人（voiceStyle×format の2軸で分散）の決定的生成を
実LLMなしで検証する。正本: docs/design/agent-io-contract.md §5-3a / packages/prompts/step3_casting_editor.md。
"""

from __future__ import annotations

from publishr_schema import GeneratedPersonaSet, PlanProposal

from publishr_agents.casting import cast_personas
from publishr_agents.casting.deterministic import cast_personas_deterministic


def _plan() -> PlanProposal:
    return PlanProposal.model_validate(
        {
            "proposalId": "plan_misa_01",
            "themeKind": "honmei",
            "round": 2,
            "tentativeTitle": "年上の実力者にどう任せるか",
            "readerSituation": "新任2ヶ月・年上部下の任せ方に悩む",
            "whyNowForYou": "6/5役員報告を控える今",
            "coreMessage": "任せ方を型として持つ",
            "diffFromMarket": "新任×年上実力者×消費財ブランド職に限定",
            "keyInsights": ["権限の段階設計"],
            "agendaOutline": ["現状", "型", "適用"],
            "recommendedAuthorTypes": ["実務家タイプ", "対話・コーチング型"],
        }
    )


def test_returns_five_personas():
    result = cast_personas_deterministic(_plan())
    assert isinstance(result, GeneratedPersonaSet)
    assert len(result.personas) == 5
    assert result.reason  # 散らし方の説明


def test_two_axes_are_distinct():
    """voiceStyle×format の組み合わせが5人で重複しない（多様性＝サブの意味）。"""
    result = cast_personas_deterministic(_plan())
    combos = {(p.voice_style, p.format) for p in result.personas}
    assert len(combos) == 5, "2軸の組み合わせが5通りに分散"


def test_personas_have_required_fields_and_ephemeral():
    result = cast_personas_deterministic(_plan())
    for p in result.personas:
        assert p.persona_id and p.name
        assert p.voice_style and p.format
        assert p.persona  # 薄くない設定
        assert p.ephemeral is True
        assert p.past_books == []


def test_plan_id_and_theme_kind_propagated():
    result = cast_personas_deterministic(_plan())
    assert result.plan_id == "plan_misa_01"
    assert result.theme_kind == "honmei"


def test_no_favorite_means_all_generated():
    result = cast_personas_deterministic(_plan(), favorite_authors=[])
    assert all(p.from_favorite is False for p in result.personas)


def test_favorite_author_injected_as_one_slot():
    """favoriteAuthors があれば1枠を fromFavorite=true で採用（15%相当・決定的に1枠）。"""
    favs = [{"personaId": "fav_1", "name": "推し 作家", "voiceStyle": "思想的", "format": "エッセイ形式"}]
    result = cast_personas_deterministic(_plan(), favorite_authors=favs)
    fav_slots = [p for p in result.personas if p.from_favorite]
    assert len(fav_slots) == 1
    assert fav_slots[0].name == "推し 作家"
    assert len(result.personas) == 5  # 員数は5を厳守


def test_deterministic_is_stable():
    a = cast_personas_deterministic(_plan())
    b = cast_personas_deterministic(_plan())
    assert a.model_dump(by_alias=True) == b.model_dump(by_alias=True)


# ── dispatcher ────────────────────────────────────────────
def test_cast_personas_defaults_to_mock(monkeypatch):
    monkeypatch.delenv("PUBLISHR_LLM", raising=False)
    result = cast_personas(_plan())
    assert len(result.personas) == 5


def test_cast_personas_unknown_mode_raises(monkeypatch):
    monkeypatch.setenv("PUBLISHR_LLM", "bogus")
    try:
        cast_personas(_plan())
    except ValueError as e:
        assert "bogus" in str(e)
    else:
        raise AssertionError("unknown PUBLISHR_LLM で ValueError を期待")
