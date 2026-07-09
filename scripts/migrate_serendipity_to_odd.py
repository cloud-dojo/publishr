"""既存の serendipity 本の shelf を arrivals→odd に移行する一回きりの運用スクリプト。

背景: persist_mapping が serendipity を odd 棚に載せるよう修正した（本命=arrivals / セレンディピティ=odd）。
コード変更は新規生成本にしか効かないため、既に Firestore にある serendipity 本（shelf=arrivals）を
ここで odd に揃える。shelf フィールドのみ PATCH＝createdAt/body/feedback 等は一切触らない。冪等。

実行:
  uv run python scripts/migrate_serendipity_to_odd.py            # ドライラン（対象を表示のみ）
  uv run python scripts/migrate_serendipity_to_odd.py --apply    # Firestore に PATCH
"""

from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.request

PROJECT = "publishr-498123"
BFF_BASE = "https://publishr-api-24ru3hr7fq-an.a.run.app"
FS_BASE = f"https://firestore.googleapis.com/v1/projects/{PROJECT}/databases/(default)/documents"


def _get_token() -> str:
    import google.auth  # noqa: PLC0415
    import google.auth.transport.requests  # noqa: PLC0415

    creds, _ = google.auth.default(scopes=["https://www.googleapis.com/auth/cloud-platform"])
    creds.refresh(google.auth.transport.requests.Request())
    return creds.token


def _serendipity_arrivals() -> list[dict]:
    """公開棚から shelf=arrivals のままの serendipity 本を拾う（移行対象）。"""
    with urllib.request.urlopen(f"{BFF_BASE}/books?status=published", timeout=20) as r:
        books = json.loads(r.read().decode("utf-8"))
    return [b for b in books if b.get("kind") == "serendipity" and b.get("shelf") == "arrivals"]


def _patch_shelf_odd(token: str, book_id: str) -> tuple[bool, object]:
    url = f"{FS_BASE}/books/{book_id}?updateMask.fieldPaths=shelf"
    data = json.dumps({"fields": {"shelf": {"stringValue": "odd"}}}).encode("utf-8")
    req = urllib.request.Request(
        url, data=data, method="PATCH",
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return True, r.status
    except urllib.error.HTTPError as e:
        return False, f"{e.code}: {e.read().decode('utf-8', errors='replace')[:200]}"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true", help="実際に PATCH する（無指定はドライラン）")
    args = ap.parse_args()

    targets = _serendipity_arrivals()
    print(f"移行対象（serendipity かつ shelf=arrivals）: {len(targets)}冊")
    for b in targets:
        print(f"  {b['id']}  {b.get('title', '')[:30]}")
    if not targets:
        print("対象なし（すべて odd 済み）。")
        return
    if not args.apply:
        print("\n[ドライラン] --apply で Firestore に shelf=odd を PATCH します。")
        return

    token = _get_token()
    ok = 0
    for b in targets:
        success, info = _patch_shelf_odd(token, b["id"])
        print(f"  {'OK ' if success else 'NG '} {b['id']} -> {info}")
        ok += int(bool(success))
    print(f"\n完了: {ok}/{len(targets)} 冊を odd に移行。")
    if ok != len(targets):
        sys.exit(1)


if __name__ == "__main__":
    main()
