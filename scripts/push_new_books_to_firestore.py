"""4テーマ新フロー（set_pipeline）でFirestoreに新book を生成・保存するスクリプト。

用途:
  - editor_chief_themes（新プロンプト）を実際に通した4冊をデモ用Firestoreに配置する
  - 本文（body）生成はスキップ（STEP0-4プレビューのみ・status=draft）
  - 既存の旧 b_* 本は別途削除（--delete-old で実行）

実行:
  uv run python -X utf8 scripts/push_new_books_to_firestore.py           # ドライラン
  uv run python -X utf8 scripts/push_new_books_to_firestore.py --apply   # Firestore書き込み
  uv run python -X utf8 scripts/push_new_books_to_firestore.py --apply --delete-old  # +旧削除
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone

# 環境変数をスクリプト先頭で設定（import 前に必要）
os.environ.setdefault("DATA_SOURCE", "firestore")
os.environ.setdefault("PUBLISHR_LLM", "vertex")
os.environ.setdefault("PUBLISHR_SET_PIPELINE", "true")
os.environ.setdefault("OBSERVE_SOURCE", "fixture")  # Google Drive接続不要
# ADK が Vertex AI を使うための設定（import 前に必須）
os.environ["GOOGLE_GENAI_USE_VERTEXAI"] = "TRUE"
os.environ.setdefault("GOOGLE_CLOUD_PROJECT", "publishr-498123")
os.environ.setdefault("GOOGLE_CLOUD_LOCATION", "asia-northeast1")

# 佐倉美咲の実Firebase UID
OWNER_UID = "5JLLGOc3rpXiGN9KXmsISBNAKty2"
FIXTURE_USER_ID = "u_sakura"
PROJECT = "publishr-498123"
BASE_URL = f"https://firestore.googleapis.com/v1/projects/{PROJECT}/databases/(default)/documents"

JST = timezone(datetime.now().astimezone().utcoffset())


def _get_token() -> str:
    import google.auth
    import google.auth.transport.requests

    creds, _ = google.auth.default(scopes=["https://www.googleapis.com/auth/cloud-platform"])
    creds.refresh(google.auth.transport.requests.Request())
    return creds.token


def _list_old_books(token: str) -> list[dict]:
    """保護対象外の旧 b_* 本を列挙する。"""
    docs, page = [], ""
    while True:
        url = f"{BASE_URL}/books?pageSize=300" + (f"&pageToken={page}" if page else "")
        req = urllib.request.Request(url, headers={"Authorization": f"Bearer {token}"})
        data = json.loads(urllib.request.urlopen(req, timeout=20).read())
        for d in data.get("documents", []):
            doc_id = d["name"].rsplit("/", 1)[-1]
            title = (d.get("fields", {}).get("title") or {}).get("stringValue", "")
            docs.append({"id": doc_id, "title": title})
        page = data.get("nextPageToken", "")
        if not page:
            break
    return [b for b in docs if b["id"].startswith("b_")]


def _delete(token: str, collection: str, doc_id: str) -> bool:
    req = urllib.request.Request(
        f"{BASE_URL}/{collection}/{doc_id}",
        method="DELETE",
        headers={"Authorization": f"Bearer {token}"},
    )
    try:
        urllib.request.urlopen(req, timeout=15)
        return True
    except urllib.error.HTTPError:
        return False


def _write_doc(token: str, collection: str, doc_id: str, fields: dict) -> bool:
    """Firestoreにドキュメントを作成/上書き（PATCH）。"""
    url = f"{BASE_URL}/{collection}/{doc_id}"
    body = json.dumps({"fields": fields}).encode()
    req = urllib.request.Request(
        url, data=body, method="PATCH",
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
    )
    try:
        urllib.request.urlopen(req, timeout=20)
        return True
    except urllib.error.HTTPError as e:
        print(f"  ERROR write {collection}/{doc_id}: {e.code} {e.read().decode()[:200]}")
        return False


def _sv(val: str) -> dict:
    return {"stringValue": val}


def _bv(val: bool) -> dict:
    return {"booleanValue": val}


def _iv(val: int) -> dict:
    return {"integerValue": str(val)}


def _av(items: list) -> dict:
    return {"arrayValue": {"values": items}}


def book_to_firestore_fields(book_data: dict, owner_uid: str, created_at: str) -> dict:
    """ModeABook / Book dict を Firestore フィールド形式に変換。"""
    fields: dict = {}
    str_fields = [
        "id", "planId", "status", "authorPersonaId", "title", "subtitle",
        "coverVariant", "coverUrl", "bodyUrl", "shelf", "prefaceSample", "kind", "deliveryReason",
        "problemToSolve", "coreMessage", "granularity",
    ]
    for f in str_fields:
        if book_data.get(f) is not None:
            fields[f] = _sv(str(book_data[f]))

    fields["ownerUid"] = _sv(owner_uid)
    fields["createdAt"] = _sv(created_at)

    if book_data.get("estimatedChapters") is not None:
        fields["estimatedChapters"] = _iv(int(book_data["estimatedChapters"]))
    if book_data.get("estimatedMinutes") is not None:
        fields["estimatedMinutes"] = _iv(int(book_data["estimatedMinutes"]))

    # agenda[] — AgendaItem マップ形式で保存（no/title/desc/locked）
    if book_data.get("agenda"):
        agenda_items = []
        for item in book_data["agenda"]:
            if isinstance(item, str):
                m = {"no": _sv(""), "title": _sv(item), "desc": _sv(""), "locked": _bv(False)}
            elif isinstance(item, dict):
                m = {
                    "no": _sv(str(item.get("no", ""))),
                    "title": _sv(str(item.get("title", ""))),
                    "desc": _sv(str(item.get("desc", ""))),
                    "locked": _bv(bool(item.get("locked", False))),
                }
                if item.get("note"):
                    m["note"] = _sv(str(item["note"]))
            else:
                continue
            agenda_items.append({"mapValue": {"fields": m}})
        fields["agenda"] = _av(agenda_items)

    # annotations[]
    fields["annotations"] = _av([])
    fields["feedback"] = {"mapValue": {"fields": {}}}

    return fields


def persona_to_firestore_fields(p: dict) -> dict:
    """Persona dict を Firestore フィールド形式に変換。"""
    fields: dict = {}
    for f in ["id", "name", "monogram", "style", "title", "voiceStyle", "format"]:
        if p.get(f):
            fields[f] = _sv(str(p[f]))
    # nameReading は Persona の required フィールド — 空でも必ず書く
    fields["nameReading"] = _sv(str(p.get("nameReading") or ""))
    if p.get("ephemeral") is not None:
        fields["ephemeral"] = _bv(bool(p["ephemeral"]))
    # persona サブオブジェクト
    if p.get("persona"):
        sub = p["persona"]
        sub_fields = {}
        for sf in ["career", "styleNote", "thought"]:
            if sub.get(sf):
                sub_fields[sf] = _sv(str(sub[sf]))
        if sub.get("signature"):
            sub_fields["signature"] = _av([_sv(s) for s in sub["signature"]])
        if sub.get("themes"):
            sub_fields["themes"] = _av([_sv(t) for t in sub["themes"]])
        fields["persona"] = {"mapValue": {"fields": sub_fields}}
    if p.get("expertise"):
        fields["expertise"] = _av([_sv(e) for e in p["expertise"]])
    if p.get("pastBooks"):
        fields["pastBooks"] = _av([_sv(b) for b in p["pastBooks"]])
    return fields


def run_set_pipeline() -> tuple[list[dict], list[dict]]:
    """4テーマ set pipeline を実行して (books, personas) を返す。"""
    from datetime import datetime, timezone

    from publishr_agents.mode_a import ModeASetResult, map_mode_a_set_to_books, run_mode_a_set_pipeline
    from publishr_agents.observe import FixtureObservationSource
    from publishr_schema import load_users

    # fixture の u_sakura プロファイルを使う（観測は fixture）
    users = {u.id: u for u in load_users()}
    user = users[FIXTURE_USER_ID]

    source = FixtureObservationSource()
    # 観測アンカー: fixture の役員報告が±14日窓内に入る基準日
    DEMO_NOW = datetime(2026, 6, 5, 9, 0, 0, tzinfo=timezone(datetime.now().astimezone().utcoffset()))

    print("== 4テーマ set pipeline 起動（vertex） ==")
    print(f"  user: {user.name} ({FIXTURE_USER_ID})")
    result: ModeASetResult = run_mode_a_set_pipeline(
        user,
        source=source,
        now=DEMO_NOW,
        reader_llm="vertex",
        llm="vertex",
        preview_llm="vertex",
        cover_llm="vertex",
        enable_imagen=True,
        theme_kind="honmei",
        threshold=70,
    )

    print(f"  生成完了: {len(result.books)} 冊（ModeABook）")
    for mb in result.books:
        title = mb.shelved[0].get("title", "?") if mb.shelved else mb.plan.theme
        print(f"    - {title}")

    # map_mode_a_set_to_books で Book / Persona Pydantic オブジェクトに変換
    created_at = datetime.now(timezone.utc).isoformat()
    today = datetime.now().strftime("%Y%m%d")
    books, personas = map_mode_a_set_to_books(result, owner_uid=OWNER_UID, created_at=created_at)

    # 新IDを採番（b_new_YYYYMMDD_A〜D）してステータスを draft に設定
    books_dicts = []
    for i, book in enumerate(books):
        bd = book.model_dump(by_alias=True)
        bd["id"] = f"b_new_{today}_{chr(65 + i)}"
        bd["status"] = "draft"
        books_dicts.append(bd)

    personas_dicts = [p.model_dump(by_alias=True) for p in personas]

    return books_dicts, personas_dicts


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true", help="実際にFirestoreへ書き込む（既定ドライラン）")
    parser.add_argument("--delete-old", action="store_true", help="旧 b_* 本を削除する")
    args = parser.parse_args()

    mode = "実行" if args.apply else "ドライラン"
    print(f"=== Firestore 新本配置（{mode}）===")

    token = _get_token()

    # 旧 b_* 一覧
    old_books = _list_old_books(token)
    print(f"\n旧 b_* 本: {len(old_books)} 件")
    for b in old_books:
        print(f"  - books/{b['id']}  \"{b['title'][:40]}\"")

    # 新本生成
    print("\n--- 4テーマ生成 ---")
    books, personas = run_set_pipeline()

    print(f"\n--- 書き込み対象: {len(books)} 冊 ---")
    for b in books:
        print(f"  + books/{b['id']}  \"{b.get('title', '?')[:50]}\"")

    if not args.apply:
        print(f"\nドライラン完了。実行は --apply を付けて再実行。")
        return

    # personas を先に書き込む
    print("\n--- personas 書き込み ---")
    for p in personas:
        pid = p.get("id", "")
        if pid:
            fields = persona_to_firestore_fields(p)
            ok = _write_doc(token, "personas", pid, fields)
            print(f"  {'OK' if ok else 'NG'} personas/{pid}")

    # books 書き込み
    print("\n--- books 書き込み ---")
    for b in books:
        bid = b["id"]
        fields = book_to_firestore_fields(b, OWNER_UID, b.get("createdAt", ""))
        ok = _write_doc(token, "books", bid, fields)
        print(f"  {'OK' if ok else 'NG'} books/{bid}  \"{b.get('title', '?')[:40]}\"")

    # 旧 b_* 削除（オプション）— 今回生成した新 ID は除外
    if args.delete_old:
        new_ids = {b["id"] for b in books}
        to_delete = [b for b in old_books if b["id"] not in new_ids]
        print(f"\n--- 旧 b_* 削除（{len(to_delete)} 件、新本 {len(new_ids)} 件は保護）---")
        for b in to_delete:
            ok = _delete(token, "books", b["id"])
            print(f"  {'DELETED' if ok else 'NG    '} books/{b['id']}")

    print("\n完了。")


if __name__ == "__main__":
    main()
