"""C5.4 judge 再現性テスト（同一ケースを複数回採点し、ブレ＝mean/σ/CV/band安定度を測る）。

ゲート判定（C5.3）の信頼度を確認するための土台。mock judge は決定的（$0・σ=0）なので、
ここでは再現性ハーネスの構造検証と床（全ケース band 安定）を提供する。実 judge のブレは
`--backend vertex`（GEAP・gated・課金）で測る（eval_gate と同じ backend 切替）。
境界ケース（eval_b1/b2）は閾値70近傍の判別の安定性を見る重点対象（meta.diagnostic）。

  uv run python -m scripts.eval_reproducibility                       # mock・5回（σ=0 を確認）
  uv run python -m scripts.eval_reproducibility -n 10 --backend vertex  # 実judge 10回（課金）
  uv run python -m scripts.eval_reproducibility --max-cv 0.08 --min-stability 0.8  # 実judge許容
"""

from __future__ import annotations

import argparse
import os
import statistics
import sys
import time
from pathlib import Path
from typing import Any, Optional

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.eval_gate import judge_plan, load_eval_set  # noqa: E402


def _all_cases(eval_set: dict[str, Any]) -> list[dict[str, Any]]:
    """cases（ゲート対象8）＋borderlineCases（診断・C5.4重点2）を一括で扱う。"""
    rows: list[dict[str, Any]] = []
    for c in eval_set.get("cases", []):
        rows.append({**c, "group": "case"})
    for c in eval_set.get("borderlineCases", []):
        rows.append({**c, "group": "borderline"})
    return rows


def score_runs(
    plan: dict[str, Any],
    *,
    backend: str,
    runs: int,
    reader_profile: dict[str, Any] | None = None,
    sleep_sec: float = 0.0,
) -> list[int]:
    """同一企画を runs 回採点したスコアの列を返す（実judgeは readerProfile も渡す）。

    sleep_sec>0 で呼び出し間に待機（実Vertex Pro は RPM/TPM が低く、連投すると 429＝
    RESOURCE_EXHAUSTED でSDKが長時間バックオフするため、ペース調整で回避する）。
    """
    scores: list[int] = []
    for i in range(runs):
        if sleep_sec > 0 and i > 0:
            time.sleep(sleep_sec)
        scores.append(judge_plan(plan, backend=backend, reader_profile=reader_profile)["total"])
    return scores


def summarize(scores: list[int], band: list[int] | tuple[int, int]) -> dict[str, Any]:
    """スコア列の mean/min/max/σ(母標準偏差)/CV と再現性指標を出す。

    再現性(stability)＝**判定の自己一致率**＝N回の in/out-of-band 判定が多数派とどれだけ
    揃うか（max(in,out)/n）。これは「採点がブレないか」を測る指標で、期待帯に当たっているか
    （＝正答性・C5.3 ゲートの担当）とは別。決定的 mock は常に 1.0（同一スコア→判定不変）。
    """
    lo, hi = band
    n = len(scores)
    mean = statistics.fmean(scores) if scores else 0.0
    stdev = statistics.pstdev(scores) if n > 1 else 0.0
    cv = (stdev / mean) if mean else 0.0
    in_band = sum(1 for s in scores if lo <= s <= hi)
    agreement = (max(in_band, n - in_band) / n) if n else 0.0
    return {
        "n": n,
        "mean": mean,
        "min": min(scores) if scores else 0,
        "max": max(scores) if scores else 0,
        "stdev": stdev,
        "cv": cv,
        "inBand": in_band,
        "stability": agreement,
    }


def run_reproducibility(
    eval_set: dict[str, Any], *, backend: str = "mock", runs: int = 5, sleep_sec: float = 0.0
) -> list[dict[str, Any]]:
    reader_profile = eval_set.get("readerProfile")
    rows: list[dict[str, Any]] = []
    for c in _all_cases(eval_set):
        scores = score_runs(
            c["plan"],
            backend=backend,
            runs=runs,
            reader_profile=reader_profile,
            sleep_sec=sleep_sec,
        )
        stats = summarize(scores, c["expectedBand"])
        rows.append(
            {
                "id": c["id"],
                "kind": c.get("kind"),
                "group": c["group"],
                "band": list(c["expectedBand"]),
                "scores": scores,
                **stats,
            }
        )
    return rows


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="C5.4 judge 再現性テスト")
    parser.add_argument("-n", "--runs", type=int, default=5, help="1ケースあたりの採点回数")
    parser.add_argument(
        "--backend",
        default=os.environ.get("PUBLISHR_EVAL_BACKEND", "mock"),
        choices=["mock", "vertex"],
    )
    parser.add_argument(
        "--max-cv", type=float, default=0.0, help="許容する変動係数(CV)の上限（超過で exit 1）"
    )
    parser.add_argument(
        "--min-stability",
        type=float,
        default=1.0,
        help="判定の自己一致率の下限（未満で exit 1・mock は常に1.0）",
    )
    parser.add_argument(
        "--sleep-sec",
        type=float,
        default=0.0,
        help="採点呼び出し間の待機秒（実Vertex Pro の低RPM対策・429回避。例: 6）",
    )
    args = parser.parse_args(argv)

    try:
        rows = run_reproducibility(
            load_eval_set(), backend=args.backend, runs=args.runs, sleep_sec=args.sleep_sec
        )
    except NotImplementedError as exc:
        print(f"vertex judge は live/gated（課金）です: {exc}")
        return 2

    print(
        f"== C5.4 judge 再現性（backend={args.backend}・{args.runs}回/ケース・"
        f"許容 CV≤{args.max_cv} 安定≥{args.min_stability:.0%}） =="
    )
    if args.backend == "mock":
        print("  （mock judge は決定的＝σ=0 が期待値。実ブレは --backend vertex で測る）")
    violations: list[str] = []
    for r in rows:
        unstable = r["cv"] > args.max_cv + 1e-9 or r["stability"] < args.min_stability - 1e-9
        flag = "  [不安定]" if unstable else ""
        if unstable:
            violations.append(r["id"])
        print(
            f"  {r['group']:9} {r['id']} [{r['kind']}] "
            f"mean={r['mean']:.1f} σ={r['stdev']:.2f} cv={r['cv']:.3f} "
            f"min/max={r['min']}/{r['max']} band={r['band']} "
            f"band内={r['inBand']}/{r['n']} 一致={r['stability']:.0%}{flag}"
        )
    if violations:
        print(
            f"\n判定: 再現性が不安定なケース {violations} "
            f"→ 閾値/ルーブリック調整(C5.5)で安定度を上げる"
        )
        return 1
    print("\n判定: 全ケース 再現性 OK（band安定・CV許容内）")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
