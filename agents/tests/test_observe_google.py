"""C1.1: STEP0 観測の実Google API 最小テスト。

既定では **skip**（OAuth/ネットワーク回避）。実行するには先に OAuth 同意を済ませる:
  uv run python scripts/google_oauth_bootstrap.py
  PUBLISHR_RUN_GOOGLE=1 uv run pytest agents/tests/test_observe_google.py
"""

from __future__ import annotations

import os
from datetime import datetime, timezone

import pytest

from publishr_schema import ObservationBundle, load_users

from publishr_agents.observe.google_source import GoogleObservationSource


@pytest.mark.google
@pytest.mark.skipif(
    os.environ.get("PUBLISHR_RUN_GOOGLE") != "1",
    reason="set PUBLISHR_RUN_GOOGLE=1 (＋OAuth token) to run live Google observation",
)
def test_google_observation_collects_real_bundle():
    user = next(u for u in load_users() if u.id == "u_sakura")
    now = datetime.now(timezone.utc)

    bundle = GoogleObservationSource().collect(user, now=now)

    assert isinstance(bundle, ObservationBundle)
    assert bundle.user_id == "u_sakura"
    assert bundle.collected_at == now.isoformat()
    # 実データは可変なので、束が壊れていない（=妥当な型・窓内）ことのみ保証する。
    total = len(bundle.drive.files) + len(bundle.calendar.events) + len(bundle.tasks.items)
    assert total >= 0
    assert all(f.file_id for f in bundle.drive.files)
    assert all(len(f.text_excerpt) <= 4000 for f in bundle.drive.files)


def test_google_source_without_token_raises(tmp_path, monkeypatch):
    """トークン未配置だと明確なエラー（live でなくても通る健全性チェック）。"""
    monkeypatch.setenv("PUBLISHR_GOOGLE_TOKEN", str(tmp_path / "missing.json"))
    from publishr_agents.observe.google_source import load_credentials

    with pytest.raises(FileNotFoundError):
        load_credentials()
