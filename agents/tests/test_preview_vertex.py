"""C1.5: STEP4 プレビュー編集の実Vertex 最小テスト。

build は creds 不要。live は既定 **skip**（コスト/認証回避・1冊のみ）。実行:
  PUBLISHR_RUN_VERTEX=1 GOOGLE_CLOUD_PROJECT=publishr-498123 \
    uv run pytest agents/tests/test_preview_vertex.py
"""

from __future__ import annotations

import os

import pytest

from publishr_schema import BookDraft, EditorVerdict, PlanProposal

from publishr_agents import state_keys as K
from publishr_agents.casting import cast_personas
from publishr_agents.preview.vertex_agent import (
    build_author_agent,
    build_editor_agent,
    run_preview_vertex,
)


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
        }
    )


def test_author_and_editor_agents_build_offline():
    author = build_author_agent()
    editor = build_editor_agent()
    assert author.name == "author_preview"
    assert author.output_schema is BookDraft
    assert "gemini" in str(author.model).lower()
    assert editor.name == "editor_preview"
    assert editor.output_schema is EditorVerdict
    assert editor.output_key == K.EDITOR_VERDICT


@pytest.mark.vertex
@pytest.mark.skipif(
    os.environ.get("PUBLISHR_RUN_VERTEX") != "1",
    reason="set PUBLISHR_RUN_VERTEX=1 (＋GCP creds) to run live Vertex preview",
)
def test_preview_vertex_one_book_has_seven_fields():
    os.environ.setdefault("GOOGLE_GENAI_USE_VERTEXAI", "TRUE")
    os.environ.setdefault("GOOGLE_CLOUD_PROJECT", "publishr-498123")
    os.environ.setdefault("GOOGLE_CLOUD_LOCATION", "asia-northeast1")

    plan = _plan()
    personas = cast_personas(plan).personas  # 決定的5人（mock・無料）
    results = run_preview_vertex(plan, personas, limit=1)  # 1冊のみ＝最小コスト

    assert len(results) == 1
    draft = BookDraft.model_validate(results[0]["bookDraft"])
    assert draft.title and draft.delivery_reason and draft.preface_sample
    assert draft.agenda
    assert results[0]["verdict"] is not None
