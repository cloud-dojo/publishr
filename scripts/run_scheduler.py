"""C1.7 自律トリガー（曜日別スケジュール）実行CLI＝ローカル・mock・課金ゼロ。

  uv run python -m scripts.run_scheduler --once                 # 今日の themeKind で1サイクル（mock）
  uv run python -m scripts.run_scheduler --once --theme-kind serendipity
  uv run python -m scripts.run_scheduler --watch                # ローカル常駐（次の水/土/日 06:00 で自律起動）

「指示なしに動く」を Cloud 課金なしで実演する。パイプラインは mock 既定（LLM課金ゼロ）。
本番は Cloud Scheduler が同じ曜日でトリガー（別途デプロイ・課金）:
  honmei `0 6 * * 3,6`（水・土）／ serendipity `0 6 * * 0`（日）
"""

from __future__ import annotations

import argparse
import time
from datetime import datetime, timedelta, timezone

from publishr_schema import load_users

from publishr_agents.scheduler import next_run, theme_kind_for

JST = timezone(timedelta(hours=9))


def _now() -> datetime:
    return datetime.now(JST)


def _run_cycle(user, *, theme_kind: str, llm: str, now: datetime):
    """モードA 1サイクル（4テーマ1-1-1-1・観測→…→装丁）を実行し ModeASetResult を返す。既定 mock＝課金ゼロ。"""
    from publishr_agents.mode_a import run_mode_a_set_pipeline
    from publishr_agents.observe import FixtureObservationSource

    return run_mode_a_set_pipeline(
        user,
        source=FixtureObservationSource(),
        now=now,
        reader_llm=llm,
        llm=llm,
        preview_llm=llm,
        cover_llm=llm,
        enable_imagen=False,
        theme_kind=theme_kind,
        threshold=70,
    )


def _print_cycle(now: datetime, theme_kind: str, result) -> None:
    pv = result.planning.get("planSetVerdict") or {}
    print(
        f"[{now.isoformat()}] 自律起動 themeKind={theme_kind} → セットゲート {pv.get('decision')}"
        f"（総合{pv.get('score')}・{result.planning.get('rounds')}R）"
    )
    print(f"  棚に {len(result.books)} 冊（4テーマ・1-1-1-1・本文生成前プレビュー）:")
    for mb in result.books:
        bd = mb.shelved[0]["bookDraft"] if mb.shelved else {"title": "（無題）"}
        author = mb.personas[0].name if mb.personas else "（著者なし）"
        print(f"    ◆ [{mb.plan.theme_role}] {bd['title']}（{author}）")


def main() -> int:
    parser = argparse.ArgumentParser(description="C1.7 自律トリガー（ローカル・mock・課金ゼロ）")
    parser.add_argument("--user", default="u_sakura")
    parser.add_argument("--llm", default="mock", choices=["mock", "vertex"], help="既定mock＝課金ゼロ")
    parser.add_argument("--theme-kind", default="auto", choices=["auto", "honmei", "serendipity"])
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--once", action="store_true", help="今すぐ1サイクル実行して終了")
    mode.add_argument("--watch", action="store_true", help="ローカル常駐し次の起動曜日で自律実行")
    args = parser.parse_args()

    user = next((u for u in load_users() if u.id == args.user), None)
    if user is None:
        raise SystemExit(f"ユーザーが見つかりません: {args.user}")

    if not args.once and not args.watch:
        args.once = True  # 既定は1回実行

    if args.once:
        now = _now()
        theme_kind = args.theme_kind if args.theme_kind != "auto" else (theme_kind_for(now) or "honmei")
        result = _run_cycle(user, theme_kind=theme_kind, llm=args.llm, now=now)
        _print_cycle(now, theme_kind, result)
        return 0

    # --watch: 次の水/土/日 06:00 まで待って自律起動（ローカル・依存なし）。
    print("== 自律スケジューラ常駐（水/土=本命・日=セレンディピティ・06:00 JST）。Ctrl+C で停止 ==")
    try:
        while True:
            target = next_run(_now())
            wait = (target - _now()).total_seconds()
            print(f"次の自律起動: {target.isoformat()}（約 {int(max(wait, 0) // 60)} 分後）")
            while wait > 0:
                time.sleep(min(wait, 300))  # 5分刻みで起床（長時間スリープを避ける）
                wait = (target - _now()).total_seconds()
            tk = theme_kind_for(target) or "honmei"
            try:
                result = _run_cycle(user, theme_kind=tk, llm=args.llm, now=target)
                _print_cycle(target, tk, result)
            except Exception as exc:  # noqa: BLE001 — 1サイクルの失敗で常駐を落とさない
                print(f"[{target.isoformat()}] サイクル失敗: {exc}")
            time.sleep(60)  # 同一分での二重起動を避ける
    except KeyboardInterrupt:
        print("\n== 停止しました ==")
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
