"""STEP5 装丁（C1.6）の決定的オフラインテスト。

プレビュー5冊に装丁（coverVariant=CSS / coverPrompt=Imagen用英語 / coverUrl）を付与。
dev（ENABLE_IMAGEN off）は CSS variant のみ・coverUrl=None。正本: agent-io-contract.md §6 / step5_cover.md。
"""

from __future__ import annotations

from publishr_schema import PlanProposal

from publishr_agents.casting import cast_personas
from publishr_agents.cover import design_covers
from publishr_agents.cover.deterministic import cover_variant_for, design_covers_deterministic
from publishr_agents.preview import run_preview


def _plan() -> PlanProposal:
    return PlanProposal.model_validate(
        {
            "proposalId": "plan_misa_01",
            "themeKind": "honmei",
            "round": 2,
            "tentativeTitle": "年上の実力者にどう任せるか",
            "readerSituation": "新任2ヶ月",
            "whyNowForYou": "6/5役員報告を控える今",
            "coreMessage": "任せ方を型として持つ",
            "diffFromMarket": "新任×年上実力者に限定",
        }
    )


def _books_and_personas():
    personas = cast_personas(_plan()).personas
    books = run_preview(_plan(), personas)
    return books, personas


def test_assigns_cover_to_every_book():
    books, personas = _books_and_personas()
    results = design_covers_deterministic(books, personas)
    assert len(results) == len(books)
    for r in results:
        assert r["coverVariant"]
        assert r["coverPrompt"]
        assert r["coverUrl"] is None  # ENABLE_IMAGEN off＝画像生成しない


def test_cover_variant_is_supported_css():
    """coverVariant は globals.css の cover--b1..b10 に対応する値。"""
    for i in range(12):
        v = cover_variant_for(i)
        assert v in {f"b{n}" for n in range(1, 11)}


def test_cover_prompt_excludes_text_burn_in():
    """coverPrompt は『文字を焼かない』方針を明示（タイトルはUIが重畳）。"""
    books, personas = _books_and_personas()
    results = design_covers_deterministic(books, personas)
    for r in results:
        assert "no text" in r["coverPrompt"].lower()


def test_persona_voice_reflected_in_prompt():
    books, personas = _books_and_personas()
    pmap = {p.persona_id: p for p in personas}
    results = design_covers_deterministic(books, personas)
    for r in results:
        p = pmap[r["personaId"]]
        assert p.voice_style in r["coverPrompt"] or p.format in r["coverPrompt"]


def test_deterministic_is_stable():
    books, personas = _books_and_personas()
    a = design_covers_deterministic(books, personas)
    b = design_covers_deterministic(books, personas)
    assert a == b


def test_does_not_mutate_input_books():
    books, personas = _books_and_personas()
    before = books[0].copy()
    design_covers_deterministic(books, personas)
    assert books[0] == before  # 入力を破壊しない（immutability）


# ── dispatcher ────────────────────────────────────────────
def test_design_covers_defaults_to_mock(monkeypatch):
    monkeypatch.delenv("PUBLISHR_LLM", raising=False)
    monkeypatch.delenv("ENABLE_IMAGEN", raising=False)
    books, personas = _books_and_personas()
    results = design_covers(books, personas)
    assert all(r["coverUrl"] is None for r in results)


def test_design_covers_unknown_mode_raises(monkeypatch):
    books, personas = _books_and_personas()  # 先に mock で組む
    monkeypatch.setenv("PUBLISHR_LLM", "bogus")
    try:
        design_covers(books, personas)
    except ValueError as e:
        assert "bogus" in str(e)
    else:
        raise AssertionError("unknown PUBLISHR_LLM で ValueError を期待")
