"""C1.6: STEP5 装丁の実Vertex/Imagen 最小テスト。

build は creds 不要。live は既定 **skip**（コスト/認証回避・1冊）。実行:
  PUBLISHR_RUN_VERTEX=1 ENABLE_IMAGEN=1 GOOGLE_CLOUD_PROJECT=publishr-498123 \
    uv run pytest agents/tests/test_cover_vertex.py
"""

from __future__ import annotations

import os

import pytest

from publishr_schema import PlanProposal

from publishr_agents.casting import cast_personas
from publishr_agents.cover.vertex_agent import build_cover_prompt_agent, design_covers_vertex
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


def test_cover_prompt_agent_builds_offline():
    agent = build_cover_prompt_agent()
    assert agent.name == "cover"
    assert "gemini" in str(agent.model).lower()  # cover=Flash
    assert agent.output_key == "coverPrompt"
    assert agent.output_schema is None  # 英語プロンプト文字列（構造化しない）


@pytest.mark.vertex
@pytest.mark.skipif(
    os.environ.get("PUBLISHR_RUN_VERTEX") != "1",
    reason="set PUBLISHR_RUN_VERTEX=1 (＋GCP creds) to run live Vertex cover prompt / Imagen",
)
def test_cover_vertex_one_book():
    os.environ.setdefault("GOOGLE_GENAI_USE_VERTEXAI", "TRUE")
    os.environ.setdefault("GOOGLE_CLOUD_PROJECT", "publishr-498123")
    os.environ.setdefault("GOOGLE_CLOUD_LOCATION", "asia-northeast1")

    plan = _plan()
    personas = cast_personas(plan).personas
    books = run_preview(plan, personas, limit=1)  # 1冊（mock・無料）
    enable_imagen = os.environ.get("ENABLE_IMAGEN", "").lower() in ("1", "true", "yes")

    results = design_covers_vertex(books, personas, enable_imagen=enable_imagen)

    assert len(results) == 1
    r = results[0]
    assert r["coverVariant"].startswith("b")
    assert r["coverPrompt"]  # Flash が英語プロンプトを返す
    if enable_imagen:
        assert r["coverUrl"], "ENABLE_IMAGEN 時は coverUrl（保存パス）が埋まる"
