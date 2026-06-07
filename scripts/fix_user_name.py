"""Firestore の特定ユーザーの name/initial を修正する。

seed で別ユーザーの fixture を上書きした名残（例: 鉄田uidの name が「佐倉 美咲」）や
オンボーディングのみで name 未設定のアカウントを、本人名へ直す。
name/initial 以外のフィールドは updateMask で温存する。

使い方:
  python scripts/fix_user_name.py --uid <UID> --name "鉄田 陽介" --initial 鉄            # ドライラン
  python scripts/fix_user_name.py --uid <UID> --name "鉄田 陽介" --initial 鉄 --apply    # 実更新
"""

from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.request

PROJECT = "publishr-498123"
BASE_URL = f"https://firestore.googleapis.com/v1/projects/{PROJECT}/databases/(default)/documents"


def _get_token() -> str:
    import google.auth
    import google.auth.transport.requests

    scopes = ["https://www.googleapis.com/auth/cloud-platform"]
    creds, _ = google.auth.default(scopes=scopes)
    req = google.auth.transport.requests.Request()
    creds.refresh(req)
    return creds.token


def _get(token: str, uid: str) -> dict:
    url = f"{BASE_URL}/users/{uid}"
    req = urllib.request.Request(url, headers={"Authorization": f"Bearer {token}"})
    r = urllib.request.urlopen(req, timeout=15)
    return json.loads(r.read().decode())


def _patch_name(token: str, uid: str, name: str, initial: str) -> tuple[bool, object]:
    # updateMask で name/initial だけを更新（他フィールドは温存）。
    url = (
        f"{BASE_URL}/users/{uid}"
        "?updateMask.fieldPaths=name&updateMask.fieldPaths=initial"
    )
    body = json.dumps(
        {"fields": {"name": {"stringValue": name}, "initial": {"stringValue": initial}}}
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
    parser.add_argument("--uid", required=True, help="対象ユーザーの Firebase Auth UID")
    parser.add_argument("--name", required=True, help="設定する name")
    parser.add_argument("--initial", required=True, help="設定する initial（1文字）")
    parser.add_argument("--apply", action="store_true", help="実更新する（既定はドライラン）")
    args = parser.parse_args()
    token = _get_token()

    try:
        doc = _get(token, args.uid)
    except urllib.error.HTTPError as e:
        print(f"ERROR: users/{args.uid} 取得失敗: {e.code}", file=sys.stderr)
        sys.exit(1)

    f = doc.get("fields", {})
    cur_name = f.get("name", {}).get("stringValue")
    cur_initial = f.get("initial", {}).get("stringValue")
    print(f"対象 users/{args.uid}")
    print(f"  現在: name={cur_name!r} initial={cur_initial!r}")
    print(f"  変更後: name={args.name!r} initial={args.initial!r}")

    if args.apply:
        ok, status = _patch_name(token, args.uid, args.name, args.initial)
        print(f"  -> {'UPDATED' if ok else 'NG'}: {status}")
    else:
        print("\nドライラン完了。実更新は --apply を付けて再実行。")


if __name__ == "__main__":
    main()
