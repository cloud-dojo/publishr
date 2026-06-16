"""表紙画像(Imagen)の保存先抽象（本文C3.3 body_store と同方針・GCSオフロード＋IAM保護）。

ENABLE_IMAGEN=true のとき `agents/cover/imagen.py` が非公開 GCS バケットへ PNG を退避し、
Firestore の books には `coverUrl`（object パス `covers/...png`）だけを残す。

保護方針（本文と同じ）:
  - バケットは非公開（公開アクセス無し）。`<img>` から直接 GCS を引かせず、BFF の
    `/api/books/{id}/cover` がサーバ側 read（`get_bytes`）して画像バイトを返す。
  - 表紙は機微情報ではない（書影アート）ため所有者チェックは課さない＝認証ヘッダを送れない
    `<img src>` から読める。生成失敗時は coverUrl=None に縮退（CSSバリアントへ）。

google-cloud-storage は gcs 退避時のみ必要（遅延 import）。
"""

from __future__ import annotations

import re
from typing import Optional


def _object_name(book_id: str) -> str:
    """coverUrl 未指定時のフォールバック object 名。book_id はサニタイズ（パストラバーサル防止）。"""
    safe = re.sub(r"[^A-Za-z0-9_.-]", "_", book_id)
    return f"covers/{safe}.png"


class GcsCoverStore:
    """非公開 GCS バケットから表紙PNGをサーバ側 read（本番・実GCP・遅延 import）。"""

    def __init__(self, bucket: str) -> None:
        if not bucket:
            raise ValueError("GcsCoverStore には bucket が必要です")
        self._bucket = bucket

    def _blob(self, name: str):
        from google.cloud import storage  # noqa: PLC0415

        client = storage.Client()
        return client.bucket(self._bucket).blob(name)

    def get_bytes(self, book_id: str, cover_url: str) -> Optional[bytes]:
        from google.api_core.exceptions import NotFound  # noqa: PLC0415

        # coverUrl は imagen が返した object パス（covers/...png）。未指定時のみ規約名でフォールバック。
        name = cover_url or _object_name(book_id)
        try:
            return self._blob(name).download_as_bytes()
        except NotFound:
            return None  # 未退避（権限/ネットワーク不全は握り潰さず伝播させる）


def get_cover_store() -> Optional[GcsCoverStore]:
    """設定に応じた表紙ストア。cover_bucket 未設定なら None＝配信不可（CSSバリアントのまま）。"""
    from ..config import settings  # noqa: PLC0415

    if settings.cover_bucket:
        return GcsCoverStore(settings.cover_bucket)
    return None
