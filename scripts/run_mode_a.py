"""モードA 完全縦串 実行CLI（STEP0観測→1読者→2企画→3著者→4プレビュー→5装丁）。

  uv run python -m scripts.run_mode_a --user u_sakura                                  # 全mock（オフライン・棚5冊＋CSS装丁）
  uv run python -m scripts.run_mode_a --user u_sakura --cover-llm vertex --enable-imagen --limit 2  # 装丁だけ実Flash+Imagen 2冊
  uv run python -m scripts.run_mode_a --user u_sakura --reader-llm vertex --llm vertex --preview-llm vertex --cover-llm vertex --enable-imagen  # 全実LLM

段階別LLM切替（コスト制御）: --reader-llm=STEP1 / --llm=STEP2企画+STEP3著者 / --preview-llm=STEP4 / --cover-llm=STEP5。
--enable-imagen で実Imagen画像生成（画像課金）。mock は課金なし。
"""

from __future__ import annotations

import argparse
import json
import os
from datetime import datetime, timedelta, timezone

from publishr_schema import load_users

JST = timezone(timedelta(hours=9))
DEMO_NOW = datetime(2026, 6, 3, 6, 0, tzinfo=JST)


def _ensure_vertex_env() -> None:
    os.environ.setdefault("GOOGLE_GENAI_USE_VERTEXAI", "TRUE")
    os.environ.setdefault("GOOGLE_CLOUD_PROJECT", "publishr-498123")
    os.environ.setdefault("GOOGLE_CLOUD_LOCATION", "asia-northeast1")


def _resolve_now(now_arg: str | None, source: str) -> datetime:
    if now_arg:
        s = now_arg[:-1] + "+00:00" if now_arg.endswith("Z") else now_arg
        dt = datetime.fromisoformat(s)
        return dt if dt.tzinfo else dt.replace(tzinfo=JST)
    return datetime.now(JST) if source == "google" else DEMO_NOW


def _build_source(source: str):
    if source == "fixture":
        from publishr_agents.observe import FixtureObservationSource

        return FixtureObservationSource()
    if source == "google":
        from publishr_agents.observe.google_source import GoogleObservationSource

        return GoogleObservationSource()
    raise SystemExit(f"unknown --source={source!r}（fixture|google）")


def _run_mode_a(user, *, source, now, reader_llm, llm, preview_llm, cover_llm, enable_imagen, theme, threshold, limit):
    from publishr_agents.mode_a import run_mode_a_pipeline

    result = run_mode_a_pipeline(
        user,
        source=source,
        now=now,
        reader_llm=reader_llm,
        llm=llm,
        preview_llm=preview_llm,
        cover_llm=cover_llm,
        enable_imagen=enable_imagen,
        theme=theme,
        threshold=threshold,
        limit=limit,
    )
    return result.plan, result.shelved


