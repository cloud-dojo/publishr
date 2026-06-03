"""Publishr MVP用の軽量Evalランナー。

外部LLMやYAML依存を使わず、`eval/eval_set.yaml` の id と
決定的パイプライン出力を照合する。
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from publishr_agents import run_pipeline
from publishr_schema import load_personas


ROOT = Path(__file__).resolve().parents[1]
EVAL_SET = ROOT / "eval" / "eval_set.yaml"


def load_eval_items(path: Path = EVAL_SET) -> dict[str, dict[str, str]]:
    items: dict[str, dict[str, str]] = {}
    current_id: str | None = None
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if stripped.startswith("- id:"):
            current_id = stripped.split(":", 1)[1].strip()
            items[current_id] = {}
        elif current_id and stripped.startswith("閾値:"):
            items[current_id]["threshold"] = stripped.split(":", 1)[1].strip().strip('"')
    return items


def load_eval_ids(path: Path = EVAL_SET) -> list[str]:
    return list(load_eval_items(path).keys())


def _passes(score: int | bool, threshold: str) -> bool:
    if threshold == "== true":
        return score is True
    if threshold.startswith(">="):
        return int(score) >= int(threshold.removeprefix(">="))
    raise ValueError(f"unsupported threshold: {threshold}")


def _result(item_id: str, score: int | bool, detail: str, items: dict[str, dict[str, str]]) -> dict[str, Any]:
    threshold = items[item_id]["threshold"]
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
    items = load_eval_items()
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

    return [
        _result(
            "plan_relevance",
            plan_relevance_score,
            f"observation evidence referenced: {', '.join(signal_hits) or 'none'}",
            items,
        ),
        _result(
            "proposal_diversity",
            diversity_score,
            f"candidates={len(candidate_names)} personas={len(candidate_personas)}",
            items,
        ),
        _result(
            "selection_adversarial",
            selection_score,
            f"round1={len(round1)} round2Verdicts={sorted(round2_verdicts)}",
            items,
        ),
        _result(
            "author_voice_consistency",
            voice_score,
            f"voiceHits={voice_hits}",
            items,
        ),
        _result(
            "stocking_reason_credibility",
            stocking_score,
            "reader situation and observation evidence found" if stocking_score >= 4 else "missing reader situation or observation evidence",
            items,
        ),
    ]


def main() -> int:
    eval_ids = set(load_eval_ids())
    report = evaluate_pipeline()
    missing = eval_ids - {r["id"] for r in report}
    failed = [r for r in report if not r["passed"]]
    for row in report:
        mark = "PASS" if row["passed"] else "FAIL"
        print(f"{mark} {row['id']}: score={row['score']} threshold={row['threshold']} {row['detail']}")
    if missing:
        print(f"FAIL missing eval implementations: {sorted(missing)}")
    return 1 if failed or missing else 0


if __name__ == "__main__":
    raise SystemExit(main())
