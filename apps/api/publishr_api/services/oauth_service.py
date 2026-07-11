"""Google OAuth 連携サービス。

start でFirebaseユーザー uid を HMAC 署名 state 付き同意URLへ、callback で code をトークン交換。
純粋ロジック（state 署名/検証・URL 組立）と I/O（code 交換・ネットワーク）を分離し、前者は
決定的にテスト、後者（exchange_code）は実Google・@pytest.mark.google/手動で隔離する。
refresh token は呼び出し側が token_store 経由で保存し、生トークン・code はログに出さない。
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import secrets
import threading
from dataclasses import dataclass, field
from urllib.parse import urlencode

GOOGLE_AUTH_ENDPOINT = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_ENDPOINT = "https://oauth2.googleapis.com/token"

# state の既定有効期限（短命・CSRF対策）。
DEFAULT_STATE_TTL_SEC = 600
# 時計ずれ許容（未来発行の上限）。
_CLOCK_SKEW_SEC = 60


class StateError(Exception):
    """state 検証失敗（署名不一致・期限切れ・形式不正＝CSRF の疑い）。"""


def _b64url_encode(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")


def _b64url_decode(value: str) -> bytes:
    pad = "=" * (-len(value) % 4)
    return base64.urlsafe_b64decode(value + pad)


def _resolved_scopes(scopes: list[str] | None) -> list[str]:
    """既定は観測と同一スコープ（保存トークンを observe が使えるよう一致させる）。

    観測側 `resolve_scopes()`（PUBLISHR_GOOGLE_SCOPES 反映）を遅延 import で再利用する。
    """
    if scopes:
        return scopes
    from publishr_agents.observe.google_source import resolve_scopes

    return resolve_scopes()


def sign_state(uid: str, *, secret: str, now: float, nonce: str = "") -> str:
    """uid 紐付き・短命・HMAC-SHA256 署名の state を作る。

    形式: base64url(JSON{uid,iat,nonce}) + "." + base64url(HMAC)。
    """
    payload = {"uid": uid, "iat": int(now), "nonce": nonce}
    body = _b64url_encode(
        json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")
    )
    sig = hmac.new(secret.encode("utf-8"), body.encode("ascii"), hashlib.sha256).digest()
    return f"{body}.{_b64url_encode(sig)}"


def verify_state_payload(
    state: str, *, secret: str, now: float, max_age_sec: int = DEFAULT_STATE_TTL_SEC
) -> dict:
    """state を検証して `{uid, iat, nonce}` を返す。署名不一致・期限切れ・形式不正は StateError。"""
    try:
        body, sig_b64 = state.split(".", 1)
    except ValueError as exc:
        raise StateError("state の形式が不正です") from exc
    expected = hmac.new(secret.encode("utf-8"), body.encode("ascii"), hashlib.sha256).digest()
    try:
        got = _b64url_decode(sig_b64)
    except Exception as exc:  # noqa: BLE001 — 復号不能は検証失敗に倒す
        raise StateError("state の署名が不正です") from exc
    if not hmac.compare_digest(expected, got):
        raise StateError("state の署名が一致しません")
    try:
        payload = json.loads(_b64url_decode(body))
    except Exception as exc:  # noqa: BLE001
        raise StateError("state のペイロードが壊れています") from exc
    iat = payload.get("iat")
    uid = payload.get("uid")
    if not isinstance(iat, int) or not isinstance(uid, str) or not uid:
        raise StateError("state のペイロードが不正です")
    if now - iat > max_age_sec:
        raise StateError("state の有効期限が切れています")
    if iat - now > _CLOCK_SKEW_SEC:
        raise StateError("state の発行時刻が不正です")
    return {"uid": uid, "iat": iat, "nonce": str(payload.get("nonce", ""))}


def verify_state(
    state: str, *, secret: str, now: float, max_age_sec: int = DEFAULT_STATE_TTL_SEC
) -> str:
    """state を検証して uid を返す（後方互換）。nonce も要るときは verify_state_payload。"""
    return verify_state_payload(state, secret=secret, now=now, max_age_sec=max_age_sec)["uid"]


class NonceStore:
    """OAuth state の nonce を単回化する（replay 防止・C4.9）。インメモリ・スレッド安全。

    `consume(nonce)` は初回 True、2回目以降は False（=replay）。nonce 無しも False（単回化
    できないため拒否）。`ttl_sec` 経過分は掃除して肥大を防ぐ（state TTL と同じ）。
    注意: 1プロセス内のみ。マルチインスタンスでは共有ストアが要る（C4.9残・PKCE/cookie束縛も別途）。
    """

    def __init__(self, *, ttl_sec: float = DEFAULT_STATE_TTL_SEC) -> None:
        self._ttl = float(ttl_sec)
        self._lock = threading.Lock()
        self._used: dict[str, float] = {}

    def consume(self, nonce: str, *, now: float) -> bool:
        if not nonce:
            return False
        with self._lock:
            for n in [n for n, t in self._used.items() if now - t > self._ttl]:
                del self._used[n]
            if nonce in self._used:
                return False
            self._used[nonce] = now
            return True

    def reset(self) -> None:
        with self._lock:
            self._used.clear()


def build_auth_url(
    uid: str,
    *,
    client_id: str,
    redirect_uri: str,
    secret: str,
    now: float,
    scopes: list[str] | None = None,
    nonce: str | None = None,
) -> tuple[str, str]:
    """Google 同意画面 URL と署名 state を作る（refresh_token 取得のため offline）。

    nonce 未指定なら毎回ランダム生成（callback で単回化＝replay 防止・C4.9）。
    """
    if nonce is None:
        nonce = secrets.token_urlsafe(16)
    state = sign_state(uid, secret=secret, now=now, nonce=nonce)
    params = {
        "client_id": client_id,
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "scope": " ".join(_resolved_scopes(scopes)),
        "access_type": "offline",
        "include_granted_scopes": "true",
        "prompt": "consent",
        "state": state,
    }
    return f"{GOOGLE_AUTH_ENDPOINT}?{urlencode(params)}", state


@dataclass
class TokenExchangeResult:
    """code 交換の結果（保存用トークンJSON＋実際に付与されたスコープ）。"""

    token_json: str
    granted_scopes: list[str] = field(default_factory=list)


def exchange_code(
    code: str,
    *,
    client_id: str,
    client_secret: str,
    redirect_uri: str,
    scopes: list[str] | None = None,
) -> TokenExchangeResult:
    """認可コードをトークンに交換（実Google・ネットワーク）。テストでは差し替える。

    google-auth-oauthlib（`google` extra）を遅延 import。生トークン・code はここで完結し、
    呼び出し側へは保存用 JSON と granted scopes だけ返す（ログ出力しない）。
    """
    import os

    os.environ.setdefault("OAUTHLIB_RELAX_TOKEN_SCOPE", "1")
    from google_auth_oauthlib.flow import Flow

    resolved = _resolved_scopes(scopes)
    flow = Flow.from_client_config(
        {
            "web": {
                "client_id": client_id,
                "client_secret": client_secret,
                "auth_uri": GOOGLE_AUTH_ENDPOINT,
                "token_uri": GOOGLE_TOKEN_ENDPOINT,
                "redirect_uris": [redirect_uri],
            }
        },
        scopes=resolved,
        redirect_uri=redirect_uri,
    )
    flow.fetch_token(code=code)
    creds = flow.credentials
    granted = list(getattr(creds, "scopes", None) or resolved)
    return TokenExchangeResult(token_json=creds.to_json(), granted_scopes=granted)
