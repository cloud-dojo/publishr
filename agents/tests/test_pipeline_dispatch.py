"""build_pipeline の PUBLISHR_LLM dispatcher テスト（P0bシーム・mock挙動不変）。"""

from __future__ import annotations

import pytest
from google.adk.agents import SequentialAgent

from publishr_agents.pipeline import build_pipeline


def test_mock_default_builds_existing_tree(monkeypatch):
    monkeypatch.delenv("PUBLISHR_LLM", raising=False)
    root = build_pipeline("u_sakura")
    assert isinstance(root, SequentialAgent)
    assert root.name == "editorial_pipeline"
    # 現行の木と同一（observe→reader→planning_team→selection→author→cover）。
    assert [a.name for a in root.sub_agents] == [
        "observe",
        "reader_analyst",
        "planning_team",
        "selection_leader",
        "author_engine",
        "cover_designer",
    ]


def test_mock_explicit(monkeypatch):
    monkeypatch.setenv("PUBLISHR_LLM", "mock")
    assert isinstance(build_pipeline("u_sakura"), SequentialAgent)


def test_vertex_not_implemented_yet(monkeypatch):
    monkeypatch.setenv("PUBLISHR_LLM", "vertex")
    with pytest.raises(NotImplementedError):
        build_pipeline("u_sakura")


def test_unknown_mode_raises(monkeypatch):
    monkeypatch.setenv("PUBLISHR_LLM", "bogus")
    with pytest.raises(ValueError):
        build_pipeline("u_sakura")
