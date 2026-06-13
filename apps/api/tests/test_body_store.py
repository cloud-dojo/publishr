"""本文ストア（C3.3）のオフライン単体テスト。

GcsBodyStore の実書込/署名は実GCP（課金）なので gated。ここは inline 既定・オブジェクト名
サニタイズ・ファクトリ分岐のみ（決定的・課金ゼロ）。
"""

from __future__ import annotations

from publishr_api.services.body_store import GcsBodyStore, _object_name, get_body_store


def test_object_name_is_per_book_under_books_prefix():
    assert _object_name("b_001") == "books/b_001/body.md"


def test_object_name_sanitizes_path_traversal():
    # book_id はデータ由来。'/' や '..' を含んでもバケット外/別パスへ書かせない。
    assert _object_name("../../etc/passwd") == "books/.._.._etc_passwd/body.md"


def test_get_body_store_inline_is_none(monkeypatch):
    from publishr_api import config

    monkeypatch.setattr(config.settings, "body_store", "inline")
    assert get_body_store() is None  # 既定＝オフロードしない


def test_get_body_store_gcs(monkeypatch):
    from publishr_api import config

    monkeypatch.setattr(config.settings, "body_store", "gcs")
    monkeypatch.setattr(config.settings, "body_bucket", "test-bucket")
    store = get_body_store()
    assert isinstance(store, GcsBodyStore)


def test_gcs_store_requires_bucket():
    try:
        GcsBodyStore("")
    except ValueError:
        pass
    else:
        raise AssertionError("空 bucket で ValueError を期待")
