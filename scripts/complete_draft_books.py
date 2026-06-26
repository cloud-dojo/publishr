"""本文未生成のまま取り残された本（draft/reserved/writing かつ body 空）を本文生成→published に
仕上げる手動再実行導線（incident-vertex-quota-writing-stuck §7-1/§7-4）。

本番ランタイムと同じ env で動かすこと（DATA_SOURCE=firestore / PUBLISHR_LLM=vertex /
PUBLISHR_BODY_STORE=gcs / PUBLISHR_BODY_BUCKET=... / PUBLISHR_BODY_EDIT_ROUNDS=1 等）。
各本は本番の執筆コードパス（reserve_now → process_write_job → _persist_published）をそのまま通すので、
推定分量・序文サンプル・body_store(GCS)退避まで通常配本と同一になる。

既定はドライラン（候補列挙のみ・無課金・無変更）。実書き込みは --apply。対象は --ids で限定するか
--all で候補全件。実Vertex課金が発生するため --apply は対象を明示すること。
"""

from __future__ import annotations

import argparse
import os
import sys

# WSL/社内CA 環境での Vertex TLS 用（uv run --with truststore 推奨）。無ければ無視。
try:  # noqa: SIM105
    import truststore  # type: ignore

    truststore.inject_into_ssl()
except Exception:  # noqa: BLE001
    pass


def _repo():
    from publishr_api.config import settings
    from publishr_api.repositories.firestore_repository import FirestoreRepository

    if settings.data_source != "firestore":
        sys.exit(f"DATA_SOURCE=firestore が必要（現在: {settings.data_source!r}）。本番envで実行のこと。")
    return FirestoreRepository()


def _has_body(book) -> bool:
    return bool(getattr(book, "body", "")) or bool(getattr(book, "body_url", None))


def _candidates(repo):
    """draft/reserved/writing かつ body 空＝本文未完成で取り残された本。"""
    out = []
    for status in ("draft", "reserved", "writing"):
        for b in repo.list_books(status=status):
            if not _has_body(b):
                out.append(b)
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true", help="実際に本文生成→published 書き込み（既定ドライラン）")
    ap.add_argument("--ids", default="", help="対象 book ID をカンマ区切りで限定")
    ap.add_argument("--all", action="store_true", help="候補全件を対象にする（--ids 未指定時）")
    args = ap.parse_args()

    from publishr_api.config import settings
    from publishr_api.services import reservation_service

    repo = _repo()
    print(f"== complete_draft_books（{'APPLY' if args.apply else 'DRY-RUN'}）==")
    print(
        f"   llm={settings.publishr_llm} rounds={settings.body_edit_rounds} "
        f"body_store={settings.body_store} project={os.environ.get('GOOGLE_CLOUD_PROJECT')}"
    )

    want = {s.strip() for s in args.ids.split(",") if s.strip()}
    if want:
        books = [b for bid in want if (b := repo.get_book(bid)) is not None]
        missing = want - {b.id for b in books}
        if missing:
            print(f"   ⚠ 見つからない ID: {sorted(missing)}")
    else:
        books = _candidates(repo)

    # 既に本文付き/published は対象外（冪等）。
    targets = [b for b in books if b.status != "published" and not _has_body(b)]
    print(f"\n対象 {len(targets)} 冊:")
    for b in targets:
        persona = repo.get_persona(b.author_persona_id) if b.author_persona_id else None
        print(
            f"  - {b.id}  status={b.status!r}  owner={b.owner_uid!r}  "
            f"persona={'OK' if persona else 'MISSING:'+str(b.author_persona_id)}"
        )
        print(f"      title={b.title[:48]!r}")

    if not targets:
        print("対象なし。")
        return
    if not args.apply:
        if not want and not args.all:
            print("\nドライラン。実行は対象を --ids で限定し --apply、または候補全件なら --all --apply。")
        else:
            print("\nドライラン完了。実行は --apply を付与。")
        return
    if not want and not args.all:
        sys.exit("安全のため --apply には --ids か --all が必要です。")

    print("\n--- 本文生成→published（実Vertex・本番書き込み）---")
    ok, ng = 0, 0
    for b in targets:
        try:
            if b.status == "draft":
                reservation_service.reserve_now(repo, b.id, owner_uid=b.owner_uid or "")
            result = reservation_service.process_write_job(repo, b.id)
            done = result is not None and result.status == "published" and _has_body(result)
            print(f"  {'OK ' if done else 'NG '} {b.id}  -> status={getattr(result,'status',None)!r}")
            ok += 1 if done else 0
            ng += 0 if done else 1
        except Exception as exc:  # noqa: BLE001
            ng += 1
            print(f"  ERR {b.id}: {type(exc).__name__}: {exc}")
    print(f"\n完了: OK={ok} NG={ng}")


if __name__ == "__main__":
    main()
