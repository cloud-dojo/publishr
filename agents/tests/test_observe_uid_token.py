"""C1.1.1/1.1.2: Web OAuth 経路の per-uid トークン解決（オフライン・決定的）。

実Google取得は test_observe_google.py（@pytest.mark.google・gated）。ここはパス解決と
トークン未配置時の挙動のみ（ネットワーク・google extra 非依存）。
"""

from __future__ import annotations

import pytest

from publishr_agents.observe.google_source import (
    load_credentials_for_uid,
    per_uid_token_path,
    token_dir,
)


def test_per_uid_token_path_is_under_token_dir(tmp_path, monkeypatch):
    monkeypatch.setenv("PUBLISHR_GOOGLE_TOKEN_DIR", str(tmp_path))
    path = per_uid_token_path("u_sakura")
    assert path == tmp_path / "u_sakura.json"
    assert path.parent == token_dir()


def test_per_uid_token_path_sanitizes_uid(tmp_path, monkeypatch):
    """パス区切りや '..' を含む uid でも保存ディレクトリを脱出しない。"""
    monkeypatch.setenv("PUBLISHR_GOOGLE_TOKEN_DIR", str(tmp_path))
    path = per_uid_token_path("../../etc/passwd")
    assert path.parent == tmp_path
    assert "/" not in path.name
    assert ".." not in path.name


def test_load_credentials_for_uid_missing_raises(tmp_path, monkeypatch):
    """トークン未配置は明確な FileNotFoundError（google extra 非依存＝パス検査が先）。"""
    monkeypatch.setenv("PUBLISHR_GOOGLE_TOKEN_DIR", str(tmp_path))
    with pytest.raises(FileNotFoundError):
        load_credentials_for_uid("u_nobody")
