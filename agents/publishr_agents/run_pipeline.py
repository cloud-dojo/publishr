"""CLI: 企画会議パイプラインをオフライン実行する。

    python -m publishr_agents.run_pipeline --user u_tadokoro
    python -m publishr_agents.run_pipeline --user u_tadokoro --json
"""

from __future__ import annotations

import argparse

from .pipeline import run_pipeline


def main() -> None:
    parser = argparse.ArgumentParser(description="Publishr 企画会議パイプライン")
    parser.add_argument("--user", default="u_tadokoro", help="観測対象ユーザーID")
    parser.add_argument("--json", action="store_true", help="結果をJSONで出力")
    args = parser.parse_args()

    result = run_pipeline(args.user)

    if args.json:
        print(result.model_dump_json(by_alias=True, indent=2))
        return

    print(f"観測ユーザー: {args.user}")
    print(f"承認企画: {len(result.plans)}件 ／ 入荷書籍: {len(result.books)}冊")
    print("── 企画会議ログ（対立①: 却下→再提出） ──")
    for e in result.reject_log:
        print(f"  R{e.round} [{e.verdict}] {e.persona}「{e.candidate}」: {e.reason}")
    resubmitted = any(e.round == 1 and e.verdict == "却下" for e in result.reject_log)
    adopted = any(e.round == 2 and e.verdict == "採用" for e in result.reject_log)
    print(f"\n却下→再提出が発生: {resubmitted} ／ 再提出後に採用: {adopted}")


if __name__ == "__main__":
    main()
