"""llm/provider と registry の整合テスト（P0bシーム）。"""

from __future__ import annotations

import pytest

from publishr_agents.llm.provider import FLASH_DEFAULT, PRO_DEFAULT, model_for, roles
from publishr_agents.prompts.registry import REGISTRY


def test_model_for_pro_and_flash_defaults():
    assert model_for("plan_leader") == PRO_DEFAULT
    assert model_for("reader_analyst") == PRO_DEFAULT
    assert model_for("sub_market") == FLASH_DEFAULT
    assert model_for("cover") == FLASH_DEFAULT


def test_model_for_unknown_role_raises():
    with pytest.raises(KeyError):
        model_for("nope")


def test_env_override(monkeypatch):
    monkeypatch.setenv("PUBLISHR_MODEL_PRO", "gemini-test-pro")
    assert model_for("plan_leader") == "gemini-test-pro"


def test_every_registry_role_has_a_model():
    known = set(roles())
    for spec in REGISTRY.values():
        assert spec.model_role in known, f"{spec.role}: model_role {spec.model_role} unknown to provider"
