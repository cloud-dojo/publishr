"""表紙ストア（cover_store）の単体テスト。実GCSには触れない。"""

from __future__ import annotations

from publishr_api import config
from publishr_api.services.cover_store import (
    GcsCoverStore,
    _object_name,
    get_cover_store,
)


def test_object_name_sanitizes_and_prefixes():
    assert _object_name("arr_20260617_p1") == "covers/arr_20260617_p1.png"
    # パストラバーサル防止: 英数 _ . - 以外は _ に置換
    assert _object_name("a/b/../c") == "covers/a_b_.._c.png"


def test_get_cover_store_returns_store_when_bucket_set(monkeypatch):
    monkeypatch.setattr(config.settings, "cover_bucket", "my-cover-bucket")
    store = get_cover_store()
    assert isinstance(store, GcsCoverStore)


def test_get_cover_store_none_when_bucket_empty(monkeypatch):
    monkeypatch.setattr(config.settings, "cover_bucket", "")
    assert get_cover_store() is None
