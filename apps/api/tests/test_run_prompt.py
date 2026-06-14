"""単発プロンプトランナー（scripts/run_prompt.py・C5.1）のオフラインテスト。

assemble() は実LLMを呼ばず system/user/model を組み立てる純粋関数＝決定的・$0。
実Vertex 実行は test_run_prompt_vertex.py（gated）。
"""

from __future__ import annotations

import importlib.util
from pathlib import Path

from publishr_agents.prompts.registry import REGISTRY

ROOT = Path(__file__).resolve().parents[3]
SPEC = importlib.util.spec_from_file_location("run_prompt", ROOT / "scripts" / "run_prompt.py")
assert SPEC and SPEC.loader
run_prompt = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(run_prompt)

SCORING_ROLES = ["plan_leader", "editor_preview", "modeb_editor", "eval_judge"]


def test_assemble_all_roles_nonempty():
    """全13ロールが（空stateでも）system/user/model を組み立てられる＝セクション切出し等が壊れていない。"""
    for role in REGISTRY:
        plan = run_prompt.assemble(role, {})
        assert plan["system"].strip(), f"{role}: system empty"
        assert plan["user"].strip(), f"{role}: user empty"
        assert plan["model"], f"{role}: model empty"


def test_scoring_roles_inject_fewshot():
    """採点系は few-shot 常時ON → 参考出力例が system に入る（render.build_system_text 規律）。"""
    for role in SCORING_ROLES:
        plan = run_prompt.assemble(role, {})
        assert "参考出力例" in plan["system"], f"{role}: few-shot 未注入"
        assert plan["is_scoring"] is True


def test_state_is_injected_into_system():
    """state の {{var}} が system に差し込まれる（plan_leader の {{threshold}}）。"""
    plan = run_prompt.assemble("plan_leader", {"threshold": 4242})
    assert "4242" in plan["system"]


def test_subs_sections_are_isolated():
    """step2_research_subs の3サブは、それぞれ別セクションの system になる（merged ではない）。"""
    systems = {
        role: run_prompt.assemble(role, {})["system"]
        for role in ("sub_reader_context", "sub_market", "sub_theme_insight")
    }
    assert len(set(systems.values())) == 3, "サブの system が分離されていない"


def test_grounded_and_structured_flags():
    """grounding サブは structured(JSON強制)にしない／スキーマ無しロールは structured=False。"""
    market = run_prompt.assemble("sub_market", {})
    assert market["grounded"] is True and market["structured"] is False
    leader = run_prompt.assemble("plan_leader", {})
    assert leader["structured"] is True  # LeaderVerdict スキーマ
    cover = run_prompt.assemble("cover", {})
    assert cover["structured"] is False  # output_schema 無し（Imagen プロンプト文）


def test_unknown_role_raises():
    try:
        run_prompt.assemble("does_not_exist", {})
    except KeyError:
        pass
    else:
        raise AssertionError("unknown role で KeyError を期待")
