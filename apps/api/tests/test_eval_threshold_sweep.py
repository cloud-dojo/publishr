"""C5.5 閾値感度スイープのテスト（決定的・$0）。

honmeiMin（本命合格ライン）を振って、高関連企画の通過数と境界ケース(eval_b1/b2)の
判定がどう動くかを示す運用調整の土台。mock judge 決定的なので結果は再現的。
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
SPEC = importlib.util.spec_from_file_location(
    "eval_threshold_sweep", ROOT / "scripts" / "eval_threshold_sweep.py"
)
assert SPEC and SPEC.loader
sweep = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(sweep)


def test_honmei_pass_count_is_monotonic_non_increasing_in_threshold():
    eval_set = sweep.load_eval_set()
    rows = sweep.run_sweep(eval_set, thresholds=[60, 65, 70, 75, 80])
    counts = [r["honmeiPass"] for r in rows]
    # 閾値を上げると本命の通過数は増えない（単調非増加）。
    assert counts == sorted(counts, reverse=True)


def test_sweep_reports_borderline_classification_at_each_threshold():
    eval_set = sweep.load_eval_set()
    rows = sweep.run_sweep(eval_set, thresholds=[70])
    row = rows[0]
    # 境界2件の合否が閾値ごとに付く（eval_b1=ギリ通す/eval_b2=ギリ落とす想定）。
    assert set(row["borderline"]) == {"eval_b1", "eval_b2"}
    assert isinstance(row["borderline"]["eval_b1"], bool)


def test_default_threshold_comes_from_eval_set_meta():
    eval_set = sweep.load_eval_set()
    assert sweep.honmei_min(eval_set) == 70  # meta.threshold.honmeiMin


def test_main_runs_and_returns_zero():
    assert sweep.main([]) == 0
