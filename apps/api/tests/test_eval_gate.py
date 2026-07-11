"""C5.3 Eval judge ゲートのテスト（決定的・$0）。

mock judge が eval_set.yaml の cases を expectedBand 通りに採点（高関連≥70/ずれ≤40/
セレンディピティ≥70※①を嗜好整合に読み替え・2026-06-12に旧中レンジ30-60を廃止）し、
8件中7件規則でゲート通過/停止を判定すること、borderline は診断専用でゲート計算外で
あることを検証する。
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
        assert r["score"] >= 70, r  # ①読み替え（嗜好整合）で本命と同じ閾値70


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


def test_serendipity_with_fit_passes_threshold():
    """①読み替え: 嗜好整合（読み切り/ストーリー形式）と素材反映のあるserendipityは70以上。"""
    plan = {
        "tentativeTitle": "もしあなたが千年共和国の元首なら？——興亡の歴史ショート・ストーリー",
        "readerSituation": "新任2ヶ月で7名のチームとブランドの方向性を預かる",
        "whyNowForYou": "歴史上の組織が分岐点で何をし、なぜ栄え滅びたかを読み切りストーリーで追体験できるから",
        "coreMessage": "盛衰は権限の配分と意思決定で決まるという視座を獲得する",
        "diffFromMarket": "学術的大著と格言集に二極化した市場の隙間（marketGap）を読み切りの疑似体験で埋める教養",
        "keyInsights": ["包括的制度と収奪的制度"],
        "agendaOutline": ["ローマの分岐点", "ヴェネツィアの黄昏"],
    }
    b = eval_gate.judge_plan_mock(plan)
    assert b["serendipity"] is True
    assert b["total"] >= 70


def test_serendipity_without_fit_stays_below_threshold():
    """①読み替えでも判別力は保つ: 嗜好整合シグナルのない雑なserendipityは70未満。"""
    plan = {
        "tentativeTitle": "宗教の通史",
        "diffFromMarket": "教養から捉え直す",
        "whyNowForYou": "",
        "coreMessage": "信仰について",
    }
    b = eval_gate.judge_plan_mock(plan)
    assert b["serendipity"] is True
    assert b["total"] < 70


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


def test_judge_user_content_serializes_dates():
    """eval_set.yaml の readerProfile は YAML date を含む＝default=str で JSON 化できる。"""
    import datetime

    content = eval_gate._judge_user_content(
        {"title": "x", "due": datetime.date(2026, 6, 5)},
        {"currentWork": {"reportDate": datetime.date(2026, 6, 5)}},
    )
    assert "2026-06-05" in content  # date が文字列化されている
    assert "読者プロファイル" in content and "PlanProposal" in content


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
