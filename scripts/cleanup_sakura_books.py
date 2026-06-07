"""seed_sakura_library.py で WW1j4 に作った `*_sakura` 本を削除する（限定・安全）。

二重ガード: 「id が _sakura で終わる」かつ「ownerUid が指定owner（既定 WW1j4）」の
books ドキュメントだけを削除する。それ以外は絶対に触らない。

使い方:
  python -X utf8 scripts/cleanup_sakura_books.py            # ドライラン（対象一覧のみ）
  python -X utf8 scripts/cleanup_sakura_books.py --apply    # 実削除
"""

from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.request

PROJECT = "publishr-498123"
BASE_URL = f"https://firestore.googleapis.com/v1/projects/{PROJECT}/databases/(default)/documents"
OWNER = "WW1j4mkYC0VzuzDdQ0OQ4Ff8zFd2"
SUFFIX = "_sakura"


def _get_token() -> str:
    import google.auth
    import google.auth.transport.requests

    creds, _ = google.auth.default(scopes=["https://www.googleapis.com/auth/cloud-platform"])
    creds.refresh(google.auth.transport.requests.Request())
    return creds.token


def _list_books(token: str) -> list[dict]:
    docs, page = [], ""
    while True:
        url = f"{BASE_URL}/books?pageSize=300" + (f"&pageToken={page}" if page else "")
        req = urllib.request.Request(url, headers={"Authorization": f"Bearer {token}"})
        data = json.loads(urllib.request.urlopen(req, timeout=20).read())
        for d in data.get("documents", []):
            doc_id = d["name"].rsplit("/", 1)[-1]
            owner = d.get("fields", {}).get("ownerUid", {}).get("stringValue")
            docs.append({"id": doc_id, "owner": owner})
        page = data.get("nextPageToken", "")
        if not page:
            break
    return docs


def _delete(token: str, doc_id: str) -> tuple[bool, object]:
    req = urllib.request.Request(
        f"{BASE_URL}/books/{doc_id}", method="DELETE",
        headers={"Authorization": f"Bearer {token}"},
    )
    try:
        r = urllib.request.urlopen(req, timeout=15)
        return True, r.status
    except urllib.error.HTTPError as e:
        return False, f"{e.code}: {e.read().decode()[:120]}"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true", help="実削除（既定はドライラン）")
    parser.add_argument("--owner", default=OWNER)
    args = parser.parse_args()
    token = _get_token()

    # 二重ガード: _sakura で終わる かつ owner 一致 のみ
    targets = [b for b in _list_books(token) if b["id"].endswith(SUFFIX) and b["owner"] == args.owner]
    print(f"削除対象 {len(targets)} 件（owner={args.owner!r}・suffix={SUFFIX!r}・{'実削除' if args.apply else 'ドライラン'}）")
    ok = 0
    for b in targets:
        if args.apply:
            done, status = _delete(token, b["id"])
            print(f"  [{'DELETED' if done else 'NG'}] books/{b['id']} -> {status}")
            ok += 1 if done else 0
        else:
            print(f"  books/{b['id']}")
    if args.apply:
        print(f"\n削除完了: {ok}/{len(targets)} 件")
    else:
        print("\nドライラン完了。実削除は --apply を付けて再実行。")


if __name__ == "__main__":
    main()
