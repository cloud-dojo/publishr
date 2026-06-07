"""Firestore の特定ユーザーの name/initial を修正する（明示ハードコードのみ）。

seed で別ユーザーの fixture を上書きした名残（鉄田uidの name が「佐倉 美咲」）を
本人名へ直す。対象は下記1件のみ。それ以外は触らない。

使い方:
  python scripts/fix_user_name.py          # ドライラン（現在値を表示のみ）
  python scripts/fix_user_name.py --apply  # 実更新
"""

from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.request

PROJECT = "publishr-498123"
BASE_URL = f"https://firestore.googleapis.com/v1/projects/{PROJECT}/databases/(default)/documents"

# 対象（uid, 新しい name, 新しい initial）。ここに無いものは触らない。
UID = "5JLLGOc3rpXiGN9KXmsISBNAKty2"
NEW_NAME = "鉄田 陽介"
NEW_INITIAL = "鉄"


def _get_token() -> str:
    import google.auth
    import google.auth.transport.requests

    scopes = ["https://www.googleapis.com/auth/cloud-platform"]
    creds, _ = google.auth.default(scopes=scopes)
    req = google.auth.transport.requests.Request()
    creds.refresh(req)
    return creds.token


def _get(token: str) -> dict:
    url = f"{BASE_URL}/users/{UID}"
    req = urllib.request.Request(url, headers={"Authorization": f"Bearer {token}"})
    r = urllib.request.urlopen(req, timeout=15)
    return json.loads(r.read().decode())


def _patch_name(token: str) -> tuple[bool, object]:
    # updateMask で name/initial だけを更新（他フィールドは温存）。
    url = (
        f"{BASE_URL}/users/{UID}"
        "?updateMask.fieldPaths=name&updateMask.fieldPaths=initial"
    )
    body = json.dumps(
        {"fields": {"name": {"stringValue": NEW_NAME}, "initial": {"stringValue": NEW_INITIAL}}}
    ).encode()
    req = urllib.request.Request(
        url, data=body, method="PATCH",
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
    )
    try:
        r = urllib.request.urlopen(req, timeout=15)
        return True, r.status
    except urllib.error.HTTPError as e:
        return False, f"{e.code}: {e.read().decode()[:160]}"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true", help="実更新する（既定はドライラン）")
    args = parser.parse_args()
    token = _get_token()

    try:
        doc = _get(token)
    except urllib.error.HTTPError as e:
        print(f"ERROR: users/{UID} 取得失敗: {e.code}", file=sys.stderr)
        sys.exit(1)

    f = doc.get("fields", {})
    cur_name = f.get("name", {}).get("stringValue")
    cur_initial = f.get("initial", {}).get("stringValue")
    print(f"対象 users/{UID}")
    print(f"  現在: name={cur_name!r} initial={cur_initial!r}")
    print(f"  変更後: name={NEW_NAME!r} initial={NEW_INITIAL!r}")

    if args.apply:
        ok, status = _patch_name(token)
        print(f"  -> {'UPDATED' if ok else 'NG'}: {status}")
    else:
        print("\nドライラン完了。実更新は --apply を付けて再実行。")


if __name__ == "__main__":
    main()
