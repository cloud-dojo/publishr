"""OAuth refresh token の per-uid 保存。

既定 = FileTokenStore（observe と共有する `.secrets/oauth_tokens/{uid}.json`・gitignore 済・
ローカル/dev）。本番 = SecretManagerTokenStore（PUBLISHR_OAUTH_TOKEN_STORE=secret_manager・
遅延 import・実GCP）。生トークンはログに出さない。
"""

from __future__ import annotations

import hashlib
import os
from typing import Optional, Protocol

from publishr_agents.observe.google_source import per_uid_token_path


class TokenStore(Protocol):
    def save(self, uid: str, token_json: str) -> None: ...

    def load(self, uid: str) -> Optional[str]: ...


class FileTokenStore:
    """observe と同じ per-uid パスにトークンJSONを保存（ローカル/dev・既定）。"""

    def save(self, uid: str, token_json: str) -> None:
        path = per_uid_token_path(uid)
        path.parent.mkdir(parents=True, exist_ok=True)
        # O_CREAT のモード指定で最初から 0600（write→chmod の世界読み取り窓を作らない）。
        fd = os.open(str(path), os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
        try:
            os.write(fd, token_json.encode("utf-8"))
        finally:
            os.close(fd)

    def load(self, uid: str) -> Optional[str]:
        path = per_uid_token_path(uid)
        if not path.exists():
            return None
        return path.read_text(encoding="utf-8")


class SecretManagerTokenStore:
    """Secret Manager に per-uid トークンを保存（本番・実GCP・遅延 import）。"""

    def __init__(self, project: str) -> None:
        if not project:
            raise ValueError("SecretManagerTokenStore には project が必要です")
        self._project = project

    def _secret_id(self, uid: str) -> str:
        # サニタイズは衝突しうる（'a.b' と 'a-b' → 同一）ため、raw uid のハッシュを付けて
        # 一意性を担保する（別ユーザーのトークン上書き/誤読を防ぐ）。
        safe = "".join(c if c.isalnum() else "-" for c in uid)
        digest = hashlib.sha256(uid.encode("utf-8")).hexdigest()[:12]
        return f"google-oauth-{safe}-{digest}"

    def save(self, uid: str, token_json: str) -> None:
        from google.api_core.exceptions import AlreadyExists
        from google.cloud import secretmanager

        client = secretmanager.SecretManagerServiceClient()
        parent = f"projects/{self._project}"
        secret_id = self._secret_id(uid)
        try:
            client.create_secret(
                request={
                    "parent": parent,
                    "secret_id": secret_id,
                    "secret": {"replication": {"automatic": {}}},
                }
            )
        except AlreadyExists:
            pass
        client.add_secret_version(
            request={
                "parent": f"{parent}/secrets/{secret_id}",
                "payload": {"data": token_json.encode("utf-8")},
            }
        )

    def load(self, uid: str) -> Optional[str]:
        from google.api_core.exceptions import NotFound
        from google.cloud import secretmanager

        client = secretmanager.SecretManagerServiceClient()
        name = f"projects/{self._project}/secrets/{self._secret_id(uid)}/versions/latest"
        try:
            resp = client.access_secret_version(request={"name": name})
        except NotFound:
            return None  # 未保存＝未連携（権限/ネットワーク不全は握り潰さず伝播させる）
        return resp.payload.data.decode("utf-8")


def get_token_store() -> TokenStore:
    """設定に応じてトークンストアを返す（既定 file・本番 secret_manager）。"""
    from ..config import settings

    if settings.oauth_token_store == "secret_manager":
        return SecretManagerTokenStore(settings.secret_manager_project)
    return FileTokenStore()
