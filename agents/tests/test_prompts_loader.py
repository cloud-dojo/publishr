"""prompts/loader の H0b テスト：全11本の .md から非空 system を抽出できる。"""

from __future__ import annotations

from publishr_agents.prompts.loader import load_prompt

PROMPT_FILES = [
    "step1_reader_analyst",
    "step2_research_subs",
    "step2_plan_owner",
    "step2_plan_leader",
    "step3_casting_editor",
    "step4_author_preview",
    "step4_editor_preview",
    "step5_cover",
    "modeB_author_body",
    "modeB_editor_body",
    "eval_judge",
]


def test_all_prompts_have_nonempty_system():
    for name in PROMPT_FILES:
        doc = load_prompt(name)
        assert doc.system.strip(), f"{name}: empty system"


def test_user_templates_present_where_expected():
    for name in ["step1_reader_analyst", "step2_plan_owner", "step5_cover"]:
        assert load_prompt(name).user_template, f"{name}: missing user template"


def test_research_subs_bundles_three_subsystems():
    system = load_prompt("step2_research_subs").system
    assert "subReaderContext" in system
    assert "subMarket" in system
    assert "subThemeInsight" in system


def test_scoring_prompt_has_good_example():
    # leader/editor 等の採点系は ✅例を持つ（few-shot 常時ONの校正材料）。
    assert load_prompt("step2_plan_leader").good_example
