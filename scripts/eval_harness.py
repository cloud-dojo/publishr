"""Publishr MVP用の軽量Evalランナー（mock決定的・オフライン）。

本ハーネスは **mock回帰の床（H0a）** として、外部LLM採点を使わず2系統を決定的に検証する：

1. **mock pipeline 出力の検証**（基準1の証跡）
   `PUBLISHR_LLM=mock` の決定的パイプライン出力を、観測根拠・企画多様性・選抜証跡
   （却下→再提出→採用）・著者ペルソナ声・入荷理由の5観点で照合する。
2. **eval/eval_set.yaml（v2）の構造検証**
   LLM-as-judge 用データセット（cases 8件・expectedBand 形式）が壊れていないことを
   決定的に確認する。実LLM/GEAP採点は本ハーネスとは分離（P6・`packages/prompts/eval_judge.md`）。

> 注: v2 `eval_set.yaml` は LLM-judge データセットであり、本ハーネスの決定的チェックの
> 閾値は `DETERMINISTIC_THRESHOLDS`（コード内）が正本。両者を混在させない。
"""

from __future__ import annotations

from collections import Counter
from pathlib import Path
from typing import Any

import yaml

from publishr_agents import run_pipeline
from publishr_schema import load_personas


ROOT = Path(__file__).resolve().parents[1]
EVAL_SET = ROOT / "eval" / "eval_set.yaml"

# 決定的チェックの閾値（mock pipeline 出力／eval_set 構造に対する床）。
# v2 eval_set.yaml には閾値を置かない（あちらは LLM-judge 用 expectedBand が正本）。
DETERMINISTIC_THRESHOLDS: dict[str, str] = {
    "plan_relevance": ">=4",
    "proposal_diversity": ">=4",
    "selection_adversarial": "== true",
    "author_voice_consistency": ">=4",
    "stocking_reason_credibility": ">=4",
    "eval_set_wellformed": "== true",
}

# v2 eval_set.yaml の cases 構成（meta.composition と一致）と帯の意味。
_EXPECTED_COMPOSITION = {"high_relevance": 4, "low_relevance": 2, "serendipity": 2}


def load_eval_set(path: Path = EVAL_SET) -> dict[str, Any]:
    """v2 eval_set.yaml を素直に読み込む（YAML）。"""
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f)


def load_eval_cases(path: Path = EVAL_SET) -> dict[str, dict[str, Any]]:
    """v2 の CIゲート用ケース（cases）を id -> {kind, expectedBand} で返す。"""
    data = load_eval_set(path)
    cases: dict[str, dict[str, Any]] = {}
    for case in data.get("cases", []) or []:
        cid = case.get("id")
        if cid is None:
            continue
        cases[cid] = {"kind": case.get("kind"), "expectedBand": case.get("expectedBand")}
    return cases


def _valid_band(band: Any) -> bool:
    return (
        isinstance(band, (list, tuple))
        and len(band) == 2
        and all(isinstance(v, int) for v in band)
        and 0 <= band[0] <= band[1] <= 100
    )


def validate_eval_set(path: Path = EVAL_SET) -> tuple[bool, str]:
    """v2 eval_set.yaml が CIゲートとして使える形か決定的に検証する。"""
    data = load_eval_set(path)
    cases = data.get("cases") or []
    problems: list[str] = []

    if len(cases) != 8:
        problems.append(f"cases must be 8, got {len(cases)}")

    kinds = Counter(c.get("kind") for c in cases)
    for kind, want in _EXPECTED_COMPOSITION.items():
        if kinds.get(kind, 0) != want:
            problems.append(f"{kind} must be {want}, got {kinds.get(kind, 0)}")

    for case in cases:
        cid = case.get("id", "?")
        band = case.get("expectedBand")
        if not _valid_band(band):
            problems.append(f"{cid}: invalid expectedBand {band!r}")
            continue
        if not case.get("plan"):
            problems.append(f"{cid}: missing plan")
        # 帯の意味：高関連は下限>=70、ずれは上限<=40、セレンディピティは中レンジに収める。
        kind = case.get("kind")
        lo, hi = band
        if kind == "high_relevance" and lo < 70:
            problems.append(f"{cid}: high_relevance lower band {lo} < 70")
        if kind == "low_relevance" and hi > 40:
            problems.append(f"{cid}: low_relevance upper band {hi} > 40")
        if kind == "serendipity" and (lo < 20 or hi > 70):
            problems.append(f"{cid}: serendipity band {band} outside [20,70]")

    ok = not problems
    detail = "8 cases well-formed" if ok else "; ".join(problems)
    return ok, detail


