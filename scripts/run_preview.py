"""C1.5 STEP4 プレビュー編集 実行CLI（モードA フル縦串 STEP0→1→2→3→4＝棚5冊draft）。

  uv run python -m scripts.run_preview --user u_sakura                          # 全mock（オフライン決定的・5冊）
  uv run python -m scripts.run_preview --user u_sakura --preview-llm vertex --limit 2  # STEP4だけ実Pro・2冊（最小）
  uv run python -m scripts.run_preview --user u_sakura --llm vertex --preview-llm vertex --reader-llm vertex  # 全実LLM

各 LLM は段階別に切替（コスト制御）: --reader-llm=STEP1 / --llm=STEP2企画+STEP3著者 / --preview-llm=STEP4。
mock は課金なし。vertex は実LLM（課金あり）。
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
    parser = argparse.ArgumentParser(description="C1.5 STEP4 プレビュー編集（モードA フル縦串）")
    parser.add_argument("--user", default="u_sakura")
    parser.add_argument("--source", default="fixture", choices=["fixture", "google"])
    parser.add_argument("--reader-llm", default="mock", choices=["mock", "vertex"], help="STEP1")
    parser.add_argument("--llm", default="mock", choices=["mock", "vertex"], help="STEP2企画+STEP3著者")
    parser.add_argument("--preview-llm", default="mock", choices=["mock", "vertex"], help="STEP4プレビュー")
    parser.add_argument("--theme", default=None)
    parser.add_argument("--threshold", type=int, default=70)
    parser.add_argument("--limit", type=int, default=None, help="STEP4で処理する冊数の上限（コスト制御）")
    parser.add_argument("--now", default=None)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    user = next((u for u in load_users() if u.id == args.user), None)
    if user is None:
        raise SystemExit(f"ユーザーが見つかりません: {args.user}")
    if "vertex" in (args.reader_llm, args.llm, args.preview_llm):
        _ensure_vertex_env()

    now = _resolve_now(args.now, args.source)
    source = _build_source(args.source)

    from publishr_agents.casting import cast_personas
    from publishr_agents.observe import collect_observation
    from publishr_agents.planning import run_planning
    from publishr_agents.preview import run_preview
    from publishr_agents.reader import analyze_reader

    print(
        f"== STEP0→1→2→3→4（user={user.id} source={args.source} "
        f"reader={args.reader_llm} plan/cast={args.llm} preview={args.preview_llm} limit={args.limit}）=="
    )
    bundle = collect_observation(user, now=now, source=source)
    profile = analyze_reader(bundle, user=user, llm=args.reader_llm)
    planning = run_planning(profile, theme=args.theme, threshold=args.threshold, llm=args.llm)
    plan = PlanProposal.model_validate(planning["approvedPlan"])
    print(f"STEP2 採用企画: {plan.tentative_title}")
    personas = cast_personas(plan, reader_profile=profile, favorite_authors=list(user.favorite_authors or []), llm=args.llm)
    print(f"STEP3 著者: {len(personas.personas)}人")

    drafts = run_preview(plan, personas.personas, reader_profile=profile, limit=args.limit, llm=args.preview_llm)

    if args.json:
        print(json.dumps(drafts, ensure_ascii=False, indent=2))
        return 0

    print(f"\nSTEP4 棚に並ぶ draft（{len(drafts)}冊・著者⇄編集長 1R）")
    for d in drafts:
        bd = d["bookDraft"]
        v = d["verdict"] or {}
        print(f"  ◆ {bd['title']}")
        print(f"      入荷理由: {str(bd.get('deliveryReason', ''))[:64]}")
        print(f"      編集: score={v.get('score')} decision={v.get('decision')} editRounds={d['editRounds']}")

    ok = len(drafts) >= 1 and all(d["bookDraft"].get("prefaceSample") for d in drafts)
    print(f"\n判定: {'OK（draft 生成・7項目充足）' if ok else 'WEAK'}")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
