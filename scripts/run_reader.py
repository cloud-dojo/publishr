"""C1.2 STEP1 読者分析 実行CLI（STEP0 観測 → STEP1 分析 の縦串）。

  uv run python -m scripts.run_reader --user u_sakura                      # 全mock（オフライン決定的・課金なし）
  uv run python -m scripts.run_reader --user u_sakura --llm vertex         # 実Gemini Pro（課金）
  uv run python -m scripts.run_reader --user u_sakura --source google --llm vertex  # 実観測＋実分析

fixture/mock は課金なし。--llm vertex は実LLM（Vertex Gemini Pro・課金あり）。
"""

from __future__ import annotations

import argparse
import json
import os
from datetime import datetime, timedelta, timezone

from publishr_schema import load_users

JST = timezone(timedelta(hours=9))
# 水朝の本命 run。6/5 役員中間報告会などが「控える重要局面」になるデモアンカー。
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


def main() -> int:
    parser = argparse.ArgumentParser(description="C1.2 STEP1 読者分析（STEP0→STEP1 縦串）")
    parser.add_argument("--user", default="u_sakura")
    parser.add_argument("--source", default="fixture", choices=["fixture", "google"])
    parser.add_argument("--llm", default="mock", choices=["mock", "vertex"])
    parser.add_argument("--now", default=None, help="観測基準時刻 ISO8601（±14日窓の中心）")
    parser.add_argument("--json", action="store_true", help="ReaderProfile を JSON で出力")
    args = parser.parse_args()

    user = next((u for u in load_users() if u.id == args.user), None)
    if user is None:
        raise SystemExit(f"ユーザーが見つかりません: {args.user}")
    if args.llm == "vertex":
        _ensure_vertex_env()

    now = _resolve_now(args.now, args.source)
    source = _build_source(args.source)

    from publishr_agents.observe import collect_observation
    from publishr_agents.reader import analyze_reader

    print(f"== STEP0→STEP1（user={user.id} source={args.source} llm={args.llm} now={now.isoformat()}）==")
    bundle = collect_observation(user, now=now, source=source)
    print(
        f"観測: drive={len(bundle.drive.files)} "
        f"calendar={len(bundle.calendar.events)} tasks={len(bundle.tasks.items)}"
    )

    profile = analyze_reader(bundle, user=user, llm=args.llm)

    if args.json:
        print(json.dumps(profile.model_dump(by_alias=True), ensure_ascii=False, indent=2))
        return 0

    b, cw, rb = profile.base, profile.current_work, profile.reading_behavior
    print("\n-- base（保持・再分析しない）--")
    print(f"  position={b.position} / orgScale={b.org_scale} / genres={b.reading_genres}")
    print("-- currentWork（分析の主戦場）--")
    print(f"  situation : {cw.current_situation}")
    print(f"  themes    : {cw.active_work_themes}")
    print(f"  challenges: {cw.challenges}")
    print(f"  upcoming  : {[(e.title, e.date) for e in cw.upcoming_key_events]}")
    print(f"  evidence  : {[(e.claim[:20], e.source) for e in cw.evidence]}")
    print("-- readingBehavior --")
    print(f"  serendipity={rb.serendipity_tolerance} / highlights='{rb.highlights_summary}'")

    ok = bool(cw.evidence) and bool(b.position or b.industry)
    print(f"\n判定: {'OK（3層Profile生成・evidence付き）' if ok else 'WEAK（evidence/base不足）'}")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