def _passes(score: int | bool, threshold: str) -> bool:
    if threshold == "== true":
        return score is True
    if threshold.startswith(">="):
        return int(score) >= int(threshold.removeprefix(">="))
    raise ValueError(f"unsupported threshold: {threshold}")


def _result(item_id: str, score: int | bool, detail: str) -> dict[str, Any]:
    threshold = DETERMINISTIC_THRESHOLDS[item_id]
    return {
        "id": item_id,
        "score": score,
        "threshold": threshold,
        "passed": _passes(score, threshold),
        "detail": detail,
    }


def _signal_keywords(signals: list[str]) -> list[str]:
    keywords: list[str] = []
    for signal in signals:
        if "管掌範囲" in signal:
            keywords.append("管掌範囲")
        if "1on1" in signal:
            keywords.append("1on1")
        if "属人化" in signal:
            keywords.append("属人化")
        if "定量" in signal:
            keywords.extend(["定量", "数字"])
    return list(dict.fromkeys(keywords))


def _score_from_count(count: int, full: int) -> int:
    if count >= full:
        return 5
    if count > 0:
        return 4
    return 1


def _has_persona_voice(book: Any, personas: dict[str, Any]) -> bool:
    persona = personas.get(book.author_persona_id)
    if not persona:
        return False
    text = f"{book.preface_sample} {' '.join(item.title + item.desc for item in book.agenda)}"
    return any(sig in text for sig in persona.persona.signature)


def evaluate_pipeline(user_id: str = "u_tadokoro") -> list[dict[str, Any]]:
    pipeline = run_pipeline(user_id)
    personas = {p.id: p for p in load_personas()}

    keywords = _signal_keywords(pipeline.observation.signals)
    reasons = " ".join(f"{p.reason} {p.reader_situation}" for p in pipeline.plans)
    signal_hits = [keyword for keyword in keywords if keyword in reasons]
    candidate_names = {c.candidate for c in pipeline.candidates}
    candidate_personas = {c.persona for c in pipeline.candidates}
    round1 = [e for e in pipeline.reject_log if e.round == 1]
    round2 = [e for e in pipeline.reject_log if e.round == 2]
    round2_verdicts = {e.verdict for e in round2}
    voice_hits = [book.id for book in pipeline.books if _has_persona_voice(book, personas)]

    plan_relevance_score = _score_from_count(len(signal_hits), 2)
    diversity_score = 5 if len(candidate_names) >= 3 and len(candidate_personas) >= 3 else 1
    selection_score = (
        bool(round1)
        and all(e.verdict == "却下" for e in round1)
        and "採用" in round2_verdicts
        and bool(round2_verdicts - {"採用"})
    )
    voice_score = _score_from_count(len(voice_hits), len(pipeline.books))
    stocking_score = 5 if ("30名" in reasons or "移行期" in reasons) and signal_hits else 1

    eval_set_ok, eval_set_detail = validate_eval_set()

    return [
        _result(
            "plan_relevance",
            plan_relevance_score,
            f"observation evidence referenced: {', '.join(signal_hits) or 'none'}",
        ),
        _result(
            "proposal_diversity",
            diversity_score,
            f"candidates={len(candidate_names)} personas={len(candidate_personas)}",
        ),
        _result(
            "selection_adversarial",
            selection_score,
            f"round1={len(round1)} round2Verdicts={sorted(round2_verdicts)}",
        ),
        _result(
            "author_voice_consistency",
            voice_score,
            f"voiceHits={voice_hits}",
        ),
        _result(
            "stocking_reason_credibility",
            stocking_score,
            "reader situation and observation evidence found"
            if stocking_score >= 4
            else "missing reader situation or observation evidence",
        ),
        _result("eval_set_wellformed", eval_set_ok, eval_set_detail),
    ]


def main() -> int:
    report = evaluate_pipeline()
    failed = [r for r in report if not r["passed"]]
    for row in report:
        mark = "PASS" if row["passed"] else "FAIL"
        print(f"{mark} {row['id']}: score={row['score']} threshold={row['threshold']} {row['detail']}")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
