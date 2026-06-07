"""特定ユーザー(既定=佐倉 WW1j4)所有の蔵書データを Firestore に投入する（非破壊・新規ID複製）。

ローカルUI検証用に作った「100ページ級」本文（apps/web/src/data/sampleLibrary.ts の
SAMPLE_BODIES）と、fixtures/books.json + EXTRA_LIBRARY_BOOKS のメタを使い、
`<origId>_sakura` という新IDで owner 所有の本を複製する。既存の b_* は一切触らない。

使い方:
  python -X utf8 scripts/seed_sakura_library.py            # ドライラン（対象一覧のみ）
  python -X utf8 scripts/seed_sakura_library.py --apply    # 実投入
  python -X utf8 scripts/seed_sakura_library.py --owner-uid <uid> --apply

前提: gcloud auth application-default login 済み。
冪等: PATCH で上書きするため何度でも実行可。createdAt は実行時刻基準で再計算。
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "packages" / "shared-schema" / "fixtures" / "books.json"
SAMPLE_LIBRARY = ROOT / "apps" / "web" / "src" / "data" / "sampleLibrary.ts"
PROJECT = "publishr-498123"
BASE_URL = f"https://firestore.googleapis.com/v1/projects/{PROJECT}/databases/(default)/documents"
SAKURA_UID = "WW1j4mkYC0VzuzDdQ0OQ4Ff8zFd2"
ID_SUFFIX = "_sakura"
DAY = 86_400  # 秒

# EXTRA_LIBRARY_BOOKS（sampleLibrary.ts 由来・b_ringi / b_kikitai のメタ）を直書き。
EXTRA_BOOKS: list[dict] = [
    {
        "id": "b_ringi", "planId": "plan_makase", "status": "published", "authorPersonaId": "p_yuki",
        "title": "決裁が速い組織", "subtitle": "意思決定の設計図", "coverVariant": "wine", "coverUrl": None,
        "shelf": "library", "estimatedChapters": 4, "estimatedMinutes": 120, "granularity": "full",
        "prefaceSample": "決められないのは情報不足ではない。決め方が、決まっていないからだ。",
        "agenda": [
            {"no": "第1章", "title": "速さは設計できる", "desc": "誰が・何を・いつまでに。決め方を先に設計する", "locked": False},
            {"no": "第2章", "title": "任せる範囲を線で引く", "desc": "三層モデルで権限を明確化。任せる覚悟を持つ", "locked": False},
            {"no": "第3章", "title": "失敗を許容する装置", "desc": "安全に失敗できる設計が、挑戦の土台になる", "locked": False},
            {"no": "第4章", "title": "決めきる文化", "desc": "決めきるリーダーの周りに、決めきる人が育つ", "locked": False},
        ],
        "body": None,
        "annotations": [
            {"id": "ann_ringi_seed1", "kind": "highlight", "paragraphIndex": 1,
             "text": "「全員の合意」を待つほど、決定は誰のものでもなくなる。", "note": None},
        ],
        "feedback": {"readPercent": 45, "dropped": False, "rating": None, "wantsSequel": False},
        "deliveryReason": "決め方が決まっていない組織に、意思決定の設計図を。",
    },
    {
        "id": "b_kikitai", "planId": "plan_toi", "status": "published", "authorPersonaId": "p_aoi",
        "title": "聞いてから、伝える", "subtitle": "関係を壊さない対話の作法", "coverVariant": "sand", "coverUrl": None,
        "shelf": "library", "estimatedChapters": 4, "estimatedMinutes": 120, "granularity": "full",
        "prefaceSample": "人は、十分に聞いてもらえたと感じて初めて、相手の言葉を受け取れる。",
        "agenda": [
            {"no": "第1章", "title": "聞く技術は、伝える技術", "desc": "傾聴が、伝える力の土台になる理由", "locked": False},
            {"no": "第2章", "title": "叱らずに伝える", "desc": "事実と解釈を分け、人格でなく行動を語る", "locked": False},
            {"no": "第3章", "title": "フィードバックの順番", "desc": "何を言うかより、いつ・どの順で言うかが効く", "locked": False},
            {"no": "第4章", "title": "関係を資産にする", "desc": "聞いて、受け取って、返す。この往復が関係を育てる", "locked": False},
        ],
        "body": None,
        "annotations": [],
        "feedback": {"readPercent": 0, "dropped": False, "rating": None, "wantsSequel": False},
        "deliveryReason": "伝える前に、聞く。関係を壊さない対話の作法を一冊に。",
    },
]


def _get_token() -> str:
    try:
        import google.auth
        import google.auth.transport.requests

        creds, _ = google.auth.default(scopes=["https://www.googleapis.com/auth/cloud-platform"])
        req = google.auth.transport.requests.Request()
        creds.refresh(req)
        return creds.token
    except Exception as exc:
        print(f"ERROR: ADC トークン取得に失敗: {exc}", file=sys.stderr)
        print("       gcloud auth application-default login を実行してください。", file=sys.stderr)
        sys.exit(1)


def _extract_sample_bodies() -> dict[str, str]:
    """sampleLibrary.ts の SAMPLE_BODIES を抽出（patch_book_bodies.py と同方式）。"""
    content = SAMPLE_LIBRARY.read_text(encoding="utf-8")
    m = re.search(r"export const SAMPLE_BODIES[^{]*\{(.*?)\n\};", content, re.DOTALL)
    if not m:
        raise ValueError("SAMPLE_BODIES が見つかりません")
    entries = re.findall(r"  (\w+):\s*`(.*?)`", m.group(1), re.DOTALL)
    return {key: body.strip() for key, body in entries}


def _to_fs_value(v: object) -> dict:
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


def _put_doc(token: str, doc_id: str, data: dict) -> tuple[bool, object]:
    url = f"{BASE_URL}/books/{doc_id}"
    body = json.dumps({"fields": {k: _to_fs_value(v) for k, v in data.items()}}).encode()
    req = urllib.request.Request(
        url, data=body, method="PATCH",
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
    )
    try:
        r = urllib.request.urlopen(req, timeout=30)
        return True, r.status
    except urllib.error.HTTPError as e:
        return False, f"{e.code}: {e.read().decode('utf-8', errors='replace')[:160]}"


def _iso(epoch: float) -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%S.000Z", time.gmtime(epoch))


def build_books(owner_uid: str) -> list[dict]:
    fixtures = json.loads(FIXTURES.read_text(encoding="utf-8"))
    bodies = _extract_sample_bodies()
    now = time.time()
    out: list[dict] = []
    draft_i = 0
    for src in [*fixtures, *EXTRA_BOOKS]:
        b = dict(src)  # コピー
        orig = b["id"]
        b["id"] = f"{orig}{ID_SUFFIX}"
        b["ownerUid"] = owner_uid
        # 本文：SAMPLE_BODIES があれば差し替え（蔵書6冊）。
        if orig in bodies:
            b["body"] = bodies[orig]
        # createdAt：published は古め、draft/writing は直近7日内に散らして書店トップに出す。
        if b.get("status") == "published":
            b["createdAt"] = _iso(now - 30 * DAY)
        else:
            b["createdAt"] = _iso(now - (draft_i % 6) * DAY)
            draft_i += 1
        out.append(b)
    return out


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--owner-uid", default=SAKURA_UID, help="所有者UID（既定=佐倉）")
    parser.add_argument("--apply", action="store_true", help="実投入（既定はドライラン）")
    args = parser.parse_args()

    books = build_books(args.owner_uid)
    print(f"複製対象 {len(books)} 冊 → ownerUid={args.owner_uid!r}（{'実投入' if args.apply else 'ドライラン'}）")
    token = _get_token() if args.apply else None
    ok = 0
    for b in books:
        body_len = len(b.get("body") or "")
        line = f"  books/{b['id']}  [{b['status']}/{b['shelf']}] body={body_len:,}字"
        if args.apply:
            done, status = _put_doc(token, b["id"], b)
            print(f"  [{'OK' if done else 'NG'}]{line}  -> {status}")
            ok += 1 if done else 0
        else:
            print(line)

    if args.apply:
        print(f"\n投入完了: {ok}/{len(books)} 件成功")
        if ok < len(books):
            sys.exit(1)
    else:
        print("\nドライラン完了。実投入は --apply を付けて再実行。")


if __name__ == "__main__":
    main()
