"""Firestore シードスクリプト（fixtures → Firestore コレクション）。

使い方:
  python scripts/seed_firestore.py                      # ownerUid = "u_tadokoro"
  python scripts/seed_firestore.py --owner-uid <uid>   # Firebase Auth UID に合わせる

実行前提:
  - GOOGLE_APPLICATION_CREDENTIALS 環境変数が有効なサービスアカウントキーを指すか、
    `gcloud auth application-default login` 済みであること。
  - firebase_admin がインストール済みであること（apps/api の deps に含まれる）。

冪等: ドキュメントは set() で上書きするため何度でも実行できる。
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "packages" / "shared-schema" / "fixtures"


def _init_firebase() -> None:
    import firebase_admin

    if not firebase_admin._apps:
        firebase_admin.initialize_app()


def _load_json(name: str) -> list[dict]:
    path = FIXTURES / name
    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    return data if isinstance(data, list) else [data]


def seed(owner_uid: str) -> None:
    _init_firebase()

    import firebase_admin.firestore as fb_firestore  # noqa: PLC0415

    db = fb_firestore.client()

    # ------------------------------------------------------------------ books
    books = _load_json("books.json")
    col = db.collection("books")
    for book in books:
        doc_id = book.get("id", book.get("bookId"))
        if not doc_id:
            print(f"  [WARN] book に id がありません: {book}", file=sys.stderr)
            continue
        book["ownerUid"] = owner_uid  # 所有者を上書き
        col.document(doc_id).set(book)
    print(f"✅ books: {len(books)} 件 (ownerUid={owner_uid!r})")

    # ------------------------------------------------------------------ plans
    plans = _load_json("plans.json")
    col = db.collection("plans")
    for plan in plans:
        doc_id = plan.get("id", plan.get("planId"))
        if not doc_id:
            print(f"  [WARN] plan に id がありません: {plan}", file=sys.stderr)
            continue
        plan["ownerUid"] = owner_uid  # 所有者を上書き
        col.document(doc_id).set(plan)
    print(f"✅ plans: {len(plans)} 件 (ownerUid={owner_uid!r})")

    # --------------------------------------------------------------- personas
    personas = _load_json("personas.json")
    col = db.collection("personas")
    for persona in personas:
        doc_id = persona.get("id", persona.get("personaId"))
        if not doc_id:
            print(f"  [WARN] persona に id がありません: {persona}", file=sys.stderr)
            continue
        col.document(doc_id).set(persona)
    print(f"✅ personas: {len(personas)} 件 (全ユーザー共有)")

    # ------------------------------------------------------------------ users
    users = _load_json("users.json")
    col = db.collection("users")
    for user in users:
        # users のドキュメント ID は owner_uid に書き換える
        user["id"] = owner_uid
        col.document(owner_uid).set(user)
    print(f"✅ users: doc_id={owner_uid!r} で 1 件")

    print("\n🎉 Firestore シード完了")


def main() -> None:
    parser = argparse.ArgumentParser(description="Firestore にフィクスチャデータを投入する")
    parser.add_argument(
        "--owner-uid",
        default="u_tadokoro",
        help="books/plans の ownerUid および users のドキュメント ID（デフォルト: u_tadokoro）",
    )
    args = parser.parse_args()

    print(f"🔥 Firestore シード開始 (owner_uid={args.owner_uid!r})")
    seed(args.owner_uid)


if __name__ == "__main__":
    main()
