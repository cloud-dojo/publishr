"""単発プロンプトランナーの実Vertex スモーク（C5.1・gated・課金）。

PUBLISHR_RUN_VERTEX=1（＋ADC）でのみ実行。plan_leader を eval_set の実データで1本流し、
JSON採点（score）が返ることを確認する＝ランナーの実Vertex 経路の最小回帰。
"""

from __future__ import annotations

import importlib.util
import json
import os
from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[3]
SPEC = importlib.util.spec_from_file_location("run_prompt", ROOT / "scripts" / "run_prompt.py")
assert SPEC and SPEC.loader
run_prompt = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(run_prompt)


@pytest.mark.vertex
@pytest.mark.skipif(
    os.environ.get("PUBLISHR_RUN_VERTEX") != "1",
    reason="set PUBLISHR_RUN_VERTEX=1 (＋GCP creds) to run live Vertex prompt（課金）",
)
def test_plan_leader_runs_on_vertex():
    os.environ.setdefault("GOOGLE_GENAI_USE_VERTEXAI", "TRUE")
    os.environ.setdefault("GOOGLE_CLOUD_PROJECT", "publishr-498123")
    os.environ.setdefault("GOOGLE_CLOUD_LOCATION", "asia-northeast1")

    data = yaml.safe_load((ROOT / "eval" / "eval_set.yaml").read_text(encoding="utf-8"))
    case = next(c for c in data["cases"] if c["id"] == "eval_01")
    state = {
        "plan": case["plan"], "planDraft": case["plan"], "readerProfile": data.get("readerProfile"),
        "themeKind": "honmei", "threshold": 70,
    }
    plan = run_prompt.assemble("plan_leader", state)
    out = run_prompt.run_vertex(plan, temperature=0.0)
    print(f"\n[vertex run_prompt] plan_leader → {out[:200]}")
    parsed = json.loads(out)
    assert "score" in parsed and isinstance(parsed["score"], int)
