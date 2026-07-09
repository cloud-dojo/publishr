"""C5.4 judge 再現性ハーネスのテスト（決定的・$0）。

mock judge は決定的＝σ=0・CV=0・band 安定度1.0 を期待値とする（再現性の床）。
実 judge のブレ測定は --backend vertex（gated・課金）で、ここではオフライン構造のみ検証。
正本: docs/planning/wbs.md C5.4 / I-21。
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
SPEC = importlib.util.spec_from_file_location(
    "eval_reproducibility", ROOT / "scripts" / "eval_reproducibility.py"
)
assert SPEC and SPEC.loader
repro = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(repro)


def test_summarize_constant_scores_is_zero_variance():
    stats = repro.summarize([84, 84, 84], (70, 100))
    assert stats["mean"] == 84
    assert stats["stdev"] == 0.0
    assert stats["cv"] == 0.0
    assert stats["stability"] == 1.0


def test_summarize_band_stability_counts_in_band_runs():
    stats = repro.summarize([69, 71, 72, 68], (70, 80))
    assert stats["inBand"] == 2
    assert stats["stability"] == 0.5
    assert stats["stdev"] > 0.0


def test_mock_reproducibility_is_deterministic_across_runs():
    eval_set = repro.load_eval_set()
    rows = repro.run_reproducibility(eval_set, backend="mock", runs=5)
    # cases(8) + borderlineCases(2) を網羅。
    assert len(rows) == 10
    for r in rows:
        assert r["stdev"] == 0.0  # mock は決定的
        assert r["cv"] == 0.0
        assert r["stability"] == 1.0  # 各ケースは自分の expectedBand 内で安定
        assert min(r["scores"]) == max(r["scores"])


def test_main_mock_passes_default_tolerances():
    # mock 既定（max-cv=0・min-stability=1.0）でゲートは通過（exit 0）。
    assert repro.main(["--backend", "mock", "-n", "3"]) == 0
