"""C1.3: STEP2 企画3階層の実Vertex 最小テスト。

build は creds 不要（トポロジの健全性）。live は既定 **skip**（コスト/認証回避）。実行:
  PUBLISHR_RUN_VERTEX=1 GOOGLE_CLOUD_PROJECT=publishr-498123 \
    uv run pytest agents/tests/test_planning_vertex.py
"""

from __future__ import annotations

import os

import pytest

from publishr_schema import load_users

from publishr_agents.observe import FixtureObservationSource, collect_observation
from publishr_agents.planning.vertex_agent import build_planning, run_planning_vertex
from publishr_agents.reader import analyze_reader


def test_planning_topology_builds_offline():
    """Sequential[Parallel[3サブ]→Loop[owner→leader→break]] が creds 不要で組める。"""
    root = build_planning(threshold=70)
    assert root.name == "planning_root"
    names = [a.name for a in root.sub_agents]
    assert names == ["research_subs", "planning_loop"]

    research = root.sub_agents[0]
    assert [a.name for a in research.sub_agents] == [
        "sub_reader_context",
        "sub_market",
        "sub_theme_insight",
    ]
    loop = root.sub_agents[1]
    assert loop.max_iterations == 3
    assert [a.name for a in loop.sub_agents] == ["plan_owner", "plan_leader", "loop_break"]


@pytest.mark.vertex
@pytest.mark.skipif(
    os.environ.get("PUBLISHR_RUN_VERTEX") != "1",
    reason="set PUBLISHR_RUN_VERTEX=1 (＋GCP creds) to run live Vertex STEP2 planning",
)
def test_planning_vertex_loop_exits_with_approved_plan():
    os.environ.setdefault("GOOGLE_GENAI_USE_VERTEXAI", "TRUE")
    os.environ.setdefault("GOOGLE_CLOUD_PROJECT", "publishr-498123")
    os.environ.setdefault("GOOGLE_CLOUD_LOCATION", "asia-northeast1")

    from datetime import datetime, timedelta, timezone

    jst = timezone(timedelta(hours=9))
    now = datetime(2026, 6, 3, 6, 0, tzinfo=jst)
    user = next(u for u in load_users() if u.id == "u_sakura")
    bundle = collect_observation(user, now=now, source=FixtureObservationSource())
    profile = analyze_reader(bundle, user=user, llm="mock")  # STEP1 は決定的でコスト節約

    # threshold を高めにして差し戻しを誘発（reject→再提出→承認/3R）。
    result = run_planning_vertex(profile, threshold=85)

    assert result["approvedPlan"], "ループは必ず承認で抜ける"
    assert result["verdictHistory"], "採点遷移が記録される"
    assert result["rounds"] <= 3
    # 3サブが走っている（B/C は grounding text）。
    assert result["subReaderContext"] is not None
    assert result["subMarket"]
