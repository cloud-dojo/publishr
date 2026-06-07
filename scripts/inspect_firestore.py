"""Firestore REST API 経由で各コレクションの中身を一覧する（読み取り専用）。

使い方:
  python scripts/inspect_firestore.py

実行前提:
  - gcloud auth application-default login 済みであること
"""

from __future__ import annotations

import json
import sys
import urllib.error
import urllib.request

PROJECT = "publishr-498123"
BASE_URL = f"https://firestore.googleapis.com/v1/projects/{PROJECT}/databases/(default)/documents"
COLLECTIONS = ["users", "books", "plans", "personas"]


def _get_token() -> str:
    import google.auth
    import google.auth.transport.requests

    scopes = ["https://www.googleapis.com/auth/cloud-platform"]
    creds, _ = google.auth.default(scopes=scopes)
    req = google.auth.transport.requests.Request()
    creds.refresh(req)
    return creds.token


def _unwrap(v: dict):
    if "stringValue" in v:
        return v["stringValue"]
    if "integerValue" in v:
        return int(v["integerValue"])
    if "booleanValue" in v:
        return v["booleanValue"]
    if "doubleValue" in v:
        return v["doubleValue"]
    if "nullValue" in v:
        return None
    if "arrayValue" in v:
        return [_unwrap(i) for i in v["arrayValue"].get("values", [])]
    if "mapValue" in v:
        return {k: _unwrap(val) for k, val in v["mapValue"].get("fields", {}).items()}
    return v


def _list(token: str, collection: str) -> list[dict]:
    docs: list[dict] = []
    page = ""
    while True:
        url = f"{BASE_URL}/{collection}?pageSize=300"
        if page:
            url += f"&pageToken={page}"
        req = urllib.request.Request(url, headers={"Authorization": f"Bearer {token}"})
        try:
            r = urllib.request.urlopen(req, timeout=20)
            data = json.loads(r.read().decode())
        except urllib.error.HTTPError as e:
            print(f"  ERROR {collection}: {e.code} {e.read().decode()[:200]}", file=sys.stderr)
            break
        for d in data.get("documents", []):
            doc_id = d["name"].rsplit("/", 1)[-1]
            fields = {k: _unwrap(v) for k, v in d.get("fields", {}).items()}
            docs.append({"id": doc_id, "fields": fields})
        page = data.get("nextPageToken", "")
        if not page:
            break
    return docs


def main() -> None:
    token = _get_token()
    for col in COLLECTIONS:
        docs = _list(token, col)
        print(f"\n=== {col} ({len(docs)} 件) ===")
        for d in docs:
            f = d["fields"]
            if col == "users":
                ip = f.get("initialProfile")
                print(f"  - {d['id']} | name={f.get('name')!r} initial={f.get('initial')!r} "
                      f"initialProfile={'set' if ip else ip} favoriteAuthors={len(f.get('favoriteAuthors') or [])}")
            elif col in ("books", "plans"):
                print(f"  - {d['id']} | ownerUid={f.get('ownerUid')!r} "
                      f"title={f.get('title') or f.get('tentativeTitle') or ''!r} status={f.get('status','')}")
            else:
                print(f"  - {d['id']} | name={f.get('name','')!r}")


if __name__ == "__main__":
    main()
