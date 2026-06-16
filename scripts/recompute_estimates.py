"""published 本の推定分量/序文サンプルを実本文から再計算して Firestore を更新する保守スクリプト。

背景: #53 で `_persist_published` が本文から `estimated_chapters`/`estimated_minutes`/
`preface_sample` を算出するようになったが、それ以前に published 化した本（例: arr_p1〜p4 は
旧 agenda ベースの「6章×8分=48分」のまま・序文も本文と不一致）は古い推定が残る。本スクリプトは
`reservation_service` と同じロジックで再計算し、差分のある本だけ更新する。

- 既定は **dry-run（読み取りのみ）**。`--apply` で実更新。
- 破壊的操作は行わない（既存フィールドの値更新のみ・削除/drop 無し）。
- 対象は既定で **`arr_*`（パイプライン生成の入荷本）のみ**。`b_*` 等の手設定デモ seed は
  意図的な推定値（例: 180分）なので触らない。`--all` で published 全件を対象にできる。
- GCS 退避本文（bodyUrl）はサーバ側 read で取得。

使い方（要 ADC: `gcloud auth application-default login`）:
  DATA_SOURCE=firestore GOOGLE_CLOUD_PROJECT=publishr-498123 \
  PUBLISHR_BODY_STORE=gcs PUBLISHR_BODY_BUCKET=publishr-contents-498123 \
    uv run python scripts/recompute_estimates.py [--apply] [--all]
"""

from __future__ import annotations

import sys

from publishr_api.repositories.firestore_repository import FirestoreRepository
from publishr_api.services.body_store import get_body_store
from publishr_api.services.reservation_service import (
    _body_chapter_count,
    _body_preface,
    _reading_minutes,
)


def main() -> int:
    apply = "--apply" in sys.argv
    only_arrivals = "--all" not in sys.argv
    repo = FirestoreRepository(owner_uid="")  # published 全件（owner 問わず）
    store = get_body_store()

    books = repo.list_books(status="published")
    if only_arrivals:
        # 手設定デモ seed（b_*）には触れず、パイプライン生成の入荷本のみ対象。
        books = [b for b in books if b.id.startswith("arr_")]
    changed = 0
    for b in sorted(books, key=lambda x: x.id):
        body = b.body or ((store.get(b.id, b.body_url) or "") if (store and b.body_url) else "")
        if not body:
            print(f"  skip {b.id}: 本文取得不可（body/bodyUrl 無し）")
            continue

        ch = _body_chapter_count(body)
        mins = _reading_minutes(body)
        pre = _body_preface(body)

        updates: dict = {}
        if ch and ch != b.estimated_chapters:
            updates["estimated_chapters"] = ch
        if mins and mins != b.estimated_minutes:
            updates["estimated_minutes"] = mins
        if pre and pre != b.preface_sample:
            updates["preface_sample"] = pre

        if not updates:
            print(f"  ok   {b.id}: ch={b.estimated_chapters} min={b.estimated_minutes}（一致）")
            continue

        changed += 1
        print(
            f"  DIFF {b.id}: "
            f"ch {b.estimated_chapters}->{updates.get('estimated_chapters', b.estimated_chapters)} "
            f"min {b.estimated_minutes}->{updates.get('estimated_minutes', b.estimated_minutes)} "
            f"preface={'更新' if 'preface_sample' in updates else '据置'}"
            f"（本文{len(body)}字）"
        )
        if apply:
            repo.upsert_book(b.model_copy(update=updates))

    print(f"\n{'APPLIED' if apply else 'DRY-RUN'}: {changed} 冊が要更新 / published {len(books)} 冊")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
