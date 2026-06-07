"""C1.1 STEP0 観測ツール 実行CLI。

  uv run python -m scripts.run_observe --user u_sakura                 # 既定=fixture（オフライン決定的）
  uv run python -m scripts.run_observe --user u_sakura --source google # 実Google API（要OAuth・隔離）

fixture は課金なし。google は実API（Drive/Calendar/Tasks の読取・LLM非使用＝課金は実質ゼロ）。
google を使う前に `uv run python scripts/google_oauth_bootstrap.py` で同意を済ませる。
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timedelta, timezone

from publishr_schema import load_users

# 水朝の本命 run を想定したデモ既定アンカー（6/5 役員報告等が窓内・run_reader と統一）。
JST = timezone(timedelta(hours=9))
DEMO_NOW = datetime(2026, 6, 3, 6, 0, tzinfo=JST)


def _resolve_now(now_arg: str | None, source: str) -> datetime:
    if now_arg:
        s = now_arg[:-1] + "+00:00" if now_arg.endswith("Z") else now_arg
        dt = datetime.fromisoformat(s)
        return dt if dt.tzinfo else dt.replace(tzinfo=JST)
    # google は実時刻（今日の±14日）、fixture はデモアンカーで決定的。
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
    parser = argparse.ArgumentParser(description="C1.1 STEP0 観測ツール 実行")
    parser.add_argument("--user", default="u_sakura", help="対象ユーザーID（fixtures/users.json）")
    parser.add_argument("--source", default="fixture", choices=["fixture", "google"])
    parser.add_argument("--now", default=None, help="観測基準時刻 ISO8601（±14日窓の中心・省略時はデモアンカー/実時刻）")
    parser.add_argument("--json", action="store_true", help="ObservationBundle を JSON で出力")
    args = parser.parse_args()

    user = next((u for u in load_users() if u.id == args.user), None)
    if user is None:
        raise SystemExit(f"ユーザーが見つかりません: {args.user}")

    now = _resolve_now(args.now, args.source)
    source = _build_source(args.source)

    from publishr_agents.observe import collect_observation

    print(f"== STEP0 観測（user={user.id} source={args.source} now={now.isoformat()}）==")
    bundle = collect_observation(user, now=now, source=source)

    if args.json:
        print(json.dumps(bundle.model_dump(by_alias=True), ensure_ascii=False, indent=2))
        return 0

    print(f"collectedAt: {bundle.collected_at}")
    print(f"drive    : {len(bundle.drive.files)} files")
    for f in bundle.drive.files[:5]:
        print(f"  - [{f.folder_label}] {f.name}  ({len(f.text_excerpt)}字)")
    print(f"calendar : {len(bundle.calendar.events)} events（±14日窓）")
    for e in bundle.calendar.events[:5]:
        print(f"  - {e.start}  {e.title}  (参加{e.attendees_count}・定例={e.recurring})")
    print(f"tasks    : {len(bundle.tasks.items)} items（未完了＋直近完了）")
    for t in bundle.tasks.items[:5]:
        print(f"  - [{t.status}] {t.title}  (due={t.due})")
    print(f"readingFB: highlights={len(bundle.reading_fb.highlights)} feedback={len(bundle.reading_fb.feedback)}")

    ok = bool(bundle.user_id) and (
        len(bundle.drive.files) + len(bundle.calendar.events) + len(bundle.tasks.items) > 0
    )
    print(f"\n判定: {'OK（観測束を生成）' if ok else 'EMPTY（接続/データを確認）'}")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
