"""C1.3 STEP2 企画3階層 実行CLI（STEP0 観測 → STEP1 読者分析 → STEP2 企画 の縦串）。

  uv run python -m scripts.run_planning --user u_sakura                       # 全mock（オフライン決定的）
  uv run python -m scripts.run_planning --user u_sakura --llm vertex          # STEP2のみ実Pro（STEP1はmock=節約）
  uv run python -m scripts.run_planning --user u_sakura --llm vertex --reader-llm vertex  # 全実LLM
  uv run python -m scripts.run_planning --user u_sakura --llm vertex --threshold 85       # 差し戻しを誘発

fixture/mock は課金なし。--llm vertex は実LLM（3サブFlash＋owner/leader Pro×最大3R・課金あり）。
"""

from __future__ import annotations

import argparse
import json
import os
from datetime import datetime, timedelta, timezone

from publishr_schema import load_users

JST = timezone(timedelta(hours=9))
DEMO_NOW = datetime(2026, 6, 3, 6, 0, tzinfo=JST)  # 水朝の本命 run（6/5役員報告が控える局面）


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
    parser = argparse.ArgumentParser(description="C1.3 STEP2 企画3階層（STEP0→STEP1→STEP2 縦串）")
    parser.add_argument("--user", default="u_sakura")
    parser.add_argument("--source", default="fixture", choices=["fixture", "google"])
    parser.add_argument("--llm", default="mock", choices=["mock", "vertex"], help="STEP2 企画の LLM")
    parser.add_argument("--reader-llm", default="mock", choices=["mock", "vertex"], help="STEP1 読者分析の LLM")
    parser.add_argument("--theme", default=None, help="仮テーマ（省略時は ReaderProfile から導出）")
    parser.add_argument("--threshold", type=int, default=70, help="承認スコア閾値（高くすると差し戻しを誘発）")
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

    from publishr_agents.observe import collect_observation
    from publishr_agents.planning import run_planning
    from publishr_agents.reader import analyze_reader

    print(
        f"== STEP0→STEP1→STEP2（user={user.id} source={args.source} "
        f"reader_llm={args.reader_llm} llm={args.llm} threshold={args.threshold}）=="
    )
    bundle = collect_observation(user, now=now, source=source)
    print(f"STEP0 観測: drive={len(bundle.drive.files)} calendar={len(bundle.calendar.events)} tasks={len(bundle.tasks.items)}")

    profile = analyze_reader(bundle, user=user, llm=args.reader_llm)
    print(f"STEP1 読者: {profile.base.position if profile.base else ''} / challenges={len((profile.current_work.challenges if profile.current_work else []))}")

    result = run_planning(profile, theme=args.theme, threshold=args.threshold, llm=args.llm)

    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0

    print(f"\nSTEP2 仮テーマ: {result['theme']}")
    print("-- 企画リーダーの差し戻し遷移（却下→再提出→採用）--")
    for v in result["verdictHistory"]:
        print(f"  R{v['round']}: score={v['score']} decision={v['decision']}")
    print(f"rounds={result['rounds']} forced_approve={result['forced_approve']}")
    if result.get("rejectionFeedback"):
        print(f"  却下理由(R1): {str(result['rejectionFeedback'])[:140]}")

    plan = result.get("approvedPlan") or {}
    print("\n-- 採用企画(PlanProposal) --")
    print(f"  title      : {plan.get('tentativeTitle', '(なし)')}")
    print(f"  whyNow     : {str(plan.get('whyNowForYou', ''))[:120]}")
    print(f"  diffMarket : {str(plan.get('diffFromMarket', ''))[:140]}")

    sub_market = result.get("subMarket")
    gap = sub_market.get("marketGap") if isinstance(sub_market, dict) else str(sub_market or "")[:160]
    print(f"\n-- subMarket marketGap --\n  {gap}")

    ok = bool(result.get("approvedPlan")) and bool(result.get("verdictHistory"))
    print(f"\n判定: {'OK（承認企画＋採点遷移あり）' if ok else 'FAIL'}")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
