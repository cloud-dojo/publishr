"""OAuth 連携 + Drive フォルダ書込エンドポイント（api-contract.md §4）のテスト。

実Google（code 交換）は exchange_code をモックして隔離。Firebase IDトークン検証も
_verify_uid をモックして決定的に回す（ネットワーク非依存）。
"""

from __future__ import annotations

import time

import pytest
from fastapi.testclient import TestClient
from publishr_api import config
from publishr_api.deps import get_repository
from publishr_api.main import app
from publishr_api.routers import auth as auth_mod
from publishr_api.services import oauth_service

client = TestClient(app)

SECRET = "test-state-secret"


@pytest.fixture(autouse=True)
def _fresh(monkeypatch):
    get_repository.cache_clear()
    monkeypatch.setattr(config.settings, "oauth_state_secret", SECRET)
    monkeypatch.setattr(config.settings, "google_oauth_client_id", "cid.apps.googleusercontent.com")
    monkeypatch.setattr(config.settings, "google_oauth_client_secret", "csecret")
    monkeypatch.setattr(
        config.settings, "oauth_redirect_uri", "https://api.example/api/auth/google/callback"
    )
    monkeypatch.setattr(config.settings, "web_app_url", "https://web.example")
    auth_mod.auth_limiter.reset()
    auth_mod.nonce_store.reset()
    yield
    get_repository.cache_clear()
    auth_mod.auth_limiter.reset()
    auth_mod.nonce_store.reset()


# ── start ────────────────────────────────────────────────────────────────────


def test_start_503_when_unconfigured(monkeypatch):
    monkeypatch.setattr(config.settings, "oauth_state_secret", "")
    assert client.get("/api/auth/google/start").status_code == 503


def test_start_401_without_token(monkeypatch):
    monkeypatch.setattr(auth_mod, "_verify_uid", lambda _a: None)
    assert client.get("/api/auth/google/start").status_code == 401


def test_start_returns_auth_url(monkeypatch):
    monkeypatch.setattr(auth_mod, "_verify_uid", lambda _a: "u_sakura")
    res = client.get("/api/auth/google/start", headers={"Authorization": "Bearer x"})
    assert res.status_code == 200
    url = res.json()["authUrl"]
    assert url.startswith("https://accounts.google.com/o/oauth2/v2/auth?")
    assert "access_type=offline" in url


def test_start_rate_limited_on_rapid_repeat(monkeypatch):
    """同一 uid の /start 連打は 429（C4.9）。"""
    monkeypatch.setattr(auth_mod, "_verify_uid", lambda _a: "u_sakura")
    h = {"Authorization": "Bearer x"}
    assert client.get("/api/auth/google/start", headers=h).status_code == 200
    assert client.get("/api/auth/google/start", headers=h).status_code == 429


# ── callback ───────────────────────────────────────────────────────────────────


class _NullStore:
    def save(self, uid: str, token_json: str) -> None:  # noqa: D401
        pass

    def load(self, uid: str):
        return None


def test_callback_rejects_bad_state():
    res = client.get(
        "/api/auth/google/callback",
        params={"code": "abc", "state": "garbage"},
        follow_redirects=False,
    )
    assert res.status_code == 403


def test_callback_success_updates_user_and_redirects(monkeypatch):
    from publishr_agents.observe.google_source import ALL_SCOPES

    saved: dict[str, str] = {}

    class _FakeStore:
        def save(self, uid: str, token_json: str) -> None:
            saved["uid"] = uid
            saved["token"] = token_json

        def load(self, uid: str):
            return saved.get("token")

    monkeypatch.setattr(auth_mod, "get_token_store", lambda: _FakeStore())
    granted = [ALL_SCOPES["calendar"], ALL_SCOPES["tasks"]]
    monkeypatch.setattr(
        oauth_service,
        "exchange_code",
        lambda code, **kw: oauth_service.TokenExchangeResult(
            token_json='{"refresh_token":"r"}', granted_scopes=granted
        ),
    )
    state = oauth_service.sign_state("u_sakura", secret=SECRET, now=time.time(), nonce="n_cb")
    res = client.get(
        "/api/auth/google/callback",
        params={"code": "authcode", "state": state},
        follow_redirects=False,
    )
    assert res.status_code == 302
    assert res.headers["location"].startswith("https://web.example/connect")
    assert saved["uid"] == "u_sakura"
    assert saved["token"] == '{"refresh_token":"r"}'
    user = get_repository().get_user("u_sakura")
    assert user.connected_sources.calendar.enabled is True
    assert user.connected_sources.tasks.enabled is True
    assert user.connected_sources.drive.enabled is False


def test_callback_preserves_existing_folder_ids(monkeypatch):
    """drive 非付与の再連携でも Picker で選んだ folderIds は消さない（enabled のみ更新）。"""
    from publishr_agents.observe.google_source import ALL_SCOPES
    from publishr_schema import ConnectedSources, DriveConnection

    repo = get_repository()
    user = repo.get_user("u_sakura")
    repo.upsert_user(
        user.model_copy(
            update={
                "connected_sources": ConnectedSources(
                    drive=DriveConnection(enabled=True, folder_ids=["FID_keep"])
                )
            }
        )
    )
    monkeypatch.setattr(auth_mod, "get_token_store", lambda: _NullStore())
    monkeypatch.setattr(
        oauth_service,
        "exchange_code",
        lambda code, **kw: oauth_service.TokenExchangeResult(
            token_json="{}", granted_scopes=[ALL_SCOPES["calendar"]]
        ),
    )
    state = oauth_service.sign_state("u_sakura", secret=SECRET, now=time.time(), nonce="n_cb")
    res = client.get(
        "/api/auth/google/callback",
        params={"code": "c", "state": state},
        follow_redirects=False,
    )
    assert res.status_code == 302
    drive = get_repository().get_user("u_sakura").connected_sources.drive
    assert drive.enabled is False
    assert drive.folder_ids == ["FID_keep"]


