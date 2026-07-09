"""GcsBodyStore の実GCS ラウンドトリップ（C3.3 live・gated・実GCP）。

PUBLISHR_RUN_GOOGLE=1（＋ADC）でのみ実行。実バケットに put→get（読書導線が使うサーバ側read）を
試し、後始末でテストオブジェクトを消す。署名URLは ADC では署名鍵が無く失敗しうるため best-effort。
"""

from __future__ import annotations

import os

import pytest

from publishr_api.services.body_store import GcsBodyStore, _object_name

BUCKET = os.environ.get("PUBLISHR_BODY_BUCKET", "publishr-contents-498123")


@pytest.mark.google
@pytest.mark.skipif(
    os.environ.get("PUBLISHR_RUN_GOOGLE") != "1",
    reason="set PUBLISHR_RUN_GOOGLE=1 (＋ADC) for live GCS round-trip（実GCP）",
)
def test_gcs_put_get_roundtrip():
    store = GcsBodyStore(BUCKET)
    book_id = "test_c33_live_smoke"
    body = "# live smoke\n\n本文ラウンドトリップ検証（テスト用・後で削除）。"
    name = store.put(book_id, body)
    assert name == _object_name(book_id)
    try:
        assert store.get(book_id, name) == body  # サーバ側read（読書導線が使う経路）
        try:
            url = store.signed_url(book_id, name)
            print(f"\n[gcs live] signed_url ok: {url[:60]}...")
        except Exception as exc:  # noqa: BLE001 — ADC では SignBlob 権限が要る（reader は get を使う）
            print(f"\n[gcs live] signed_url skipped (ADC 署名不可): {type(exc).__name__}")
    finally:
        from google.cloud import storage  # noqa: PLC0415

        storage.Client().bucket(BUCKET).blob(name).delete()  # テストオブジェクト後始末