def _run_mode_a_set(user, *, source, now, reader_llm, llm, preview_llm, cover_llm, enable_imagen, theme_kind, threshold):
    """4テーマ1-1-1-1のセット縦串（予約制廃止改定 2026-06-23・既定）。"""
    from publishr_agents.mode_a import run_mode_a_set_pipeline

    return run_mode_a_set_pipeline(
        user,
        source=source,
        now=now,
        reader_llm=reader_llm,
        llm=llm,
        preview_llm=preview_llm,
        cover_llm=cover_llm,
        enable_imagen=enable_imagen,
        theme_kind=theme_kind,
        threshold=threshold,
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="モードA 完全縦串（STEP0→5）")
    parser.add_argument("--user", default="u_sakura")
    parser.add_argument("--source", default="fixture", choices=["fixture", "google"])
    parser.add_argument("--reader-llm", default="mock", choices=["mock", "vertex"])
    parser.add_argument("--llm", default="mock", choices=["mock", "vertex"], help="STEP2企画+STEP3著者")
    parser.add_argument("--preview-llm", default="mock", choices=["mock", "vertex"])
    parser.add_argument("--cover-llm", default="mock", choices=["mock", "vertex"])
    parser.add_argument("--enable-imagen", action="store_true", help="実Imagen画像生成（画像課金）")
    parser.add_argument("--theme", default=None, help="旧・単一テーマ用の仮テーマ（--legacy 時のみ）")
    parser.add_argument("--theme-kind", default="honmei", choices=["honmei", "serendipity"])
    parser.add_argument("--threshold", type=int, default=70)
    parser.add_argument("--limit", type=int, default=None, help="旧・単一テーマ用の冊数上限（--legacy 時のみ）")
    parser.add_argument("--legacy", action="store_true", help="旧・単一テーマ縦串で走る（既定は4テーマ・1-1-1-1セット）")
    parser.add_argument("--now", default=None)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    user = next((u for u in load_users() if u.id == args.user), None)
    if user is None:
        raise SystemExit(f"ユーザーが見つかりません: {args.user}")
    if "vertex" in (args.reader_llm, args.llm, args.preview_llm, args.cover_llm) or args.enable_imagen:
        _ensure_vertex_env()

    now = _resolve_now(args.now, args.source)
    source = _build_source(args.source)

    mode_label = "旧・単一テーマ" if args.legacy else "4テーマ・1-1-1-1セット"
    print(
        f"== モードA STEP0→5（{mode_label}・user={user.id} reader={args.reader_llm} plan/cast={args.llm} "
        f"preview={args.preview_llm} cover={args.cover_llm} imagen={args.enable_imagen}）=="
    )

    if args.legacy:
        plan, shelved = _run_mode_a(
            user, source=source, now=now, reader_llm=args.reader_llm, llm=args.llm,
            preview_llm=args.preview_llm, cover_llm=args.cover_llm, enable_imagen=args.enable_imagen,
            theme=args.theme, threshold=args.threshold, limit=args.limit,
        )
        if args.json:
            print(json.dumps(shelved, ensure_ascii=False, indent=2))
            return 0
        print(f"採用企画: {plan.tentative_title}")
        print(f"\n📚 棚に並ぶ {len(shelved)} 冊（draft＋装丁）")
        for b in shelved:
            url = b.get("coverUrl")
            print(f"  ◆ {b['bookDraft']['title']}")
            print(f"      装丁: variant={b['coverVariant']} cover={'(Imagen) ' + url if url else '(CSS)'}")
        ok = len(shelved) >= 1 and all(b.get("coverVariant") for b in shelved)
        print(f"\n判定: {'OK（棚に draft＋装丁）' if ok else 'WEAK'}")
        return 0 if ok else 1

    res = _run_mode_a_set(
        user, source=source, now=now, reader_llm=args.reader_llm, llm=args.llm,
        preview_llm=args.preview_llm, cover_llm=args.cover_llm, enable_imagen=args.enable_imagen,
        theme_kind=args.theme_kind, threshold=args.threshold,
    )
    if args.json:
        print(json.dumps([mb.shelved for mb in res.books], ensure_ascii=False, indent=2))
        return 0

    pv = res.planning.get("planSetVerdict") or {}
    print(f"セットゲート: {pv.get('decision')} （セット総合{pv.get('score')}・{res.planning.get('rounds')}R）")
    print(f"\n📚 棚に並ぶ {len(res.books)} 冊（4テーマ・1-1-1-1・draft＋装丁）")
    for mb in res.books:
        bd = mb.shelved[0]["bookDraft"] if mb.shelved else {"title": "（無）"}
        author = mb.personas[0].name if mb.personas else "（無）"
        url = mb.shelved[0].get("coverUrl") if mb.shelved else None
        print(f"  ◆ [{mb.plan.theme_role}] {bd['title']}（著者: {author}）")
        print(f"      装丁: cover={'(Imagen) ' + url if url else '(CSS)'}")
    ok = len(res.books) == 4 and all(mb.shelved for mb in res.books)
    print(f"\n判定: {'OK（4テーマ・4冊が棚に draft＋装丁）' if ok else 'WEAK'}")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
