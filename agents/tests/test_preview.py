"""STEP4 プレビュー編集（C1.5）の決定的オフラインテスト。

承認企画＋5著者 → 各著者が BookDraft(7項目) → 編集長3観点採点 → 1R改稿 → 棚5冊draft。
正本: docs/design/agent-io-contract.md §5-2 / packages/prompts/step4_*.md。
"""

from __future__ import annotations

from publishr_schema import BookDraft, EditorVerdict, PlanProposal

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
