"""
sampleLibrary.ts の SAMPLE_BODIES を Firestore books コレクションに PATCH する。

Firestore モードでは MockProvider のマージが走らないため、
本文（body フィールド）が null のまま読書ページが空になる問題を修正する。

使い方:
  python scripts/patch_book_bodies.py            # DRY-RUN（何も書き込まない・既定）
  python scripts/patch_book_bodies.py --apply    # 実 PATCH

実行前提:
  - gcloud auth application-default login 済みであること
  - Firestore に対象の books ドキュメントが既に存在すること（seed 済み）

冪等: updateMask.fieldPaths=body で body フィールドのみを上書きするため
     何度でも安全に実行できる。
安全策:
  - 既定は DRY-RUN（書込ゼロ）。実 PATCH は `--apply` を明示した時のみ。対象は本番
    publishr-498123 固定のため、引数なし実行での誤上書きを防ぐ。
  - Firestore に存在する book だけに PATCH する（存在しない id への PATCH は upsert で
    body だけの孤児ドキュメントを作るため、必ずスキップする）。
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SAMPLE_LIBRARY = ROOT / "apps" / "web" / "src" / "data" / "sampleLibrary.ts"
PROJECT = "publishr-498123"
BASE_URL = (
    f"https://firestore.googleapis.com/v1/projects/{PROJECT}/databases/(default)/documents"
)


def _get_token() -> str:
    """ADC アクセストークンを google-auth ライブラリ経由で取得する。"""
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
        print(
            "       gcloud auth application-default login を実行してください。",
            file=sys.stderr,
        )
        sys.exit(1)


def _extract_sample_bodies() -> dict[str, str]:
    """sampleLibrary.ts の SAMPLE_BODIES を正規表現で抽出する。"""
    content = SAMPLE_LIBRARY.read_text(encoding="utf-8")

    # SAMPLE_BODIES オブジェクト全体を取り出す
    m = re.search(
        r"export const SAMPLE_BODIES[^{]*\{(.*?)\n\};",
        content,
        re.DOTALL,
    )
    if not m:
        raise ValueError(
            f"SAMPLE_BODIES が見つかりません: {SAMPLE_LIBRARY}"
        )

    bodies_str = m.group(1)

    # 各エントリ (key: `value`) を取り出す
    # テンプレートリテラル内にバッククォートは含まれない前提
    entries = re.findall(r"  (\w+):\s*`(.*?)`", bodies_str, re.DOTALL)
    if not entries:
        raise ValueError("SAMPLE_BODIES のエントリが 0 件でした")

    return {key: body.strip() for key, body in entries}


def _doc_exists(token: str, book_id: str) -> bool:
    """books/{book_id} が Firestore に存在するか（GET 200 か）。"""
    url = f"{BASE_URL}/books/{book_id}"
    req = urllib.request.Request(url, headers={"Authorization": f"Bearer {token}"})
    try:
        urllib.request.urlopen(req, timeout=15)
        return True
    except urllib.error.HTTPError as e:
        if e.code == 404:
            return False
        raise


def _patch_body(token: str, book_id: str, body_text: str) -> tuple[bool, object]:
    """books/{book_id} の body フィールドのみを PATCH する。"""
    url = f"{BASE_URL}/books/{book_id}?updateMask.fieldPaths=body"
    payload = {
        "fields": {
            "body": {"stringValue": body_text},
        }
    }
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=data,
        method="PATCH",
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        },
    )
    try:
        r = urllib.request.urlopen(req, timeout=30)
        return True, r.status
    except urllib.error.HTTPError as e:
        return False, f"{e.code}: {e.read().decode('utf-8', errors='replace')[:200]}"


def main() -> None:
    parser = argparse.ArgumentParser(
        description="sampleLibrary.ts の SAMPLE_BODIES を Firestore books に PATCH する"
    )
    parser.add_argument(
        "--apply",
        action="store_true",
        help="実際に PATCH する（既定は DRY-RUN で書込ゼロ）。本番誤上書き防止のフェイルセーフ。",
    )
    args = parser.parse_args()

    mode = "APPLY（実 PATCH）" if args.apply else "DRY-RUN（書込なし）"
    print(f"[{mode}] project={PROJECT}")
    print(f"sampleLibrary.ts から SAMPLE_BODIES を抽出中: {SAMPLE_LIBRARY}")
    bodies = _extract_sample_bodies()
    book_ids = list(bodies.keys())
    print(f"  {len(bodies)} 件のエントリを検出: {book_ids}")

    if not args.apply:
        # DRY-RUN: トークン取得も存在チェックもしない（ADC 無しの誤実行でも安全に終わる）。
        print("  [DRY-RUN] 存在する book の body を PATCH 対象にします（書込なし）。")
        for book_id in book_ids:
            print(f"  [DRY-RUN] books/{book_id} を PATCH予定")
        print("\nDRY-RUN 完了（何も書き込んでいません）。実 PATCH は --apply を付けて再実行。")
        return

    print("ADC トークンを取得中...")
    token = _get_token()

    print("Firestore books コレクションに body を PATCH 中...")
    # 既存の book だけに PATCH する。存在しない id（mock専用の EXTRA_LIBRARY_BOOKS 等）に
    # PATCH すると upsert で body だけの孤児ドキュメントが生まれるため、必ずスキップする。
    ok_count = 0
    skipped: list[str] = []
    targets = {k: v for k, v in bodies.items() if _doc_exists(token, k)}
    for book_id in bodies:
        if book_id not in targets:
            skipped.append(book_id)
    for book_id, body_text in targets.items():
        ok, status = _patch_body(token, book_id, body_text)
        mark = "OK" if ok else "NG"
        char_count = len(body_text)
        print(f"  [{mark}] books/{book_id}: {status}  ({char_count:,} chars)")
        if ok:
            ok_count += 1

    if skipped:
        print(f"  [skip] Firestore未存在のためスキップ: {skipped}")
    print(f"\n完了: {ok_count}/{len(targets)} 件成功（対象 {len(bodies)} 中 {len(skipped)} 件スキップ）")
    if ok_count < len(targets):
        print("NG があります。対象ドキュメントの状態を確認してください。")
        sys.exit(1)


if __name__ == "__main__":
    main()
