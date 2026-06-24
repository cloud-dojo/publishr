"""全 arr_* テスト本と生成 persona を Firestore から削除する（二重ガード）。

削除対象:
  books    : ID が "arr_" で始まるもの全件（旧形式 arr_p1〜p4 + 新形式 arr_YYYYMMDD_* 含む）
  personas : p_* 固定フィクスチャ以外の生成 persona（タイムスタンク付き + 旧 p1〜p5）
             具体的には ID が "p_" で始まらないもの（p1,p2,p3,p4,p5 + 20260617... 等）

保護されるもの:
  - b_* books（手動デモ本）
  - plan_* plans
  - p_* personas（p_kirishima, p_azumi 等のフィクスチャ著者）
  - users コレクション

使い方:
  python -X utf8 scripts/cleanup_arr_books.py                      # ドライラン
  python -X utf8 scripts/cleanup_arr_books.py --apply              # books のみ実削除
  python -X utf8 scripts/cleanup_arr_books.py --with-personas --apply  # books + personas 実削除
"""

from __future__ import annotations

import argparse
import json
import urllib.error
import urllib.request

PROJECT = "publishr-498123"
BASE_URL = f"https://firestore.googleapis.com/v1/projects/{PROJECT}/databases/(default)/documents"


def _get_token() -> str:
    import google.auth
    import google.auth.transport.requests

    creds, _ = google.auth.default(scopes=["https://www.googleapis.com/auth/cloud-platform"])
    creds.refresh(google.auth.transport.requests.Request())
    return creds.token


def _list_collection(token: str, collection: str) -> list[dict]:
    docs, page = [], ""
    while True:
        url = f"{BASE_URL}/{collection}?pageSize=300" + (f"&pageToken={page}" if page else "")
        req = urllib.request.Request(url, headers={"Authorization": f"Bearer {token}"})
        try:
            data = json.loads(urllib.request.urlopen(req, timeout=20).read())
        except urllib.error.HTTPError as e:
            print(f"  ERROR {collection}: {e.code}")
            break
        for d in data.get("documents", []):
            doc_id = d["name"].rsplit("/", 1)[-1]
            fields = d.get("fields", {})
            owner = fields.get("ownerUid", {}).get("stringValue")
            title = (fields.get("title") or fields.get("name") or {}).get("stringValue", "")
            docs.append({"id": doc_id, "owner": owner, "title": title})
        page = data.get("nextPageToken", "")
        if not page:
            break
    return docs


def _delete(token: str, collection: str, doc_id: str) -> tuple[bool, object]:
    req = urllib.request.Request(
        f"{BASE_URL}/{collection}/{doc_id}", method="DELETE",
        headers={"Authorization": f"Bearer {token}"},
    )
    try:
        r = urllib.request.urlopen(req, timeout=15)
        return True, r.status
    except urllib.error.HTTPError as e:
        return False, f"{e.code}: {e.read().decode()[:120]}"


def _is_generated_persona(doc_id: str) -> bool:
    """p_* 固定フィクスチャ以外の生成 persona か判定。"""
    return not doc_id.startswith("p_")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true", help="実削除（既定はドライラン）")
    parser.add_argument("--with-personas", action="store_true", help="生成 persona も合わせて削除する")
    args = parser.parse_args()

    token = _get_token()

    # books: arr_* 全件
    all_books = _list_collection(token, "books")
    target_books = [b for b in all_books if b["id"].startswith("arr_")]

    # personas: p_* フィクスチャ以外（--with-personas 時のみ）
    target_personas: list[dict] = []
    if args.with_personas:
        all_personas = _list_collection(token, "personas")
        target_personas = [p for p in all_personas if _is_generated_persona(p["id"])]

    mode = "実削除" if args.apply else "ドライラン"
    print(f"=== arr テスト本クリーンアップ（{mode}）===")
    print(f"books 対象: {len(target_books)} 件  / 保護: {len(all_books) - len(target_books)} 件")
    if args.with_personas:
        print(f"personas 対象: {len(target_personas)} 件  / 保護(p_*): {len(all_personas) - len(target_personas)} 件")

    ok = 0
    print("\n--- books ---")
    for b in target_books:
        if args.apply:
            done, status = _delete(token, "books", b["id"])
            mark = "DELETED" if done else "NG    "
            print(f"  [{mark}] books/{b['id']}  \"{b['title'][:40]}\"")
            ok += 1 if done else 0
        else:
            print(f"  books/{b['id']}  \"{b['title'][:50]}\"")

    if args.with_personas:
        print("\n--- personas ---")
        for p in target_personas:
            if args.apply:
                done, status = _delete(token, "personas", p["id"])
                mark = "DELETED" if done else "NG    "
                print(f"  [{mark}] personas/{p['id']}  {p['title']!r}")
                ok += 1 if done else 0
            else:
                print(f"  personas/{p['id']}  {p['title']!r}")

    total = len(target_books) + len(target_personas)
    if args.apply:
        print(f"\n削除完了: {ok}/{total} 件")
    else:
        print(f"\nドライラン完了。実削除は --apply を付けて再実行。")
        print("  books のみ:           python -X utf8 scripts/cleanup_arr_books.py --apply")
        print("  books + personas:     python -X utf8 scripts/cleanup_arr_books.py --with-personas --apply")


if __name__ == "__main__":
    main()
