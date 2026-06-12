"""C5.5 閾値感度スイープ（本命合格ライン honmeiMin を振って通過挙動を見る運用調整の土台）。

「合格ライン(70点等)や採点基準を実データを見ながら微調整」(C5.5)するための可視化ツール。
mock judge は決定的なので結果は再現的。各閾値 T について、
  - 高関連(high_relevance)企画のうち score≥T の通過数（＝本命の取りこぼし/緩さ）
  - 境界ケース eval_b1（ギリ通したい）/eval_b2（ギリ落としたい）の T での合否
を表にし、70 を上下に動かしたときの影響を一望できる。既定の中心は meta.threshold.honmeiMin。

  uv run python -m scripts.eval_threshold_sweep                 # 既定: honmeiMin±10 を5点
  uv run python -m scripts.eval_threshold_sweep -t 65 70 75     # 任意の閾値群
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any, Optional

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.eval_gate import judge_plan, load_eval_set  # noqa: E402


def honmei_min(eval_set: dict[str, Any]) -> int:
    """meta.threshold.honmeiMin（本命合格ライン・単一の調整箇所）。"""
    return int(eval_set.get("meta", {}).get("threshold", {}).get("honmeiMin", 70))


def _scores_by_kind(eval_set: dict[str, Any]) -> dict[str, list[tuple[str, int]]]:
    """kind ごとに (id, mock score) を集める（cases のみ・決定的）。"""
    by_kind: dict[str, list[tuple[str, int]]] = {}
    for c in eval_set.get("cases", []):
        score = judge_plan(c["plan"])["total"]
        by_kind.setdefault(c.get("kind", "?"), []).append((c["id"], score))
    return by_kind


def _borderline_scores(eval_set: dict[str, Any]) -> dict[str, int]:
    return {c["id"]: judge_plan(c["plan"])["total"] for c in eval_set.get("borderlineCases", [])}


def run_sweep(
    eval_set: dict[str, Any], *, thresholds: Optional[list[int]] = None
) -> list[dict[str, Any]]:
    """各閾値での高関連通過数と境界ケースの合否（score≥T）を返す。"""
    if thresholds is None:
        center = honmei_min(eval_set)
        thresholds = [center - 10, center - 5, center, center + 5, center + 10]
    by_kind = _scores_by_kind(eval_set)
    highs = by_kind.get("high_relevance", [])
    border = _borderline_scores(eval_set)
    rows: list[dict[str, Any]] = []
    for t in thresholds:
        rows.append(
            {
                "threshold": t,
                "honmeiTotal": len(highs),
                "honmeiPass": sum(1 for _id, s in highs if s >= t),
                "borderline": {bid: (s >= t) for bid, s in border.items()},
            }
        )
    return rows


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="C5.5 閾値感度スイープ")
    parser.add_argument(
        "-t",
        "--thresholds",
        type=int,
        nargs="+",
        default=None,
        help="採点閾値の列（既定: meta.honmeiMin±10 の5点）",
    )
    args = parser.parse_args(argv)

    eval_set = load_eval_set()
    rows = run_sweep(eval_set, thresholds=args.thresholds)
    center = honmei_min(eval_set)
    print(f"== C5.5 閾値感度スイープ（中心 honmeiMin={center}・mock・決定的） ==")
    border_ids = sorted(rows[0]["borderline"]) if rows else []
    header = "  T   本命通過   " + "  ".join(border_ids)
    print(header)
    for r in rows:
        mark = " ←現行" if r["threshold"] == center else ""
        border_cells = "  ".join(
            ("通過" if r["borderline"][bid] else "落下") for bid in border_ids
        )
        print(
            f"  {r['threshold']:<3} {r['honmeiPass']}/{r['honmeiTotal']}        "
            f"{border_cells}{mark}"
        )
    print(
        "\n読み方: 閾値を上げるほど本命(high_relevance)の取りこぼしが増える。"
        "\n        境界の真の刃先(eval_b1=ギリ通す/eval_b2=ギリ落とす)は実judgeで現れる"
        "（mock は eval_b1 が飽和＝全閾値で通過）。両立点を 70 近傍で選ぶ（C5.5）。"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
