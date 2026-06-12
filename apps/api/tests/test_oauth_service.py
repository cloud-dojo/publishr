"""OAuth サービス（state 署名/検証・認可URL組立）の単体テスト。

決定的・ネットワーク非依存。code 交換（実Google）は exchange_code に隔離し、ここでは触れない。
"""

from __future__ import annotations

import pytest
from publishr_api.services import oauth_service

SECRET = "test-state-secret"


def test_sign_verify_roundtrip():
    state = oauth_service.sign_state("u_sakura", secret=SECRET, now=1000.0)
    assert oauth_service.verify_state(state, secret=SECRET, now=1005.0) == "u_sakura"


def test_verify_rejects_tampered_signature():
    state = oauth_service.sign_state("u_sakura", secret=SECRET, now=1000.0)
    body, _sig = state.split(".", 1)
    with pytest.raises(oauth_service.StateError):
        oauth_service.verify_state(f"{body}.AAAA", secret=SECRET, now=1005.0)


def test_verify_rejects_wrong_secret():
    state = oauth_service.sign_state("u_sakura", secret=SECRET, now=1000.0)
    with pytest.raises(oauth_service.StateError):
        oauth_service.verify_state(state, secret="other-secret", now=1005.0)


def test_verify_rejects_expired():
    state = oauth_service.sign_state("u_sakura", secret=SECRET, now=1000.0)
    with pytest.raises(oauth_service.StateError):
        oauth_service.verify_state(state, secret=SECRET, now=1000.0 + 10_000, max_age_sec=600)


def test_verify_rejects_uid_swap_keeps_signature():
    """別uidのbody＋正規署名の貼り合わせは署名不一致で弾く（uid改ざん耐性）。"""
    legit = oauth_service.sign_state("u_sakura", secret=SECRET, now=1000.0)
    evil = oauth_service.sign_state("u_evil", secret="x", now=1000.0)
    body_evil, _ = evil.split(".", 1)
    _, sig_ok = legit.split(".", 1)
    with pytest.raises(oauth_service.StateError):
        oauth_service.verify_state(f"{body_evil}.{sig_ok}", secret=SECRET, now=1005.0)


def test_verify_rejects_future_iat():
    """発行時刻が許容ずれを超えて未来の state は弾く（時計改ざん耐性）。"""
    state = oauth_service.sign_state("u_sakura", secret=SECRET, now=10_000.0)
    with pytest.raises(oauth_service.StateError):
        oauth_service.verify_state(state, secret=SECRET, now=10_000.0 - 5_000)


def test_build_auth_url_contains_required_params():
    url, state = oauth_service.build_auth_url(
        "u_sakura",
        client_id="cid.apps.googleusercontent.com",
        redirect_uri="https://api.example/api/auth/google/callback",
        secret=SECRET,
        now=1000.0,
        scopes=["https://www.googleapis.com/auth/calendar.readonly"],
    )
    assert url.startswith("https://accounts.google.com/o/oauth2/v2/auth?")
    assert "client_id=cid.apps.googleusercontent.com" in url
    assert "access_type=offline" in url
    assert "response_type=code" in url
    assert "calendar.readonly" in url
    assert "state=" in url
    # 返した state は検証可能（uid 復元できる）。
    assert oauth_service.verify_state(state, secret=SECRET, now=1001.0) == "u_sakura"
