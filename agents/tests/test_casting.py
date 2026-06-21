"""STEP3 キャスティング（C1.4）の決定的オフラインテスト。

承認企画(PlanProposal) → 架空著者5人（voiceStyle×format の2軸で分散）の決定的生成を
実LLMなしで検証する。正本: docs/design/agent-io-contract.md §5-3a / packages/prompts/step3_casting_editor.md。
"""

from __future__ import annotations

from publishr_schema import GeneratedPersona, GeneratedPersonaSet, PlanProposal

from publishr_agents.casting import cast_personas, reconcile_favorite_ids
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


# ── お気に入りID整合（reconcile_favorite_ids・cross-run 継続のかなめ） ──────────
def _vertex_like_set(fav_slot: dict) -> GeneratedPersonaSet:
    """vertex の LLM 出力を模す: from_favorite を立てつつ personaId は新規生成(p1..)。"""
    base = [
        GeneratedPersona(
            persona_id=f"p{i}", name=f"生成{i}", voice_style="v", format="f",
            persona="x", expertise=["e"], from_favorite=False, ephemeral=True,
        )
        for i in range(1, 6)
    ]
    base[0] = GeneratedPersona(
        persona_id=fav_slot["persona_id"], name=fav_slot["name"], voice_style="v",
        format="f", persona="x", expertise=["e"], from_favorite=True, ephemeral=True,
    )
    return GeneratedPersonaSet(plan_id="pl", theme_kind="honmei", personas=base, reason="r")


def test_reconcile_stamps_registered_favorite_id_over_llm_generated():
    """登録IDが run-unique でも、from_favorite 枠の personaId をそれへ固定する（★継続のかなめ）。"""
    # LLM は fromFavorite=true・personaId="p1"（新規）で返す ＝ 登録IDが失われる失敗モード。
    pset = _vertex_like_set({"persona_id": "p1", "name": "推し 作家"})
    favs = [{"personaId": "arr20260617_p3", "name": "推し 作家", "savedAt": "t"}]
    out = reconcile_favorite_ids(pset, favs)
    fav = next(p for p in out.personas if p.from_favorite)
    assert fav.persona_id == "arr20260617_p3"  # front の favorites.has(id) と一致する
    assert fav.name == "推し 作家"
    assert len(out.personas) == 5


def test_reconcile_matches_by_order_when_name_differs():
    """LLM が名前を変えても、登録順で personaId を割り当てて拾う。"""
    pset = _vertex_like_set({"persona_id": "p1", "name": "別名にされた"})
    favs = [{"personaId": "favX", "name": "本来の名"}]
    out = reconcile_favorite_ids(pset, favs)
    fav = next(p for p in out.personas if p.from_favorite)
    assert fav.persona_id == "favX"
    assert fav.name == "本来の名"


def test_reconcile_demotes_unbacked_favorite_to_normal():
    """お気に入りが無いのに from_favorite が立った枠は通常枠へ降格（安定IDを誤付与しない）。"""
    pset = _vertex_like_set({"persona_id": "p1", "name": "幻のお気に入り"})
    out = reconcile_favorite_ids(pset, [])
    assert all(p.from_favorite is False for p in out.personas)


def test_reconcile_is_noop_without_favorite_slots():
    pset = cast_personas_deterministic(_plan(), favorite_authors=[])
    out = reconcile_favorite_ids(pset, [])
    assert out.model_dump(by_alias=True) == pset.model_dump(by_alias=True)


def test_reconcile_does_not_mutate_input():
    pset = _vertex_like_set({"persona_id": "p1", "name": "推し"})
    favs = [{"personaId": "favY", "name": "推し"}]
    reconcile_favorite_ids(pset, favs)
    assert pset.personas[0].persona_id == "p1"  # 入力は不変


def test_cast_personas_vertex_path_fixes_favorite_id(monkeypatch):
    """dispatcher 経由でも（vertex を模した結果に）reconcile が掛かりIDが固定される。"""
    fake = _vertex_like_set({"persona_id": "p1", "name": "推し 作家"})
    monkeypatch.setenv("PUBLISHR_LLM", "vertex")
    monkeypatch.setattr(
        "publishr_agents.casting.vertex_agent.cast_personas_vertex",
        lambda *a, **k: fake,
    )
    favs = [{"personaId": "arr20260617_p3", "name": "推し 作家"}]
    out = cast_personas(_plan(), favorite_authors=favs)
    fav = next(p for p in out.personas if p.from_favorite)
    assert fav.persona_id == "arr20260617_p3"
