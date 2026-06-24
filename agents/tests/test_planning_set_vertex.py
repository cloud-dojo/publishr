"""PR-5: STEP2 4テーマ・セット企画の実Vertex 最小テスト。

build は creds 不要（トポロジの健全性）。live は既定 **skip**（コスト/認証回避）。実行:
  PUBLISHR_RUN_VERTEX=1 GOOGLE_CLOUD_PROJECT=publishr-498123 \
    uv run pytest agents/tests/test_planning_set_vertex.py
"""

from __future__ import annotations

import os

import pytest

from publishr_schema import PlanSet, PlanSetVerdict, ThemeAssignmentSet, load_users

from publishr_agents.observe import FixtureObservationSource, collect_observation
from publishr_agents.planning.vertex_set import (
    build_planning_set,
    build_research_trio,
    build_team_pipeline,
    run_planning_set_vertex,
)
from publishr_agents.reader import analyze_reader


# ── トポロジ（creds 不要）─────────────────────────────────────
def test_research_trio_is_new_today_market_classics():
    """調査トリオが新3観点（今=sub_trend / 市場=sub_competitors / 普遍=sub_classics）で組める。"""
    trio = build_research_trio()
    assert trio.name == "research_trio"
    assert [a.name for a in trio.sub_agents] == ["sub_trend", "sub_competitors", "sub_classics"]


def test_team_pipeline_is_research_then_owner():
    team = build_team_pipeline()
    assert team.name == "team_pipeline"
    assert [a.name for a in team.sub_agents] == ["research_trio", "plan_owner"]


def test_planning_set_topology_builds_offline():
    parts = build_planning_set()
    assert parts["themes"].name == "editor_chief_themes"
    assert parts["themes"].output_schema is ThemeAssignmentSet
    assert parts["set_gate"].name == "editor_chief_gate"
    assert parts["set_gate"].output_schema is PlanSetVerdict
    # team_pipeline は research_trio → plan_owner。
    assert [a.name for a in parts["team_pipeline"].sub_agents] == ["research_trio", "plan_owner"]


# ── live（実Vertex・既定 skip）────────────────────────────────
@pytest.mark.vertex
@pytest.mark.skipif(
    os.environ.get("PUBLISHR_RUN_VERTEX") != "1",
    reason="set PUBLISHR_RUN_VERTEX=1 (＋GCP creds) to run live Vertex STEP2 set planning",
)
def test_planning_set_vertex_yields_four_plans():
    os.environ.setdefault("GOOGLE_GENAI_USE_VERTEXAI", "TRUE")
    os.environ.setdefault("GOOGLE_CLOUD_PROJECT", "publishr-498123")
    os.environ.setdefault("GOOGLE_CLOUD_LOCATION", "asia-northeast1")

    from datetime import datetime, timedelta, timezone

    jst = timezone(timedelta(hours=9))
    now = datetime(2026, 6, 3, 6, 0, tzinfo=jst)
    user = next(u for u in load_users() if u.id == "u_sakura")
    bundle = collect_observation(user, now=now, source=FixtureObservationSource())
    profile = analyze_reader(bundle, user=user, llm="mock")  # STEP1 は決定的でコスト節約

    result = run_planning_set_vertex(profile, threshold=70)

    tas = ThemeAssignmentSet.model_validate(result["themeAssignmentSet"])
    assert len(tas.assignments) == 4, "編集長が4テーマを割り当てる"
    ps = PlanSet.model_validate(result["planSet"])
    assert len(ps.plans) == 4, "4冊が承認される（最高3R・棚を空にしない）"
    # I-39: 各 plan は proposal_id を必ず持つ（None だと PipelineResult が落ち cast_None になる）。
    pids = [p.proposal_id for p in ps.plans]
    assert all(pids), f"proposal_id must be non-None on vertex path: {pids}"
    assert len(set(pids)) == 4, "proposal_id は4冊で一意"
    PlanSetVerdict.model_validate(result["planSetVerdict"])
    assert result["verdictHistory"], "セットゲートの採点遷移が記録される"
    assert result["rounds"] <= 3
