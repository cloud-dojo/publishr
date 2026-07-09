"""C5.4: 実 Vertex judge（Gemini Pro）の最小 live テスト（既定 skip・課金）。

実行（GCP ADC＋課金が要る）:
  PUBLISHR_RUN_VERTEX=1 GOOGLE_CLOUD_PROJECT=publishr-498123 \
    uv run pytest apps/api/tests/test_eval_gate_vertex.py -s

mock床（CI常用・$0）は test_eval_gate.py。ここは judge_plan(backend="vertex") の配線が
実Geminiで end-to-end 動く（readerProfile＋plan→4観点JSON→mock互換dict）ことの確認のみ。
"""

from __future__ import annotations

import importlib.util
import os
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[3]
SPEC = importlib.util.spec_from_file_location("eval_gate", ROOT / "scripts" / "eval_gate.py")
assert SPEC and SPEC.loader
eval_gate = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(eval_gate)


@pytest.mark.vertex
@pytest.mark.skipif(
    os.environ.get("PUBLISHR_RUN_VERTEX") != "1",
    reason="set PUBLISHR_RUN_VERTEX=1 (＋GCP creds) to run live Vertex judge（課金）",
)
def test_vertex_judge_scores_eval_01_shape():
    os.environ.setdefault("GOOGLE_GENAI_USE_VERTEXAI", "TRUE")
    os.environ.setdefault("GOOGLE_CLOUD_PROJECT", "publishr-498123")
    os.environ.setdefault("GOOGLE_CLOUD_LOCATION", "asia-northeast1")

    eset = eval_gate.load_eval_set()
    case = next(c for c in eset["cases"] if c["id"] == "eval_01")
    out = eval_gate.judge_plan(
        case["plan"], backend="vertex", reader_profile=eset.get("readerProfile")
    )
    print(f"\n[vertex judge] eval_01 → {out}")  # noqa: T201 — gated手動実行で人が読む
    for key in ("relevance", "differentiation", "researchUse", "titleHook", "raw", "total"):
        assert key in out
        assert 0 <= out[key] <= 100
    assert 0 <= out["total"] <= 100
