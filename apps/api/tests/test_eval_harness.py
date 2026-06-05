from __future__ import annotations

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
SPEC = importlib.util.spec_from_file_location("eval_harness", ROOT / "scripts" / "eval_harness.py")
assert SPEC and SPEC.loader
eval_harness = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(eval_harness)

EVAL_SET = ROOT / "eval" / "eval_set.yaml"


def test_eval_set_v2_dataset_is_wellformed():
    # v2: eval_set.yaml は LLM-judge 用データセット（cases 8件・expectedBand 形式）。
    cases = eval_harness.load_eval_cases(EVAL_SET)
    assert set(cases) == {f"eval_0{i}" for i in range(1, 9)}
    # 帯の意味: 高関連は下限>=70・ずれは上限<=40。
    assert cases["eval_01"]["expectedBand"][0] >= 70
    assert cases["eval_05"]["expectedBand"][1] <= 40

    ok, detail = eval_harness.validate_eval_set(EVAL_SET)
    assert ok, detail


def test_eval_harness_passes_for_mock_pipeline():
    report = eval_harness.evaluate_pipeline("u_tadokoro")
    ids = {r["id"] for r in report}
    # 決定的チェックの正本はコード内 DETERMINISTIC_THRESHOLDS。
    assert ids >= set(eval_harness.DETERMINISTIC_THRESHOLDS)
    assert all(r["passed"] for r in report)
    assert all("score" in r and "threshold" in r for r in report)
