"""(1) Firebase IDトークン検証の前段＝firebase_admin app の遅延初期化のテスト。

`_verify_uid` は mock モードでも呼ばれるが、従来 firebase_admin app は firestore リポジトリ
でしか初期化されず、mock 時は未初期化で verify_id_token が落ちていた。`_ensure_firebase_app`
が冪等に初期化することを、firebase_admin をモックして offline で検証する（実Auth非依存）。
"""

from __future__ import annotations

import firebase_admin

from publishr_api.routers import api as api_mod


def test_ensure_firebase_app_initializes_once_with_project(monkeypatch):
    calls: list = []
    monkeypatch.setattr(firebase_admin, "_apps", {})

    def fake_init(credential=None, options=None, name="[DEFAULT]"):
        calls.append(options)
        firebase_admin._apps["[DEFAULT]"] = object()

    monkeypatch.setattr(firebase_admin, "initialize_app", fake_init)
    monkeypatch.setenv("GOOGLE_CLOUD_PROJECT", "publishr-498123")

    api_mod._ensure_firebase_app()
    api_mod._ensure_firebase_app()  # 2回目は既存appで no-op（冪等）

    assert len(calls) == 1
    assert calls[0] == {"projectId": "publishr-498123"}


def test_ensure_firebase_app_no_project_passes_none(monkeypatch):
    calls: list = []
    monkeypatch.setattr(firebase_admin, "_apps", {})
    monkeypatch.setattr(
        firebase_admin,
        "initialize_app",
        lambda credential=None, options=None, name="[DEFAULT]": (
            calls.append(options),
            firebase_admin._apps.__setitem__("[DEFAULT]", object()),
        ),
    )
    monkeypatch.delenv("GOOGLE_CLOUD_PROJECT", raising=False)

    api_mod._ensure_firebase_app()
    assert calls == [None]


def test_verify_uid_returns_uid_on_valid_token(monkeypatch):
    monkeypatch.setattr(api_mod, "_ensure_firebase_app", lambda: None)
    import firebase_admin.auth as fb_auth

    monkeypatch.setattr(fb_auth, "verify_id_token", lambda token: {"uid": "u_real"})
    assert api_mod._verify_uid("Bearer goodtoken") == "u_real"


def test_verify_uid_none_without_bearer():
    assert api_mod._verify_uid(None) is None
    assert api_mod._verify_uid("NotBearer x") is None


def test_verify_uid_none_on_verify_error(monkeypatch):
    monkeypatch.setattr(api_mod, "_ensure_firebase_app", lambda: None)
    import firebase_admin.auth as fb_auth

    def boom(token):
        raise ValueError("bad token")

    monkeypatch.setattr(fb_auth, "verify_id_token", boom)
    assert api_mod._verify_uid("Bearer badtoken") is None
