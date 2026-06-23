"""C1.4: STEP3 キャスティングの実Vertex 最小テスト。

build は creds 不要。live は既定 **skip**（コスト/認証回避）。実行:
  PUBLISHR_RUN_VERTEX=1 GOOGLE_CLOUD_PROJECT=publishr-498123 \
    uv run pytest agents/tests/test_casting_vertex.py
"""

from __future__ import annotations

import os

import pytest

from publishr_schema import AuthorCasting, GeneratedPersonaSet, PlanProposal

from publishr_agents import state_keys as K
from publishr_agents.casting.vertex_agent import (
    build_author_casting_agent,
    build_casting_agent,
    cast_author_vertex,
    cast_personas_vertex,
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
            "recommendedAuthorTypes": ["実務家タイプ", "対話・コーチング型"],
        }
    )


def test_casting_agent_builds_offline():
    agent = build_casting_agent()
    assert agent.name == "persona_generator"
    assert "gemini" in str(agent.model).lower()
    assert agent.output_key == K.GENERATED_PERSONA_SET
    assert agent.output_schema is GeneratedPersonaSet


@pytest.mark.vertex
@pytest.mark.skipif(
    os.environ.get("PUBLISHR_RUN_VERTEX") != "1",
    reason="set PUBLISHR_RUN_VERTEX=1 (＋GCP creds) to run live Vertex casting",
)
def test_casting_vertex_generates_five_diverse_personas():
    os.environ.setdefault("GOOGLE_GENAI_USE_VERTEXAI", "TRUE")
    os.environ.setdefault("GOOGLE_CLOUD_PROJECT", "publishr-498123")
    os.environ.setdefault("GOOGLE_CLOUD_LOCATION", "asia-northeast1")

    result = cast_personas_vertex(_plan())

    assert isinstance(result, GeneratedPersonaSet)
    assert len(result.personas) == 5
    # voiceStyle×format が分散している（多様性）。
    combos = {(p.voice_style, p.format) for p in result.personas}
    assert len(combos) >= 4
    assert all(p.persona for p in result.personas)  # persona が薄くない


# ── author_casting（v3・4テーマ・3候補→1選抜）────────────────────
def test_author_casting_agent_builds_offline():
    agent = build_author_casting_agent()
    assert agent.name == "author_casting"
    assert "gemini" in str(agent.model).lower()
    assert agent.output_key == K.AUTHOR_CASTING
    assert agent.output_schema is AuthorCasting


@pytest.mark.vertex
@pytest.mark.skipif(
    os.environ.get("PUBLISHR_RUN_VERTEX") != "1",
    reason="set PUBLISHR_RUN_VERTEX=1 (＋GCP creds) to run live Vertex author_casting",
)
def test_author_casting_vertex_picks_one_of_three():
    os.environ.setdefault("GOOGLE_GENAI_USE_VERTEXAI", "TRUE")
    os.environ.setdefault("GOOGLE_CLOUD_PROJECT", "publishr-498123")
    os.environ.setdefault("GOOGLE_CLOUD_LOCATION", "asia-northeast1")

    result = cast_author_vertex(_plan())

    assert isinstance(result, AuthorCasting)
    assert len(result.candidates) == 3
    assert result.chosen is not None
    # chosen は candidates の1人と一致（personaId 対応）。
    assert result.chosen.persona_id in {c.persona_id for c in result.candidates}
    # 3候補は voiceStyle×format で散る。
    combos = {(c.voice_style, c.format) for c in result.candidates}
    assert len(combos) >= 2
    assert result.selection_reason  # 選抜理由（証跡）がある
