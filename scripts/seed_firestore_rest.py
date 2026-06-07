"""Firestore REST API 経由でフィクスチャデータを投入するスクリプト。

gRPC の Windows SSL 問題を回避するため、HTTPS REST API を直接使用する。
ADC（Application Default Credentials）から gcloud アクセストークンを取得する。

使い方:
  python scripts/seed_firestore_rest.py                      # ownerUid = "u_tadokoro"
  python scripts/seed_firestore_rest.py --owner-uid <uid>   # Firebase Auth UID に合わせる

実行前提:
  - gcloud auth application-default login 済みであること
  - packages/shared-schema/fixtures/ に books.json, plans.json, personas.json, users.json があること

冪等: ドキュメントは PATCH で上書きするため何度でも実行できる。
"""

from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "packages" / "shared-schema" / "fixtures"
PROJECT = "publishr-498123"
BASE_URL = f"https://firestore.googleapis.com/v1/projects/{PROJECT}/databases/(default)/documents"


def _get_token() -> str:
    """ADC アクセストークンを google-auth ライブラリ経由で取得する。
    gRPC を使わず urllib（HTTPS REST）のみを使うため Windows 環境でも動作する。
    """
    try:
        import google.auth
        import google.auth.transport.requests

        scopes = ["https://www.googleapis.com/auth/cloud-platform"]
        creds, _ = google.auth.default(scopes=scopes)
        req = google.auth.transport.requests.Request()
        creds.refresh(req)
        return creds.token
    except Exception as exc:
        print(f"ERROR: ADC トークン取得に失敗しました: {exc}", file=sys.stderr)
        print("       gcloud auth application-default login を実行してください。", file=sys.stderr)
        sys.exit(1)


def _load_json(name: str) -> list[dict]:
    path = FIXTURES / name
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    return data if isinstance(data, list) else [data]


def _to_fs_value(v: object) -> dict:
    """Python 値を Firestore REST 値フォーマットに変換する。"""
    if isinstance(v, bool):
        return {"booleanValue": v}
    if isinstance(v, int):
        return {"integerValue": str(v)}
    if isinstance(v, float):
        return {"doubleValue": v}
    if isinstance(v, str):
        return {"stringValue": v}
    if v is None:
        return {"nullValue": None}
    if isinstance(v, list):
        return {"arrayValue": {"values": [_to_fs_value(i) for i in v]}}
    if isinstance(v, dict):
        return {"mapValue": {"fields": {k: _to_fs_value(val) for k, val in v.items()}}}
    return {"stringValue": str(v)}


def _put_doc(token: str, collection: str, doc_id: str, data: dict) -> tuple[bool, object]:
    fields = {k: _to_fs_value(v) for k, v in data.items()}
    url = f"{BASE_URL}/{collection}/{doc_id}"
    body = json.dumps({"fields": fields}).encode()
    req = urllib.request.Request(
        url, data=body, method="PATCH",
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }
    )
    try:
        r = urllib.request.urlopen(req, timeout=15)
        return True, r.status
    except urllib.error.HTTPError as e:
        return False, f"{e.code}: {e.read().decode()[:120]}"


def seed(owner_uid: str) -> None:
    token = _get_token()

    # --- books ---
    books = _load_json("books.json")
    for book in books:
        doc_id = book.get("id") or book.get("bookId", "")
        book["ownerUid"] = owner_uid
        ok, status = _put_doc(token, "books", doc_id, book)
        mark = "OK" if ok else "NG"
        print(f"  [{mark}] books/{doc_id}: {status}")
    print(f"books: {len(books)} 件 (ownerUid={owner_uid!r})")

    # --- plans ---
    plans = _load_json("plans.json")
    for plan in plans:
        doc_id = plan.get("id") or plan.get("planId", "")
        plan["ownerUid"] = owner_uid
        ok, status = _put_doc(token, "plans", doc_id, plan)
        mark = "OK" if ok else "NG"
        print(f"  [{mark}] plans/{doc_id}: {status}")
    print(f"plans: {len(plans)} 件 (ownerUid={owner_uid!r})")

    # --- personas (全ユーザー共有) ---
    personas = _load_json("personas.json")
    for persona in personas:
        doc_id = persona.get("id") or persona.get("personaId", "")
        ok, status = _put_doc(token, "personas", doc_id, persona)
        mark = "OK" if ok else "NG"
        print(f"  [{mark}] personas/{doc_id}: {status}")
    print(f"personas: {len(personas)} 件 (全ユーザー共有)")

    # --- users (doc_id = owner_uid) ---
    users = _load_json("users.json")
    for user in users:
        user["id"] = owner_uid
        ok, status = _put_doc(token, "users", owner_uid, user)
        mark = "OK" if ok else "NG"
        print(f"  [{mark}] users/{owner_uid}: {status}")
    print(f"users: doc_id={owner_uid!r} で 1 件")

    print("\nFirestore seed 完了")


def main() -> None:
    parser = argparse.ArgumentParser(description="Firestore に fixtures データを REST API で投入する")
    parser.add_argument(
        "--owner-uid",
        default="u_tadokoro",
        help="books/plans の ownerUid および users のドキュメント ID（デフォルト: u_tadokoro）",
    )
    args = parser.parse_args()

    print(f"Firestore seed 開始 (owner_uid={args.owner_uid!r})")
    seed(args.owner_uid)


if __name__ == "__main__":
    main()
