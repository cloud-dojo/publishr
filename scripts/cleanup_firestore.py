"""Firestore のテスト痕跡を限定削除する（明示ハードコードのみ・読み取り→削除）。

対象は下記3件のみ（ゴミ/レガシー）。それ以外は触らない。
  - books/b_kikitai   (ownerUid 無し・空ドキュメント)
  - books/b_ringi     (ownerUid 無し・空ドキュメント)
  - users/u_tadokoro  (レガシーの既定 seed ユーザー)

使い方:
  python scripts/cleanup_firestore.py          # ドライラン（対象の現在値を表示のみ）
  python scripts/cleanup_firestore.py --apply  # 実削除
"""

from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.request

PROJECT = "publishr-498123"
BASE_URL = f"https://firestore.googleapis.com/v1/projects/{PROJECT}/databases/(default)/documents"

# 削除対象（collection, docId）。ここに無いものは絶対に消さない。
TARGETS: list[tuple[str, str]] = [
    ("books", "b_kikitai"),
    ("books", "b_ringi"),
    ("users", "u_tadokoro"),
]


def _get_token() -> str:
    import google.auth
    import google.auth.transport.requests

    scopes = ["https://www.googleapis.com/auth/cloud-platform"]
    creds, _ = google.auth.default(scopes=scopes)
    req = google.auth.transport.requests.Request()
    creds.refresh(req)
    return creds.token


def _get_doc(token: str, collection: str, doc_id: str) -> tuple[bool, object]:
    url = f"{BASE_URL}/{collection}/{doc_id}"
    req = urllib.request.Request(url, headers={"Authorization": f"Bearer {token}"})
    try:
        r = urllib.request.urlopen(req, timeout=15)
        data = json.loads(r.read().decode())
        return True, list((data.get("fields") or {}).keys())
    except urllib.error.HTTPError as e:
        return False, f"{e.code}"


def _delete_doc(token: str, collection: str, doc_id: str) -> tuple[bool, object]:
    url = f"{BASE_URL}/{collection}/{doc_id}"
    req = urllib.request.Request(
        url, method="DELETE", headers={"Authorization": f"Bearer {token}"}
    )
    try:
        r = urllib.request.urlopen(req, timeout=15)
        return True, r.status
    except urllib.error.HTTPError as e:
        return False, f"{e.code}: {e.read().decode()[:120]}"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true", help="実削除する（既定はドライラン）")
    args = parser.parse_args()
    token = _get_token()

    print(f"対象 {len(TARGETS)} 件（{'実削除' if args.apply else 'ドライラン'}）")
    for col, doc_id in TARGETS:
        exists, info = _get_doc(token, col, doc_id)
        if not exists:
            print(f"  [skip] {col}/{doc_id}: 見つからない（{info}）")
            continue
        print(f"  [found] {col}/{doc_id}: fields={info}")
        if args.apply:
            ok, status = _delete_doc(token, col, doc_id)
            mark = "DELETED" if ok else "NG"
            print(f"     -> {mark}: {status}")

    if not args.apply:
        print("\nドライラン完了。実削除は --apply を付けて再実行。")
    else:
        print("\n削除完了。")


if __name__ == "__main__":
    main()
