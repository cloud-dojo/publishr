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

    # 3〜5章（手動1冊スライス）。各章に title/text。
    assert 3 <= len(result.chapters) <= 5
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
    # body は章見出しを含む markdown。
    assert result.chapters[0]["title"] in result.body


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
