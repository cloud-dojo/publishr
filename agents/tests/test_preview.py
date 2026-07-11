"""STEP4 プレビュー編集（C1.5）の決定的オフラインテスト。

承認企画＋5著者 → 各著者が BookDraft(7項目) → 編集長3観点採点 → 1R改稿 → 棚5冊draft。
正本: packages/prompts/step4_*.md。
"""

from __future__ import annotations

from publishr_schema import BookDraft, EditorVerdict, PlanProposal, ReaderProfile3Layer

from publishr_agents.casting import cast_personas
from publishr_agents.preview import run_preview
from publishr_agents.preview.deterministic import run_preview_deterministic


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
            "recommendedAuthorTypes": ["実務家タイプ"],
        }
    )


def _personas():
    return cast_personas(_plan()).personas  # 決定的5人


def test_returns_one_draft_per_author():
    results = run_preview_deterministic(_plan(), _personas())
    assert len(results) == 5


def test_each_book_draft_has_seven_fields():
    results = run_preview_deterministic(_plan(), _personas())
    for r in results:
        d = BookDraft.model_validate(r["bookDraft"])
        assert d.title
        assert d.subtitle
        assert d.delivery_reason   # ③ 入荷理由
        assert d.problem_to_solve  # ④
        assert d.core_message      # ⑤
        assert d.agenda            # ⑥ 章
        assert d.preface_sample    # ⑦ はじめに


def test_agenda_has_intro_numbered_chapters_and_outro():
    results = run_preview_deterministic(_plan(), _personas())
    for r in results:
        d = BookDraft.model_validate(r["bookDraft"])
        labels = [item.chapter.split()[0] for item in d.agenda]
        assert labels == ["はじめに", "1章", "2章", "3章", "おわりに"]


def test_verdict_validates_and_persona_linked():
    results = run_preview_deterministic(_plan(), _personas())
    persona_ids = {p.persona_id for p in _personas()}
    for r in results:
        EditorVerdict.model_validate(r["verdict"])
        assert r["personaId"] in persona_ids


def test_one_round_revise_is_demonstrated():
    """編集長の1R差し戻し（round1 revise→round2 approve）が少なくとも1冊で起きる＝編集の証跡。"""
    results = run_preview_deterministic(_plan(), _personas())
    revised = [r for r in results if r["editRounds"] == 2]
    assert revised, "1R改稿が1冊以上"
    for r in revised:
        assert r["verdict"]["decision"] == "approve"  # 改稿後は採用
    # 改稿が起きなかった本は1Rで採用
    for r in results:
        assert r["editRounds"] in (1, 2)


def test_persona_voice_reflected_in_draft():
    """著者の voiceStyle/format が draft に反映（ペルソナ前面化＝②観点）。"""
    results = run_preview_deterministic(_plan(), _personas())
    personas = {p.persona_id: p for p in _personas()}
    for r in results:
        p = personas[r["personaId"]]
        text = r["bookDraft"]["coreMessage"] + r["bookDraft"]["prefaceSample"]
        assert p.voice_style in text or p.format in text or p.name in text


def test_deterministic_is_stable():
    a = run_preview_deterministic(_plan(), _personas())
    b = run_preview_deterministic(_plan(), _personas())
    assert a == b


def test_limit_caps_book_count():
    results = run_preview_deterministic(_plan(), _personas(), limit=2)
    assert len(results) == 2


# ── serendipity 棚書き文法（本文の抽象化ライン）────────────────
def _profile_with_challenge(challenge: str) -> ReaderProfile3Layer:
    return ReaderProfile3Layer.model_validate(
        {
            "base": {
                "industry": "食品・飲料メーカー",
                "jobType": "マーケティング・ブランド",
                "position": "課長（新任）",
                "orgScale": "部下7名",
                "readingGenres": ["実践書"],
            },
            "currentWork": {
                "currentSituation": "新任2ヶ月",
                "activeWorkThemes": ["新任マネジメント"],
                "challenges": [challenge],
                "upcomingKeyEvents": [],
                "evidence": [],
            },
            "readingBehavior": {"serendipityTolerance": "mid", "stylePreference": "実務的"},
        }
    )


def _serendipity_plan() -> PlanProposal:
    return PlanProposal.model_validate(
        {
            "proposalId": "plan_misa_seren_01",
            "themeKind": "serendipity",
            "round": 2,
            "tentativeTitle": "貨幣が変えた人類の信用史",
            "readerSituation": "教養への関心の萌芽",
            "whyNowForYou": "関心の隣へ",
            "coreMessage": "価値の約束はどう編まれてきたか",
            "diffFromMarket": "実務書ではなく文化史の視点",
            "keyInsights": ["交換から信用へ"],
            "agendaOutline": ["物々交換", "貨幣の発明", "信用の制度化"],
            "recommendedAuthorTypes": ["教養エッセイタイプ"],
        }
    )


def test_serendipity_draft_does_not_leak_surface_challenge():
    """セレンディピティ本は棚書き文法＝読者の表層業務課題を直書きしない（本文の抽象化ライン）。

    同じ profile を honmei に渡すと入荷理由で課題を直撃する、の対比で「空振りでない」ことを担保する。
    """
    surface = "売上前年割れの立て直し"
    profile = _profile_with_challenge(surface)

    seren = run_preview_deterministic(_serendipity_plan(), _personas(), reader_profile=profile)
    for r in seren:
        d = r["bookDraft"]
        blob = d["deliveryReason"] + d["problemToSolve"] + d["prefaceSample"]
        assert surface not in blob, f"serendipityで表層課題が漏れた: {blob}"

    # 対比: 同じ課題を honmei に渡すと入荷理由で直撃する（honmei は課題直撃でよい）
    honmei = run_preview_deterministic(_plan(), _personas(), reader_profile=profile)
    assert any(surface in r["bookDraft"]["deliveryReason"] for r in honmei), "honmeiは課題直撃のはず"


# ── dispatcher ────────────────────────────────────────────
def test_run_preview_defaults_to_mock(monkeypatch):
    monkeypatch.delenv("PUBLISHR_LLM", raising=False)
    results = run_preview(_plan(), _personas())
    assert len(results) == 5


def test_run_preview_unknown_mode_raises(monkeypatch):
    monkeypatch.setenv("PUBLISHR_LLM", "bogus")
    try:
        run_preview(_plan(), _personas())
    except ValueError as e:
        assert "bogus" in str(e)
    else:
        raise AssertionError("unknown PUBLISHR_LLM で ValueError を期待")