def test_callback_400_on_exchange_failure(monkeypatch):
    def _boom(code, **kw):
        raise RuntimeError("token endpoint down")

    monkeypatch.setattr(auth_mod, "get_token_store", lambda: _NullStore())
    monkeypatch.setattr(oauth_service, "exchange_code", _boom)
    state = oauth_service.sign_state("u_sakura", secret=SECRET, now=time.time(), nonce="n_cb")
    res = client.get(
        "/api/auth/google/callback",
        params={"code": "c", "state": state},
        follow_redirects=False,
    )
    assert res.status_code == 400


def test_callback_replay_rejected(monkeypatch):
    """同じ state(nonce) の callback 再生は2回目を 403（C4.9 単回化）。"""
    from publishr_agents.observe.google_source import ALL_SCOPES

    monkeypatch.setattr(auth_mod, "get_token_store", lambda: _NullStore())
    monkeypatch.setattr(
        oauth_service,
        "exchange_code",
        lambda code, **kw: oauth_service.TokenExchangeResult(
            token_json="{}", granted_scopes=[ALL_SCOPES["calendar"]]
        ),
    )
    state = oauth_service.sign_state("u_sakura", secret=SECRET, now=time.time(), nonce="n_replay")
    p = {"code": "c", "state": state}
    assert client.get("/api/auth/google/callback", params=p, follow_redirects=False).status_code == 302
    # 再生（同じ nonce）→ 単回化で 403。
    assert client.get("/api/auth/google/callback", params=p, follow_redirects=False).status_code == 403


# ── drive-folders（C1.1.2 Picker サーバ書込）─────────────────────────────────────


def test_drive_folders_writes_folderids(monkeypatch):
    monkeypatch.setattr(auth_mod, "_verify_uid", lambda _a: "u_sakura")
    res = client.post(
        "/api/connect/drive-folders",
        json={
            "folderIds": ["FID_business", "FID_hobby"],
            "labels": [{"folderId": "FID_business", "label": "業務"}],
        },
        headers={"Authorization": "Bearer x"},
    )
    assert res.status_code == 200
    body = res.json()
    assert body["ok"] is True
    assert body["connectedSources"]["drive"]["folderIds"] == ["FID_business", "FID_hobby"]
    user = get_repository().get_user("u_sakura")
    assert user.connected_sources.drive.folder_ids == ["FID_business", "FID_hobby"]
    assert user.connected_sources.drive.labels[0].label == "業務"


def test_drive_folders_rejects_suspicious_id(monkeypatch):
    monkeypatch.setattr(auth_mod, "_verify_uid", lambda _a: "u_sakura")
    res = client.post(
        "/api/connect/drive-folders",
        json={"folderIds": ["ok", "bad'id"]},
        headers={"Authorization": "Bearer x"},
    )
    assert res.status_code == 400


def test_drive_folders_rejects_bad_label_folder_id(monkeypatch):
    """labels[].folderId にも folderId 検証を適用する（不正文字=400）。"""
    monkeypatch.setattr(auth_mod, "_verify_uid", lambda _a: "u_sakura")
    res = client.post(
        "/api/connect/drive-folders",
        json={"folderIds": ["ok"], "labels": [{"folderId": "bad'id", "label": "業務"}]},
        headers={"Authorization": "Bearer x"},
    )
    assert res.status_code == 400


def test_drive_folders_401_without_uid(monkeypatch):
    monkeypatch.setattr(auth_mod, "_verify_uid", lambda _a: None)
    assert client.post("/api/connect/drive-folders", json={"folderIds": ["x"]}).status_code == 401


def test_drive_folders_demo_fallback_in_mock(monkeypatch):
    """ローカル mock（実データ無し）では demo_uid に縮退して匿名でも書ける。"""
    monkeypatch.setattr(auth_mod, "_verify_uid", lambda _a: None)
    monkeypatch.setattr(config.settings, "data_source", "mock")
    monkeypatch.setattr(config.settings, "demo_uid", "u_sakura")
    res = client.post("/api/connect/drive-folders", json={"folderIds": ["FID_x"]})
    assert res.status_code == 200
    assert get_repository().get_user("u_sakura").connected_sources.drive.folder_ids == ["FID_x"]


# ── repository upsert_user（mock）────────────────────────────────────────────────


def test_mock_upsert_user_roundtrip():
    from publishr_api.repositories.mock_repository import MockRepository
    from publishr_schema import ConnectedSources, TasksConnection

    repo = MockRepository()
    user = repo.get_user("u_sakura")
    assert user is not None
    updated = user.model_copy(
        update={"connected_sources": ConnectedSources(tasks=TasksConnection(enabled=True))}
    )
    saved = repo.upsert_user(updated)
    assert saved.connected_sources.tasks.enabled is True
    assert repo.get_user("u_sakura").connected_sources.tasks.enabled is True
