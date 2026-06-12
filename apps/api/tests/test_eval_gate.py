"""C5.3 Eval judge ゲートのテスト（決定的・$0）。

mock judge が eval_set.yaml の cases を expectedBand 通りに採点（高関連≥70/ずれ≤40/
セレンディピティ30-60）し、8件中7件規則でゲート通過/停止を判定すること、borderline は
診断専用でゲート計算外であることを検証する。正本: docs/planning/wbs.md C5.3 / I-21。
"""

from __future__ import annotations

import copy
import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
SPEC = importlib.util.spec_from_file_location("eval_gate", ROOT / "scripts" / "eval_gate.py")
assert SPEC and SPEC.loader
eval_gate = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(eval_gate)


def test_mock_gate_passes_on_real_eval_set():
    rep = eval_gate.run_gate(eval_gate.load_eval_set())
    assert rep["total"] == 8
    assert rep["required"] == 7  # ceil(87.5% of 8)
    assert rep["passed"] >= rep["required"]
    assert rep["gate_pass"] is True


def test_judge_bands_each_kind_on_real_set():
    rep = eval_gate.run_gate(eval_gate.load_eval_set())
    by_kind: dict[str, list] = {}
    for r in rep["results"]:
        by_kind.setdefault(r["kind"], []).append(r)
    for r in by_kind["high_relevance"]:
        assert r["score"] >= 70, r
    for r in by_kind["low_relevance"]:
        assert r["score"] <= 40, r
    for r in by_kind["serendipity"]:
        assert 30 <= r["score"] <= 60, r


def test_gate_fails_when_below_required():
    """高関連2件のbandを到達不能にして誤答化→6/8（<7）→ゲート停止。"""
    bad = copy.deepcopy(eval_gate.load_eval_set())
    for c in bad["cases"]:
        if c["id"] in ("eval_01", "eval_02"):
            c["expectedBand"] = [0, 10]
    rep = eval_gate.run_gate(bad)
    assert rep["passed"] == 6
    assert rep["gate_pass"] is False


def test_borderline_is_diagnostic_not_in_gate():
    rep = eval_gate.run_gate(eval_gate.load_eval_set())
    assert len(rep["diagnostics"]) == 2  # eval_b1 / eval_b2
    assert rep["total"] == 8  # borderline は分母に含めない


def test_serendipity_clamped_to_midrange():
    """教養/越境シグナルのある企画は raw が高くても中レンジに収まる（rubric）。"""
    plan = {
        "tentativeTitle": "ブランドと宗教の構造",  # 宗教=serendipity
        "diffFromMarket": "教養から捉え直す越境型",
        "whyNowForYou": "中期戦略メモ(drive/07)に基づく",
        "coreMessage": "信仰とブランドの相似",
    }
    b = eval_gate.judge_plan_mock(plan)
    assert b["serendipity"] is True
    assert 30 <= b["total"] <= 60


def test_normalize_judge_json_maps_breakdown():
    """実judgeのJSON（score＋scoreBreakdown）を mock 互換 dict に整える。"""
    out = eval_gate._normalize_judge_json(
        {
            "score": 84,
            "scoreBreakdown": {
                "relevance": 24,
                "differentiation": 21,
                "researchUse": 20,
                "titleHook": 19,
            },
        }
    )
    assert out["total"] == 84
    assert out["relevance"] == 24 and out["titleHook"] == 19
    assert out["raw"] == 84
    assert out["serendipity"] is False


def test_normalize_judge_json_clamps_and_falls_back():
    """観点は0-25にクランプ、score欠落時は4観点合計で埋める。"""
    out = eval_gate._normalize_judge_json({"scoreBreakdown": {"relevance": 99}})
    assert out["relevance"] == 25  # 0-25 にクランプ
    assert out["total"] == out["raw"] == 25  # score 欠落→合計で代替


def test_loads_judge_response_strips_fences():
    """response_mime_type=json でも稀に付く ```json フェンスを剥がして parse できる。"""
    fenced = '```json\n{"score": 71, "scoreBreakdown": {"relevance": 18}}\n```'
    out = eval_gate._loads_judge_response(fenced)
    assert out["score"] == 71
    assert eval_gate._loads_judge_response('{"score": 50}')["score"] == 50


def test_loads_judge_response_rejects_empty():
    """resp.text が None/空（SAFETY/MAX_TOKENS 等）は明確に失敗させる。"""
    import pytest as _pytest

    for bad in (None, "", "   "):
        with _pytest.raises(ValueError):
            eval_gate._loads_judge_response(bad)


def test_vertex_backend_dispatches_to_vertex_judge(monkeypatch):
    """backend=vertex は judge_plan_vertex に委譲し reader_profile を渡す（実呼び出しはしない）。"""
    seen: dict[str, object] = {}

    def _fake_vertex(plan, *, reader_profile=None):
        seen["plan"] = plan
        seen["reader_profile"] = reader_profile
        return {
            "relevance": 0,
            "differentiation": 0,
            "researchUse": 0,
            "titleHook": 0,
            "raw": 0,
            "serendipity": False,
            "total": 77,
        }

    monkeypatch.setattr(eval_gate, "judge_plan_vertex", _fake_vertex)
    out = eval_gate.judge_plan({"tentativeTitle": "x"}, backend="vertex", reader_profile={"r": 1})
    assert out["total"] == 77
    assert seen["reader_profile"] == {"r": 1}


def test_main_returns_zero_on_pass():
    assert eval_gate.main([]) == 0
