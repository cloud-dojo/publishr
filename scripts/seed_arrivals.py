"""C4結線: モードA で生成した新刊5冊＋著者を書店「入荷(arrivals)」へ投入する。

  uv run python -m scripts.seed_arrivals --owner-uid <uid>            # ドライラン（投入内容のみ表示）
  uv run python -m scripts.seed_arrivals --owner-uid <uid> --apply    # 実投入（DATA_SOURCE で mock/firestore）
  DATA_SOURCE=firestore uv run python -m scripts.seed_arrivals --owner-uid <uid> --apply   # 実Firestoreへ

パイプラインは mock 既定＝LLM課金ゼロ。Book は shelf=arrivals/status=draft/ownerUid付き・
ID は `arr_<personaId>`（冪等上書き・既存 b_*/_sakura 非破壊）。著者は personas へ upsert。
前提（firestore時）: gcloud auth application-default login 済み。
"""

from __future__ import annotations

import argparse
import os
from datetime import datetime, timedelta, timezone

from publishr_schema import load_users

from publishr_agents.persist_mapping import map_mode_a_to_books, persist_arrivals

JST = timezone(timedelta(hours=9))
DEMO_NOW = datetime(2026, 6, 3, 6, 0, tzinfo=JST)
# 佐倉 美咲 の Firebase Auth UID（seed_sakura_library.py と同一）。
SAKURA_UID = "WW1j4mkYC0VzuzDdQ0OQ4Ff8zFd2"


def _ensure_vertex_env() -> None:
    os.environ.setdefault("GOOGLE_GENAI_USE_VERTEXAI", "TRUE")
    os.environ.setdefault("GOOGLE_CLOUD_PROJECT", "publishr-498123")
    os.environ.setdefault("GOOGLE_CLOUD_LOCATION", "asia-northeast1")


def _build_repo(apply: bool, owner_uid: str):
    """--apply かつ DATA_SOURCE=firestore のときだけ実Firestore。それ以外は mock。"""
    if apply and os.environ.get("DATA_SOURCE", "mock").lower() == "firestore":
        from publishr_api.repositories.firestore_repository import FirestoreRepository

        return FirestoreRepository(owner_uid=owner_uid), "firestore"
    from publishr_api.repositories.mock_repository import MockRepository

    return MockRepository(), "mock"


def _generate(user, *, theme, theme_kind: str, llm: str, limit, threshold: int, enable_imagen: bool, now):
    from publishr_agents.observe import FixtureObservationSource
    from publishr_agents.mode_a import run_mode_a_pipeline

    result = run_mode_a_pipeline(
        user,
        source=FixtureObservationSource(),
        now=now,
        reader_llm=llm,
        llm=llm,
        preview_llm=llm,
        cover_llm=llm,
        enable_imagen=enable_imagen,
        theme=theme,
        theme_kind=theme_kind,
        threshold=threshold,
        limit=limit,
    )
    return result.plan, result.shelved, result.personas


def _generate_set(user, *, theme_kind: str, llm: str, threshold: int, enable_imagen: bool, now, owner_uid: str):
    """4テーマ1-1-1-1のセット縦串（既定）→ (Book[], Persona[], headerラベル) を返す。"""
    from publishr_agents.observe import FixtureObservationSource
    from publishr_agents.mode_a import run_mode_a_set_pipeline, map_mode_a_set_to_books

    res = run_mode_a_set_pipeline(
        user,
        source=FixtureObservationSource(),
        now=now,
        reader_llm=llm,
        llm=llm,
        preview_llm=llm,
        cover_llm=llm,
        enable_imagen=enable_imagen,
        theme_kind=theme_kind,
        threshold=threshold,
    )
    books, personas = map_mode_a_set_to_books(
        res, owner_uid=owner_uid, created_at=datetime.now(JST).isoformat()
    )
    pv = res.planning.get("planSetVerdict") or {}
    header = f"4テーマ・1-1-1-1（セットゲート {pv.get('decision')}・総合{pv.get('score')}・{res.planning.get('rounds')}R）"
    return books, personas, header


def main() -> int:
    parser = argparse.ArgumentParser(description="C4: モードA新刊を arrivals へ投入")
    parser.add_argument("--user", default="u_sakura")
    parser.add_argument("--owner-uid", default=SAKURA_UID, help="本の所有 Firebase Auth UID")
    parser.add_argument("--llm", default="mock", choices=["mock", "vertex"], help="既定mock＝課金ゼロ")
    parser.add_argument("--theme", default=None, help="仮テーマ（--legacy 時のみ・省略時は導出）")
    parser.add_argument("--theme-kind", default="honmei", choices=["honmei", "serendipity"])
    parser.add_argument("--threshold", type=int, default=70)
    parser.add_argument("--limit", type=int, default=None, help="冊数上限（--legacy 時のみ）")
    parser.add_argument("--legacy", action="store_true", help="旧・単一テーマで投入（既定は4テーマ・1-1-1-1セット）")
    parser.add_argument("--enable-imagen", action="store_true")
    parser.add_argument("--now", default=None)
    parser.add_argument("--apply", action="store_true", help="実際に upsert（無いとドライラン）")
    args = parser.parse_args()

    user = next((u for u in load_users() if u.id == args.user), None)
    if user is None:
        raise SystemExit(f"ユーザーが見つかりません: {args.user}")
    if args.llm == "vertex" or args.enable_imagen:
        _ensure_vertex_env()

    now = datetime.fromisoformat(args.now) if args.now else DEMO_NOW
    if args.legacy:
        plan, shelved, personas = _generate(
            user, theme=args.theme, theme_kind=args.theme_kind, llm=args.llm, limit=args.limit,
            threshold=args.threshold, enable_imagen=args.enable_imagen, now=now,
        )
        books, mapped_personas = map_mode_a_to_books(
            plan, shelved, personas, owner_uid=args.owner_uid, created_at=datetime.now(JST).isoformat()
        )
        header = f"旧・単一テーマ「{plan.tentative_title}」"
    else:
        books, mapped_personas, header = _generate_set(
            user, theme_kind=args.theme_kind, llm=args.llm, threshold=args.threshold,
            enable_imagen=args.enable_imagen, now=now, owner_uid=args.owner_uid,
        )

    print(f"== arrivals 投入プレビュー（owner={args.owner_uid} llm={args.llm} themeKind={args.theme_kind}）==")
    print(f"配本: {header}")
    for b in books:
        author = next((p.name for p in mapped_personas if p.id == b.author_persona_id), "?")
        cover = b.cover_url or f"CSS:{b.cover_variant}"
        print(f"  ◆ {b.id}  {b.title}  / 著者={author} / {cover}")
        print(f"      入荷理由: {b.delivery_reason[:60]}")

    if not args.apply:
        print("\n(ドライラン) --apply で実投入。DATA_SOURCE=firestore なら実Firestoreへ。")
        return 0

    repo, backend = _build_repo(apply=True, owner_uid=args.owner_uid)
    n = persist_arrivals(repo, books, mapped_personas)
    print(f"\n✅ {backend} に {n} 冊＋著者 {len(mapped_personas)} 名 を投入（arrivals/draft・owner={args.owner_uid}）")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
