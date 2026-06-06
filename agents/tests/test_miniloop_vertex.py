"""H2: MiniLoop の実Vertex 最小テスト。

既定では **skip**（コスト/認証回避）。実行するには:
  PUBLISHR_RUN_VERTEX=1 GOOGLE_CLOUD_PROJECT=publishr-498123 uv run pytest agents/tests/test_miniloop_vertex.py
"""

from __future__ import annotations

import os

import pytest


@pytest.mark.vertex
@pytest.mark.skipif(
    os.environ.get("PUBLISHR_RUN_VERTEX") != "1",
    reason="set PUBLISHR_RUN_VERTEX=1 (＋GCP creds) to run live Vertex MiniLoop",
)
def test_miniloop_exits_with_approved_plan():
    os.environ.setdefault("GOOGLE_GENAI_USE_VERTEXAI", "TRUE")
    os.environ.setdefault("GOOGLE_CLOUD_PROJECT", "publishr-498123")
    os.environ.setdefault("GOOGLE_CLOUD_LOCATION", "asia-northeast1")

    from publishr_agents.vertex import run_miniloop

    result = run_miniloop()

    # ループは必ず承認で抜ける（escalate or round3強制承認）。
    assert result["approvedPlan"], "loop must exit with an approved plan"
    # 少なくとも1ラウンドの採点遷移が記録される。
    assert result["verdict_history"], "must record at least one leader verdict"
    # 最大3ラウンドで収束。
    assert result["rounds"] <= 3
    # 各ラウンドは score/decision を持つ。
    for v in result["verdict_history"]:
        assert "score" in v and "decision" in v


def test_miniloop_builds_offline():
    """ビルド（実LLM呼び出しなし）は creds 不要で通ること＝構造の健全性。"""
    from publishr_agents.vertex import build_miniloop

    root = build_miniloop()
    assert root.name == "miniloop_root"
    names = [a.name for a in root.sub_agents]
    assert names == ["market_sub", "planning_loop"]
    loop = root.sub_agents[1]
    assert loop.max_iterations == 3
    assert [a.name for a in loop.sub_agents] == ["plan_owner", "plan_leader", "loop_break"]
