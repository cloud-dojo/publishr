"""prompts/render の P0bシームテスト（変数注入 + few-shot 規律）。"""

from __future__ import annotations

from publishr_agents.prompts.render import build_system_text, make_instruction


class _Ctx:
    def __init__(self, state: dict):
        self.state = state


def test_make_instruction_returns_callable_and_injects_var():
    provider = make_instruction("plan_leader")
    text = provider(_Ctx({"threshold": 70}))
    assert isinstance(text, str) and text
    # leader system は {{threshold}} を含む → 注入される。
    assert "70" in text


def test_nested_var_injection():
    # 著者プレビュー system は {{persona.name}} を含む（ネストパス自前展開）。
    text = build_system_text("author_preview", {"persona": {"name": "神崎 玄一郎"}})
    assert "神崎 玄一郎" in text


def test_scoring_role_fewshot_always_on(monkeypatch):
    monkeypatch.setenv("PROMPT_FEWSHOT", "off")
    text = build_system_text("plan_leader", {})
    assert "参考出力例" in text  # 採点系は off でも付く


def test_generation_role_respects_flag(monkeypatch):
    monkeypatch.setenv("PROMPT_FEWSHOT", "off")
    assert "参考出力例" not in build_system_text("plan_owner", {})
    monkeypatch.setenv("PROMPT_FEWSHOT", "on")
    assert "参考出力例" in build_system_text("plan_owner", {})
