"""C1.2: STEP1 読者分析の実Vertex 最小テスト。

build は creds 不要（構造の健全性）。live は既定 **skip**（コスト/認証回避）。実行するには:
  PUBLISHR_RUN_VERTEX=1 GOOGLE_CLOUD_PROJECT=publishr-498123 \
    uv run pytest agents/tests/test_reader_vertex.py
"""

from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone

import pytest

from publishr_schema import ReaderProfile3Layer, load_users

from publishr_agents import state_keys as K
from publishr_agents.observe import FixtureObservationSource, collect_observation
from publishr_agents.reader.vertex_agent import analyze_reader_vertex, build_reader_agent

JST = timezone(timedelta(hours=9))
NOW = datetime(2026, 6, 3, 6, 0, tzinfo=JST)


def test_reader_agent_builds_offline():
    """LlmAgent ビルド（実LLM呼び出しなし）は creds 不要で通る＝構造の健全性。"""
    agent = build_reader_agent()
    assert agent.name == "reader_analyst"
    assert "gemini" in str(agent.model).lower()
    assert agent.output_key == K.READER_PROFILE
    assert agent.output_schema is ReaderProfile3Layer


@pytest.mark.vertex
@pytest.mark.skipif(
    os.environ.get("PUBLISHR_RUN_VERTEX") != "1",
    reason="set PUBLISHR_RUN_VERTEX=1 (＋GCP creds) to run live Vertex reader analysis",
)
def test_reader_vertex_produces_three_layer_profile():
    os.environ.setdefault("GOOGLE_GENAI_USE_VERTEXAI", "TRUE")
    os.environ.setdefault("GOOGLE_CLOUD_PROJECT", "publishr-498123")
    os.environ.setdefault("GOOGLE_CLOUD_LOCATION", "asia-northeast1")

    user = next(u for u in load_users() if u.id == "u_sakura")
    bundle = collect_observation(user, now=NOW, source=FixtureObservationSource())

    profile = analyze_reader_vertex(bundle, user=user)

    assert isinstance(profile, ReaderProfile3Layer)
    assert profile.base is not None
    assert profile.current_work is not None
    # 実LLMは観測の具体に踏み込むはず（evidence で根拠を出す）。
    assert profile.current_work.evidence, "currentWork.evidence が空でない（一般論回避）"
