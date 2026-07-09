"""per-uid OAuth トークン保存（FileTokenStore）の単体テスト。

SecretManagerTokenStore は本番（実GCP）専用で gated。ここは file バックエンドのみ。
"""

from __future__ import annotations

from publishr_api.services.token_store import FileTokenStore, get_token_store


def test_file_store_roundtrip(tmp_path, monkeypatch):
    monkeypatch.setenv("PUBLISHR_GOOGLE_TOKEN_DIR", str(tmp_path))
    store = FileTokenStore()
    assert store.load("u_sakura") is None
    store.save("u_sakura", '{"refresh_token":"x"}')
    assert store.load("u_sakura") == '{"refresh_token":"x"}'
    assert (tmp_path / "u_sakura.json").exists()


def test_get_token_store_defaults_to_file(monkeypatch):
    from publishr_api import config

    monkeypatch.setattr(config.settings, "oauth_token_store", "file")
    assert isinstance(get_token_store(), FileTokenStore)
