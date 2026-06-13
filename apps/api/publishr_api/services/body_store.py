"""モードB本文(body)の保存先抽象（C3.3・GCSオフロード＋署名URL/IAM保護）。

既定 = inline（`get_body_store()` が None＝オフロードしない）: 本文を books ドキュメントに
そのまま持つ（mock/dev・課金ゼロ・従来挙動）。
本番 = gcs（PUBLISHR_BODY_STORE=gcs）: 本文を **非公開** バケットへ退避し、Firestore の books
には `bodyUrl`（オブジェクトパス）だけ残す（ドキュメント肥大防止）。

本文の保護方針:
  - バケットは非公開（公開アクセス無し）。読出は所有者チェック済みAPIがサーバ側 read（`get`）で
    返す＝GCSオブジェクトを外部に晒さない（最も強い保護）。
  - 直接ダウンロードが要る場合のみ、都度 `signed_url`（短命・V4署名）を発行する（保存はしない＝
    失効/漏洩に強い）。

google-cloud-storage は gcs 選択時のみ必要（遅延 import）。生本文はログに出さない。
"""

from __future__ import annotations

import re
from typing import Optional, Protocol


def _object_name(book_id: str) -> str:
    """book_id から退避オブジェクト名。book_id はデータ由来＝パストラバーサル防止にサニタイズ。"""
    safe = re.sub(r"[^A-Za-z0-9_.-]", "_", book_id)
    return f"books/{safe}/body.md"


class BodyStore(Protocol):
    def put(self, book_id: str, body: str) -> str: ...

    def get(self, book_id: str, body_url: str) -> Optional[str]: ...

    def signed_url(self, book_id: str, body_url: str) -> Optional[str]: ...


class GcsBodyStore:
    """非公開 GCS バケットに本文MDを退避（本番・実GCP・遅延 import・課金あり）。"""

    def __init__(self, bucket: str, *, signed_url_ttl_sec: int = 900) -> None:
        if not bucket:
            raise ValueError("GcsBodyStore には bucket が必要です")
        self._bucket = bucket
        self._ttl = signed_url_ttl_sec

    def _blob(self, name: str):
        from google.cloud import storage  # noqa: PLC0415

        client = storage.Client()
        return client.bucket(self._bucket).blob(name)

    def put(self, book_id: str, body: str) -> str:
        name = _object_name(book_id)
        self._blob(name).upload_from_string(
            body, content_type="text/markdown; charset=utf-8"
        )
        # bodyUrl にはオブジェクトパスを格納（署名URLは都度発行＝期限切れ/漏洩に強い）。
        return name

    def get(self, book_id: str, body_url: str) -> Optional[str]:
        from google.api_core.exceptions import NotFound  # noqa: PLC0415

        name = body_url or _object_name(book_id)
        try:
            return self._blob(name).download_as_text()
        except NotFound:
            return None  # 未退避（権限/ネットワーク不全は握り潰さず伝播させる）

    def signed_url(self, book_id: str, body_url: str) -> Optional[str]:
        from datetime import timedelta  # noqa: PLC0415

        name = body_url or _object_name(book_id)
        return self._blob(name).generate_signed_url(
            version="v4", expiration=timedelta(seconds=self._ttl), method="GET"
        )


def get_body_store() -> Optional[BodyStore]:
    """設定に応じた本文ストア。inline（既定）は None＝オフロードせず body をそのまま持つ。"""
    from ..config import settings  # noqa: PLC0415

    if settings.body_store == "gcs":
        return GcsBodyStore(
            settings.body_bucket, signed_url_ttl_sec=settings.body_signed_url_ttl_sec
        )
    return None
