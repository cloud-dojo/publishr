from __future__ import annotations

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
SPEC = importlib.util.spec_from_file_location("eval_harness", ROOT / "scripts" / "eval_harness.py")
assert SPEC and SPEC.loader
eval_harness = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(eval_harness)


def test_eval_set_ids_are_loaded():
    ids = eval_harness.load_eval_ids(ROOT / "eval" / "eval_set.yaml")
    assert ids == [
        "plan_relevance",
        "proposal_diversity",
        "selection_adversarial",
        "author_voice_consistency",
        "stocking_reason_credibility",
    ]
    items = eval_harness.load_eval_items(ROOT / "eval" / "eval_set.yaml")
    assert items["plan_relevance"]["threshold"] == ">=4"
    assert items["selection_adversarial"]["threshold"] == "== true"


def test_eval_harness_passes_for_mock_pipeline():
    report = eval_harness.evaluate_pipeline("u_tadokoro")
    assert {r["id"] for r in report} >= set(eval_harness.load_eval_ids(ROOT / "eval" / "eval_set.yaml"))
    assert all(r["passed"] for r in report)
    assert all("score" in r and "threshold" in r for r in report)
