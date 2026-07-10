"""Firestore シードスクリプト（fixtures → Firestore コレクション）。

使い方:
  python scripts/seed_firestore.py                      # DRY-RUN（何も書き込まない・既定）
  python scripts/seed_firestore.py --apply              # 実書込（ownerUid = "u_sakura"）
  python scripts/seed_firestore.py --apply --owner-uid <uid>   # Firebase Auth UID に合わせる

実行前提:
  - GOOGLE_APPLICATION_CREDENTIALS 環境変数が有効なサービスアカウントキーを指すか、
    `gcloud auth application-default login` 済みであること。
  - firebase_admin がインストール済みであること（apps/api の deps に含まれる）。

安全策: 既定は DRY-RUN（書込ゼロ）。実書込は `--apply` を明示した時のみ。ADC の既定プロジェクトを
     そのまま対象にするため、引数なし実行での本番誤上書きを防ぐ。
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


def seed(owner_uid: str, apply: bool) -> None:
    # DRY-RUN では firebase 初期化も client 構築もしない（ADC 無しの誤実行でも安全に終わる）。
    db = None
    if apply:
        _init_firebase()
        import firebase_admin.firestore as fb_firestore  # noqa: PLC0415

        db = fb_firestore.client()
    mark = "書込" if apply else "DRY-RUN（書込なし）"

    # ------------------------------------------------------------------ books
    books = _load_json("books.json")
    col = db.collection("books") if apply else None
    for book in books:
        doc_id = book.get("id", book.get("bookId"))
        if not doc_id:
            print(f"  [WARN] book に id がありません: {book}", file=sys.stderr)
            continue
        book["ownerUid"] = owner_uid  # 所有者を上書き
        if apply:
            col.document(doc_id).set(book)
    print(f"✅ books: {len(books)} 件 {mark} (ownerUid={owner_uid!r})")

    # ------------------------------------------------------------------ plans
    plans = _load_json("plans.json")
    col = db.collection("plans") if apply else None
    for plan in plans:
        doc_id = plan.get("id", plan.get("planId"))
        if not doc_id:
            print(f"  [WARN] plan に id がありません: {plan}", file=sys.stderr)
            continue
        plan["ownerUid"] = owner_uid  # 所有者を上書き
        if apply:
            col.document(doc_id).set(plan)
    print(f"✅ plans: {len(plans)} 件 {mark} (ownerUid={owner_uid!r})")

    # --------------------------------------------------------------- personas
    personas = _load_json("personas.json")
    col = db.collection("personas") if apply else None
    for persona in personas:
        doc_id = persona.get("id", persona.get("personaId"))
        if not doc_id:
            print(f"  [WARN] persona に id がありません: {persona}", file=sys.stderr)
            continue
        if apply:
            col.document(doc_id).set(persona)
    print(f"✅ personas: {len(personas)} 件 {mark} (全ユーザー共有)")

    # ------------------------------------------------------------------ users
    users = _load_json("users.json")
    col = db.collection("users") if apply else None
    for user in users:
        # users のドキュメント ID は owner_uid に書き換える
        user["id"] = owner_uid
        if apply:
            col.document(owner_uid).set(user)
    print(f"✅ users: doc_id={owner_uid!r} で 1 件 {mark}")

    if apply:
        print("\n🎉 Firestore シード完了")
    else:
        print("\n🧪 DRY-RUN 完了（何も書き込んでいません）。実書込は --apply を付けて再実行。")


def main() -> None:
    parser = argparse.ArgumentParser(description="Firestore にフィクスチャデータを投入する")
    parser.add_argument(
        "--owner-uid",
        default="u_sakura",
        help="books/plans の ownerUid および users のドキュメント ID（デフォルト: u_sakura）",
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="実際に書き込む（既定は DRY-RUN で書込ゼロ）。本番誤上書き防止のフェイルセーフ。",
    )
    args = parser.parse_args()

    mode = "APPLY（実書込）" if args.apply else "DRY-RUN（書込なし）"
    print(f"🔥 Firestore シード開始 [{mode}] (owner_uid={args.owner_uid!r})")
    seed(args.owner_uid, args.apply)


if __name__ == "__main__":
    main()
