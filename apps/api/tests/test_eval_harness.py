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


# --- C5.2: 採点系プロンプトの 良い例/悪い例 を eval fixture に兼用 ---------------

from publishr_agents.prompts.loader import load_prompt  # noqa: E402

SCORING_PROMPTS = ["step2_plan_leader", "step4_editor_preview", "modeB_editor_body", "eval_judge"]


def test_scoring_fewshot_examples_extracted():
    # 採点系4本は loader が ✅良い例・❌悪い例の両ブロックを抽出できる（単一ソース＝.md）。
    for name in SCORING_PROMPTS:
        doc = load_prompt(name)
        assert doc.good_example, f"{name}: good example block not extracted"
        assert doc.bad_example, f"{name}: bad example block not extracted"
        good = eval_harness._parse_jsonc_objects(doc.good_example)
        bad = eval_harness._parse_jsonc_objects(doc.bad_example)
        assert good and all("score" in o for o in good), f"{name}: good example unparsable"
        assert bad and all("score" in o for o in bad), f"{name}: bad example unparsable"


def test_fewshot_eval_alignment():
    # 良い例＝合格・悪い例＝不合格・eval_judge は eval_set 帯と整合（決定的・実LLM不要）。
    rows = eval_harness.check_fewshot_eval_alignment()
    ids = {r["id"] for r in rows}
    expected = {
        f"fewshot_{n}_{k}"
        for n in ["step2_plan_leader", "step4_editor_preview", "modeB_editor_body"]
        for k in ("good", "bad")
    } | {"fewshot_eval_judge_good", "fewshot_eval_judge_bad"}
    assert ids == expected
    failed = [r for r in rows if not r["passed"]]
    assert not failed, f"misaligned examples: {[(r['id'], r['detail']) for r in failed]}"
