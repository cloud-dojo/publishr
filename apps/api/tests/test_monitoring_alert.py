"""Cloud Monitoring → Discord 中継 endpoint（/api/monitoring/discord-alert）のテスト。

GCP の webhook 通知チャネルが送るインシデントJSONを受け、Discord webhook に整形転送する
（本文未承認published アラートの能動通知・レベル1続き）。公開 Cloud Run 上に置くため
`PUBLISHR_MONITORING_WEBHOOK_TOKEN` 設定時は `?token=` を検証。Discord URL 未設定なら no-op＝
ローカル/mock は外部送信ゼロ・挙動不変。
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from publishr_api.config import settings
from publishr_api.main import app
from publishr_api.services import discord_alert

client = TestClient(app)

INCIDENT = {
    "version": "1.2",
    "incident": {
        "incident_id": "0.abc123",
        "state": "open",
        "summary": "本文が未承認のまま published — forced_approve ログが1件以上発生",
        "policy_name": "Publishr: 本文が未承認のまま published",
        "condition_name": "forced_approve ログが1件以上発生（1時間あたり）",
        "resource_name": "publishr-api",
        "url": "https://console.cloud.google.com/monitoring/alerting/incidents/0.abc123?project=publishr-498123",
        "started_at": 1735689600,
    },
}


@pytest.fixture
def _capture_discord(monkeypatch):
    """Discord への実送信を捕捉（ネットワークに出さない）。"""
    calls: list[tuple[str, str]] = []
    monkeypatch.setattr(
        discord_alert, "post_to_discord", lambda url, content: calls.append((url, content)) or True
    )
    return calls


def test_relays_incident_to_discord_when_configured(monkeypatch, _capture_discord):
    monkeypatch.setattr(settings, "discord_alert_webhook_url", "https://discord.test/webhooks/1/x")
    monkeypatch.setattr(settings, "monitoring_webhook_token", "s3cret")

    res = client.post("/api/monitoring/discord-alert?token=s3cret", json=INCIDENT)

    assert res.status_code == 204
    assert len(_capture_discord) == 1
    url, content = _capture_discord[0]
    assert url == "https://discord.test/webhooks/1/x"
    # 主要フィールドが Discord メッセージに含まれる
    assert "Publishr: 本文が未承認のまま published" in content
    assert "open" in content
    assert INCIDENT["incident"]["url"] in content


def test_rejects_bad_token(monkeypatch, _capture_discord):
    monkeypatch.setattr(settings, "discord_alert_webhook_url", "https://discord.test/webhooks/1/x")
    monkeypatch.setattr(settings, "monitoring_webhook_token", "s3cret")

    # トークン不一致
    assert client.post("/api/monitoring/discord-alert?token=wrong", json=INCIDENT).status_code == 401
    # トークン欠落
    assert client.post("/api/monitoring/discord-alert", json=INCIDENT).status_code == 401
    assert _capture_discord == []  # 送信されない


def test_noop_when_webhook_url_unset(monkeypatch, _capture_discord):
    """Discord URL 未設定（ローカル/mock 既定）＝外部送信せず 2xx で受け流す（挙動不変）。"""
    monkeypatch.setattr(settings, "discord_alert_webhook_url", "")
    monkeypatch.setattr(settings, "monitoring_webhook_token", "")

    res = client.post("/api/monitoring/discord-alert", json=INCIDENT)

    assert res.status_code == 204
    assert _capture_discord == []


def test_token_check_skipped_when_token_unset(monkeypatch, _capture_discord):
    """token 未設定（ローカル）なら検証スキップ（worker の audience 空と同方針）。URL 設定時は送る。"""
    monkeypatch.setattr(settings, "discord_alert_webhook_url", "https://discord.test/webhooks/1/x")
    monkeypatch.setattr(settings, "monitoring_webhook_token", "")

    res = client.post("/api/monitoring/discord-alert", json=INCIDENT)

    assert res.status_code == 204
    assert len(_capture_discord) == 1


def test_bad_payload_still_2xx(monkeypatch, _capture_discord):
    """壊れた/空 body でも 2xx（GCP の再送ストームを避ける）。落ちない。"""
    monkeypatch.setattr(settings, "discord_alert_webhook_url", "https://discord.test/webhooks/1/x")
    monkeypatch.setattr(settings, "monitoring_webhook_token", "")

    assert client.post("/api/monitoring/discord-alert", json={}).status_code == 204
    assert client.post(
        "/api/monitoring/discord-alert", content=b"not-json", headers={"content-type": "application/json"}
    ).status_code == 204


# --- 整形ロジックのユニットテスト --------------------------------------------


def test_format_discord_content_includes_key_fields():
    content = discord_alert.format_discord_content(INCIDENT["incident"])
    assert "Publishr: 本文が未承認のまま published" in content
    assert "forced_approve ログが1件以上発生（1時間あたり）" in content
    assert INCIDENT["incident"]["url"] in content
    assert len(content) <= 2000  # Discord content 上限


def test_format_discord_content_handles_missing_fields():
    # 欠損だらけでも例外を出さず文字列を返す（防御的）。
    content = discord_alert.format_discord_content({})
    assert isinstance(content, str)
    assert content  # 空でない


def test_format_discord_content_truncates_long_summary():
    incident = {"summary": "あ" * 5000, "policy_name": "p", "state": "open"}
    content = discord_alert.format_discord_content(incident)
    assert len(content) <= 2000


def test_post_to_discord_sets_non_default_user_agent(monkeypatch):
    """Discord(Cloudflare) は既定 `Python-urllib` UA を 403(1010) で弾くため、明示 UA が必須。"""
    import urllib.request

    captured: dict = {}

    class _Resp:
        status = 204

        def __enter__(self):
            return self

        def __exit__(self, *_a):
            return False

    def _fake_urlopen(req, timeout=None):
        captured["req"] = req
        return _Resp()

    monkeypatch.setattr(urllib.request, "urlopen", _fake_urlopen)
    ok = discord_alert.post_to_discord("https://discord.test/webhooks/1/x", "hi")

    assert ok is True
    ua = captured["req"].get_header("User-agent")
    assert ua, "User-Agent が未設定＝Cloudflare 1010 で弾かれる"
    assert "urllib" not in ua.lower()  # 既定の Python-urllib ではない
