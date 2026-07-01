"""モードB「手動1冊」本文編集ループ（編集長⇄著者1人・弱章のみ改稿）の決定的テスト。

mock 既定＝決定的・課金ゼロ。必然性の証跡（編集長が著者を採点して差し戻す＝BodyVerdict.weakChapters）
と、弱い章のみ改稿（全文再生成しない＝コスト抑制）を押さえる。
"""

from __future__ import annotations

import os

import pytest
from publishr_schema import load_books, load_personas

from publishr_agents.mode_b import write_body_loop


def _book():
    return next(b for b in load_books() if b.id == "b_makasekata")


def _persona(pid: str):
    return next((p for p in load_personas() if p.id == pid), None)


def test_body_loop_produces_chapters_and_revise_trace():
    book = _book()
    persona = _persona(book.author_persona_id)
    result = write_body_loop(book, persona=persona, rounds=1, llm="mock")

    # はじめに＋最大5番号章＋おわりに（手動1冊スライス）。各章に title/text。
    assert 3 <= len(result.chapters) <= 7
    for ch in result.chapters:
        assert ch["title"] and ch["text"]

    # 1R改稿が起きた＝round2 到達。
    assert result.edit_rounds == 2
    # round1 は差し戻し（弱い章あり）。
    assert result.verdicts[0]["decision"] == "revise"
    assert result.verdicts[0]["weakChapters"]
    # 最終は承認・弱章なし。
    assert result.body_verdict["decision"] == "approve"
    assert result.body_verdict["weakChapters"] == []
    # 改稿対象＝round1 の弱章のみ。
    assert result.revised_chapters == result.verdicts[0]["weakChapters"]
    # body は章見出しを含む markdown（はじめに／おわりには見出しのみで章タイトルを含まない）。
    assert result.chapters[1]["title"] in result.body
    assert "## はじめに" in result.body
    assert "## おわりに" in result.body


def test_body_loop_revises_only_weak_chapter():
    """弱い章だけ改稿し、他章は不変（全文再生成しない＝コスト抑制）。"""
    book = _book()
    persona = _persona(book.author_persona_id)
    base = write_body_loop(book, persona=persona, rounds=0, llm="mock")  # 改稿なし初稿
    revised = write_body_loop(book, persona=persona, rounds=1, llm="mock")
    weak = set(revised.revised_chapters)
    assert weak  # 改稿が1章は起きる

    for i, (b, r) in enumerate(zip(base.chapters, revised.chapters), start=1):
        if i in weak:
            assert b["text"] != r["text"]  # 弱章は変わる
        else:
            assert b["text"] == r["text"]  # 他章は不変


def test_body_loop_unknown_llm_raises():
    book = _book()
    with pytest.raises(ValueError):
        write_body_loop(book, persona=None, llm="bogus")


def test_modeb_vertex_agents_build_offline():
    """vertex_agent の著者/編集長エージェントが offline で構築でき、modeB プロンプトが解決する
    （wiring 検証＝import/registry/model_for。API は呼ばない）。"""
    from publishr_agents.mode_b import vertex_agent

    author = vertex_agent.build_author_agent()
    editor = vertex_agent.build_editor_agent()
    assert author.name == "modeb_author"
    assert editor.name == "modeb_editor"


@pytest.mark.vertex
@pytest.mark.skipif(
    os.environ.get("PUBLISHR_RUN_VERTEX") != "1",
    reason="set PUBLISHR_RUN_VERTEX=1 (＋GCP) to run live mode-B body loop",
)
def test_modeb_vertex_live():
    book = _book()
    persona = _persona(book.author_persona_id)
    result = write_body_loop(book, persona=persona, rounds=1, llm="vertex")
    assert 1 <= len(result.chapters) <= 5
    assert result.body
    assert result.body_verdict


def test_resolve_volume_from_profile_derives_per_chapter(monkeypatch):
    """本全体目標(prod=12,000字)から各章=本全体÷採用章数 を導出し、{{body_volume}} 文字列を返す（I-35）。"""
    from publishr_agents.mode_b import vertex_agent

    monkeypatch.delenv("PUBLISHR_BODY_CHARS_PER_CHAPTER", raising=False)
    monkeypatch.setenv("PUBLISHR_RUN_PROFILE", "prod")
    monkeypatch.delenv("PUBLISHR_BODY_CHAR_TARGET", raising=False)

    body_volume, per_chapter_hint = vertex_agent._resolve_volume(4)
    assert body_volume == "12,000字"          # system プロンプト {{body_volume}} を生かす
    assert "3,000字程度" in per_chapter_hint    # 12,000 ÷ 4章


