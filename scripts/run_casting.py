"""C1.4 STEP3 キャスティング 実行CLI（STEP0観測→STEP1読者→STEP2企画→STEP3著者 の縦串）。

  uv run python -m scripts.run_casting --user u_sakura                       # 全mock（オフライン決定的）
  uv run python -m scripts.run_casting --user u_sakura --llm vertex          # STEP2/3を実Pro（STEP1はmock=節約）
  uv run python -m scripts.run_casting --user u_sakura --llm vertex --reader-llm vertex  # 全実LLM

fixture/mock は課金なし。--llm vertex は実LLM（課金あり）。
"""

from __future__ import annotations

import argparse
import json
import os
from datetime import datetime, timedelta, timezone

from publishr_schema import PlanProposal, load_users

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


def main() -> int:
    parser = argparse.ArgumentParser(description="C1.4 STEP3 キャスティング（STEP0→1→2→3 縦串）")
    parser.add_argument("--user", default="u_sakura")
    parser.add_argument("--source", default="fixture", choices=["fixture", "google"])
    parser.add_argument("--llm", default="mock", choices=["mock", "vertex"], help="STEP2/3 の LLM")
    parser.add_argument("--reader-llm", default="mock", choices=["mock", "vertex"], help="STEP1 の LLM")
    parser.add_argument("--theme", default=None)
    parser.add_argument("--threshold", type=int, default=70)
    parser.add_argument("--now", default=None)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    user = next((u for u in load_users() if u.id == args.user), None)
    if user is None:
        raise SystemExit(f"ユーザーが見つかりません: {args.user}")
    if args.llm == "vertex" or args.reader_llm == "vertex":
        _ensure_vertex_env()

    now = _resolve_now(args.now, args.source)
    source = _build_source(args.source)

    from publishr_agents.casting import cast_personas
    from publishr_agents.observe import collect_observation
    from publishr_agents.planning import run_planning
    from publishr_agents.reader import analyze_reader

    print(
        f"== STEP0→1→2→3（user={user.id} source={args.source} "
        f"reader_llm={args.reader_llm} llm={args.llm} threshold={args.threshold}）=="
    )
    bundle = collect_observation(user, now=now, source=source)
    profile = analyze_reader(bundle, user=user, llm=args.reader_llm)
    planning = run_planning(profile, theme=args.theme, threshold=args.threshold, llm=args.llm)
    plan = PlanProposal.model_validate(planning["approvedPlan"])
    print(f"STEP2 採用企画: {plan.tentative_title}（rounds={planning['rounds']}）")

    favorites = list(user.favorite_authors or [])
    personas = cast_personas(plan, reader_profile=profile, favorite_authors=favorites, llm=args.llm)

    if args.json:
        print(json.dumps(personas.model_dump(by_alias=True), ensure_ascii=False, indent=2))
        return 0

    print(f"\nSTEP3 キャスティング（{len(personas.personas)}人・voiceStyle×format 2軸）")
    for p in personas.personas:
        fav = "★お気に入り" if p.from_favorite else ""
        print(f"  - {p.name}：{p.voice_style} × {p.format} {fav}")
        print(f"      {p.persona[:70]}")
    print(f"\n散らし方: {personas.reason[:160]}")

    combos = {(p.voice_style, p.format) for p in personas.personas}
    ok = len(personas.personas) == 5 and len(combos) >= 4
    print(f"\n判定: {'OK（5著者・2軸分散）' if ok else 'WEAK（員数/分散不足）'}")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
