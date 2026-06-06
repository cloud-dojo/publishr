"""BFF 設定の P0b 実行プロファイル項目を検証する。"""

from __future__ import annotations

from publishr_api.config import Settings


def test_settings_default_to_mock_dev_profile():
    settings = Settings(_env_file=None)

    assert settings.publishr_llm == "mock"
    assert settings.publishr_run_profile == "dev"
    assert settings.prompt_fewshot == "on"
    assert settings.max_books_per_run == 2
    assert settings.max_body_pages == 5
    assert settings.enable_imagen is False


def test_settings_accept_prod_runtime_overrides(monkeypatch):
    monkeypatch.setenv("PUBLISHR_RUN_PROFILE", "prod")
    monkeypatch.setenv("PUBLISHR_MAX_BOOKS_PER_RUN", "5")
    monkeypatch.setenv("PUBLISHR_MAX_BODY_PAGES", "100")
    monkeypatch.setenv("ENABLE_IMAGEN", "true")

    settings = Settings(_env_file=None)

    assert settings.publishr_run_profile == "prod"
    assert settings.max_books_per_run == 5
    assert settings.max_body_pages == 100
    assert settings.enable_imagen is True