def test_resolve_volume_per_chapter_env_takes_precedence(monkeypatch):
    """章単位の明示指定(CLI run_full_book)が最優先＝本全体は 章数×章単位 で逆算（I-35）。"""
    from publishr_agents.mode_b import vertex_agent

    monkeypatch.setenv("PUBLISHR_BODY_CHARS_PER_CHAPTER", "2000")
    body_volume, per_chapter_hint = vertex_agent._resolve_volume(3)
    assert body_volume == "6,000字"           # 2,000 × 3章
    assert "2,000字程度" in per_chapter_hint


def test_resolve_volume_zero_target_yields_no_hint(monkeypatch):
    """目標0/未満なら制御なし＝プロンプト既定(1万〜2万字)に委ねる（空文字を注入し {{body_volume}} は無害）。"""
    from publishr_agents.mode_b import vertex_agent

    monkeypatch.delenv("PUBLISHR_BODY_CHARS_PER_CHAPTER", raising=False)
    monkeypatch.setenv("PUBLISHR_BODY_CHAR_TARGET", "0")
    body_volume, per_chapter_hint = vertex_agent._resolve_volume(5)
    assert body_volume == ""
    assert per_chapter_hint == ""


def test_extract_raw_terms_finds_company_date_person():
    """delivery_reason から会社名(単一英字+社)・日付・氏名敬称のみを狭く抽出する（7/1レビュー・
    p1「A社」流出の再発防止）。「他社」「弊社」等の一般語は拾わない。"""
    from publishr_agents.mode_b.vertex_agent import _extract_raw_terms

    text = (
        "来週6月8日のエンジニアリング全体会議、そして10日の取締役会報告をカレンダーで拝見しました。"
        "重要顧客A社の更新提案に向けて、佐藤さんとも相談のうえ、他社事例も参考にしつつ進めます。"
    )
    terms = _extract_raw_terms(text)
    assert "A社" in terms
    assert "6月8日" in terms
    assert "佐藤さん" in terms
    assert "他社" not in terms  # 一般語（自社/弊社/他社等）は誤検出しない


def test_extract_raw_terms_empty_when_no_text():
    from publishr_agents.mode_b.vertex_agent import _extract_raw_terms

    assert _extract_raw_terms(None) == []
    assert _extract_raw_terms("") == []


def test_chapters_containing_finds_matching_index():
    from publishr_agents.mode_b.vertex_agent import _chapters_containing

    chapters = [
        {"no": "はじめに", "title": "はじめに", "text": "一般的な導入文。"},
        {"no": "1章", "title": "第1章", "text": "健全なA社は…という説明。"},
        {"no": "おわりに", "title": "おわりに", "text": "まとめ。"},
    ]
    assert _chapters_containing(chapters, ["A社"]) == [2]
    assert _chapters_containing(chapters, []) == []
    assert _chapters_containing(chapters, ["存在しない語"]) == []


def test_mechanical_override_forces_revise_when_raw_term_survives():
    """judge が approve でも、読者プロファイル由来の固有名詞が本文に残っていれば revise へ強制する
    （p1: 編集長が一度「A社」漏れを指摘したのに次ラウンドで見逃して承認した実例の再発防止）。"""
    from publishr_agents.mode_b.vertex_agent import _mechanical_override
    from publishr_schema.agent_io import BodyVerdict

    chapters = [{"no": "1章", "title": "第1章", "text": "健全なA社は…という説明。"}]
    verdict = BodyVerdict(score=90, decision="approve", weak_chapters=[], editor_feedback=None)

    overridden = _mechanical_override(verdict, chapters, ["A社"])
    assert overridden.decision == "revise"
    assert overridden.weak_chapters == [1]
    assert "A社" in overridden.editor_feedback


def test_mechanical_override_noop_when_no_raw_terms_present():
    from publishr_agents.mode_b.vertex_agent import _mechanical_override
    from publishr_schema.agent_io import BodyVerdict

    chapters = [{"no": "1章", "title": "第1章", "text": "型へ一般化された説明。"}]
    verdict = BodyVerdict(score=90, decision="approve", weak_chapters=[], editor_feedback=None)

    unchanged = _mechanical_override(verdict, chapters, ["A社"])
    assert unchanged is verdict  # 変更なし・同一オブジェクトを返す


def test_body_loop_up_to_three_rounds():
    """最高3R: 初稿→2回改稿で3ラウンド到達し承認（編集長⇄著者の差し戻しが複数回）。"""
    book = _book()
    persona = _persona(book.author_persona_id)
    result = write_body_loop(book, persona=persona, rounds=3, llm="mock")
    assert result.edit_rounds == 3
    assert len(result.verdicts) == 3
    assert result.verdicts[0]["decision"] == "revise"
    assert result.verdicts[1]["decision"] == "revise"
    assert result.body_verdict["decision"] == "approve"
    assert result.revised_chapters
