"""お気に入り「配本ごと約25%で1冊だけ起用」ゲート（choose_favorite_feature）と
AuthorCasting のID固定（reconcile_author_favorite_id）の決定的テスト。

確率はオーケストレーション層（mode_a）が握る純関数。実LLMなし・全mock・決定的。
"""

from __future__ import annotations

from publishr_schema import AuthorCasting, GeneratedPersona

from publishr_agents.casting import cast_author, reconcile_author_favorite_id
from publishr_agents.casting.favorites import (
    FAVORITE_FEATURE_PCT_DEFAULT,
    choose_favorite_feature,
)

_PLANS = ["plan_det_A", "plan_det_B", "plan_det_C", "plan_det_D"]
_FAVS = [{"personaId": "fav_1", "name": "推し 作家", "voiceStyle": "思想的・哲学的", "format": "エッセイ形式"}]


# ── ゲート（choose_favorite_feature） ─────────────────────────────
def test_default_pct_is_25():
    assert FAVORITE_FEATURE_PCT_DEFAULT == 25


def test_empty_or_no_favorites_never_features():
    assert choose_favorite_feature(_PLANS, [], seed="x") is None
    assert choose_favorite_feature(_PLANS, None, seed="x") is None
    assert choose_favorite_feature([], _FAVS, seed="x") is None  # plan が無ければ起用先なし


def test_pct_zero_never_and_hundred_always():
    assert choose_favorite_feature(_PLANS, _FAVS, seed="x", pct=0) is None
    out = choose_favorite_feature(_PLANS, _FAVS, seed="x", pct=100)
    assert out is not None
    idx, fav = out
    assert idx in range(len(_PLANS))  # 起用先は4枠のどれか1つ
    assert fav["personaId"] == "fav_1"


def test_deterministic_same_seed_same_result():
    a = choose_favorite_feature(_PLANS, _FAVS, seed="run-123")
    b = choose_favorite_feature(_PLANS, _FAVS, seed="run-123")
    assert a == b


def test_seed_varies_outcome_across_deliveries():
    """seed（配本トークン）が変われば抽選し直す＝出る配本・出ない配本が混ざる。"""
    outcomes = {choose_favorite_feature(_PLANS, _FAVS, seed=f"s-{i}") is not None for i in range(50)}
    assert outcomes == {True, False}  # 出る回と出ない回の両方が存在


def test_rate_is_about_25pct_over_many_seeds():
    n = 4000
    hits = sum(1 for i in range(n) if choose_favorite_feature(_PLANS, _FAVS, seed=f"seed-{i}") is not None)
    rate = hits / n
    assert 0.22 < rate < 0.28, f"~25% を期待: {rate:.3f}"


def test_single_book_only_when_featured():
    """当たっても返すのは (idx, fav) ＝1枠だけ（4冊全部お気に入りにならない）。"""
    out = choose_favorite_feature(_PLANS, _FAVS, seed="seed-7", pct=100)
    assert out is not None and isinstance(out[0], int)


def test_picks_one_of_multiple_favorites_deterministically():
    favs = [{"personaId": "fav_1", "name": "A"}, {"personaId": "fav_2", "name": "B"}, {"personaId": "fav_3", "name": "C"}]
    out = choose_favorite_feature(_PLANS, favs, seed="s", pct=100)
    assert out is not None and out[1]["personaId"] in {"fav_1", "fav_2", "fav_3"}
    again = choose_favorite_feature(_PLANS, favs, seed="s", pct=100)
    assert out[1]["personaId"] == again[1]["personaId"]  # 「誰か」も決定的


# ── AuthorCasting のID固定（reconcile_author_favorite_id） ───────────
def _casting_with_favorite(llm_persona_id: str, name: str) -> AuthorCasting:
    """vertex 風の出力: from_favorite を立てつつ personaId は LLM 生成（c1 等）。"""
    favc = GeneratedPersona(
        persona_id=llm_persona_id, name=name, voice_style="v", format="f",
        persona="x", expertise=["e"], from_favorite=True, ephemeral=True,
    )
    others = [
        GeneratedPersona(
            persona_id=f"c{i}", name=f"gen{i}", voice_style="v", format="f",
            persona="x", expertise=["e"], from_favorite=False, ephemeral=True,
        )
        for i in (2, 3)
    ]
    return AuthorCasting(plan_id="pl", candidates=[favc, *others], chosen=favc, selection_reason="r")


def test_reconcile_stamps_registered_id_on_chosen_and_candidate():
    casting = _casting_with_favorite("c1", "推し 作家")
    favs = [{"personaId": "arr20260617_p3", "name": "推し 作家"}]
    out = reconcile_author_favorite_id(casting, favs)
    fav_c = next(c for c in out.candidates if c.from_favorite)
    assert fav_c.persona_id == "arr20260617_p3"
    assert out.chosen is not None and out.chosen.persona_id == "arr20260617_p3"  # chosen も追従
    assert out.chosen.from_favorite


def test_reconcile_matches_by_order_when_name_differs():
    casting = _casting_with_favorite("c1", "別名にされた")
    out = reconcile_author_favorite_id(casting, [{"personaId": "favX", "name": "本来の名"}])
    fav_c = next(c for c in out.candidates if c.from_favorite)
    assert fav_c.persona_id == "favX" and fav_c.name == "本来の名"


def test_reconcile_demotes_unbacked_favorite():
    casting = _casting_with_favorite("c1", "幻のお気に入り")
    out = reconcile_author_favorite_id(casting, [])
    assert all(not c.from_favorite for c in out.candidates)
    assert out.chosen is not None and not out.chosen.from_favorite


def test_cast_author_vertex_path_fixes_favorite_id(monkeypatch):
    """dispatcher 経由（vertex 模擬）でも reconcile が掛かり chosen の personaId が固定される。"""
    fake = _casting_with_favorite("c1", "推し 作家")
    monkeypatch.setenv("PUBLISHR_LLM", "vertex")
    monkeypatch.setattr(
        "publishr_agents.casting.vertex_agent.cast_author_vertex",
        lambda *a, **k: fake,
    )
    from publishr_schema import PlanProposal

    plan = PlanProposal.model_validate({
        "proposalId": "pl", "themeKind": "honmei", "round": 1,
        "tentativeTitle": "t", "readerSituation": "s", "whyNowForYou": "w",
        "coreMessage": "c", "diffFromMarket": "d",
    })
    favs = [{"personaId": "arr20260617_p3", "name": "推し 作家"}]
    out = cast_author(plan, favorite_authors=favs)
    assert out.chosen is not None and out.chosen.persona_id == "arr20260617_p3"
