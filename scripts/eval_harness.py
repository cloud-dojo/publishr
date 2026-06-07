"""Publishr MVP用の軽量Evalランナー（mock決定的・オフライン）。

本ハーネスは **mock回帰の床（H0a）** として、外部LLM採点を使わず2系統を決定的に検証する：

1. **mock pipeline 出力の検証**（基準1の証跡）
   `PUBLISHR_LLM=mock` の決定的パイプライン出力を、観測根拠・企画多様性・選抜証跡
   （却下→再提出→採用）・著者ペルソナ声・入荷理由の5観点で照合する。
2. **eval/eval_set.yaml（v2）の構造検証**
   LLM-as-judge 用データセット（cases 8件・expectedBand 形式）が壊れていないことを
   決定的に確認する。実LLM/GEAP採点は本ハーネスとは分離（P6・`packages/prompts/eval_judge.md`）。
3. **採点系プロンプトの 良い例/悪い例 ↔ eval 兼用（C5.2・`check_fewshot_eval_alignment`）**
   採点系4本（leader/editor×2/judge）の ✅良い例/❌悪い例 を `packages/prompts/*.md`（単一正本）
   から読み、「良い例＝合格・悪い例＝不合格・eval_judge は `eval_set.yaml` の帯と整合」を
   決定的に回帰する。few-shot 注入（render.py）と同じ例を使い回す＝二重管理しない。

> 注: v2 `eval_set.yaml` は LLM-judge データセットであり、本ハーネスの決定的チェックの
> 閾値は `DETERMINISTIC_THRESHOLDS`（コード内）が正本。両者を混在させない。
"""

from __future__ import annotations

import json
import re
from collections import Counter
from pathlib import Path
from typing import Any

import yaml

from publishr_agents import run_pipeline
from publishr_agents.prompts.loader import load_prompt
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
        if "年上" in signal:
            keywords.append("年上")
        if "1on1" in signal:
            keywords.append("1on1")
        if "評価" in signal or "面談" in signal:
            keywords.append("評価")
        if "抱え" in signal or "権限" in signal:
            keywords.append("権限")
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


def evaluate_pipeline(user_id: str = "u_sakura") -> list[dict[str, Any]]:
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
    stocking_score = 5 if ("7名" in reasons or "昇格" in reasons or "新任マネージャー" in reasons) and signal_hits else 1

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


# ---------------------------------------------------------------------------
# C5.2: 採点系プロンプトの 良い例/悪い例 を eval fixture に「兼用」する決定的回帰。
#
# few-shot 側（良い例 → system 注入）は loader.py / render.py で配線済み。本節は
# その同じ例を「Eval 回帰アンカー」として読み直し、良い例＝合格・悪い例＝不合格・
# eval_judge は eval_set.yaml の expectedBand と整合、を実LLM無しで検証する。
# プロンプトの例を壊す編集（合計が崩れる・合格例が閾値割れ・帯外）は CI で落ちる。
# 正本は packages/prompts/*.md（新規 fixture ファイルは作らない＝二重管理しない）。
# ---------------------------------------------------------------------------

# 採点系プロンプトの閾値・観点（各 .md ヘッダ／README 規約と一致）。
SCORING_EXAMPLE_SPECS: dict[str, dict[str, Any]] = {
    "step2_plan_leader": {
        "threshold": 70,
        "fields": ["relevance", "differentiation", "researchUse", "titleHook"],
        "floor": 10,
        "floor_fields": ["relevance"],  # 読者局面の足切り（<10 で不合格）
    },
    "step4_editor_preview": {
        "threshold": 50,
        "fields": ["rawInsight", "personaForward", "catchiness"],
        "floor": 10,
        "floor_fields": ["rawInsight", "personaForward", "catchiness"],  # どの観点も10以上
    },
    "modeB_editor_body": {
        "threshold": 70,
        "fields": ["coherence", "hook", "relevance", "personaConsistency", "actionability"],
        "uses_weak_chapters": True,
    },
}

_TRAILING_COMMA = re.compile(r",(\s*[}\]])")


def _strip_jsonc(text: str) -> str:
    """jsonc（// 行・/* */ ブロックコメント）からコメントを除去。文字列内は保護。"""
    out: list[str] = []
    in_str = esc = False
    i, n = 0, len(text)
    while i < n:
        ch = text[i]
        if in_str:
            out.append(ch)
            if esc:
                esc = False
            elif ch == "\\":
                esc = True
            elif ch == '"':
                in_str = False
            i += 1
            continue
        if ch == '"':
            in_str = True
            out.append(ch)
            i += 1
        elif ch == "/" and i + 1 < n and text[i + 1] == "/":
            while i < n and text[i] != "\n":
                i += 1
        elif ch == "/" and i + 1 < n and text[i + 1] == "*":
            i += 2
            while i + 1 < n and not (text[i] == "*" and text[i + 1] == "/"):
                i += 1
            i += 2
        else:
            out.append(ch)
            i += 1
    return "".join(out)


def _parse_jsonc_objects(text: str) -> list[dict[str, Any]]:
    """jsonc ブロックからトップレベルの {...} を全て取り出して JSON パースする。"""
    s = _TRAILING_COMMA.sub(r"\1", _strip_jsonc(text))
    objs: list[dict[str, Any]] = []
    depth = 0
    start: int | None = None
    in_str = esc = False
    for i, ch in enumerate(s):
        if in_str:
            if esc:
                esc = False
            elif ch == "\\":
                esc = True
            elif ch == '"':
                in_str = False
            continue
        if ch == '"':
            in_str = True
        elif ch == "{":
            if depth == 0:
                start = i
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0 and start is not None:
                objs.append(json.loads(s[start : i + 1]))
                start = None
    return objs


def _check_scoring_verdict(
    obj: dict[str, Any], spec: dict[str, Any], *, expect_pass: bool
) -> tuple[bool, str]:
    """1件の採点結果が「合格として/不合格として」自己整合かを判定する。"""
    fields = spec["fields"]
    threshold = spec["threshold"]
    breakdown = obj.get("scoreBreakdown") or {}
    score = obj.get("score")
    decision = obj.get("decision")
    notes: list[str] = []

    field_sum = sum(breakdown.get(f, 0) for f in fields)
    sum_ok = score == field_sum
    if not sum_ok:
        notes.append(f"breakdown sum {field_sum} != score {score}")

    floor = spec.get("floor")
    floor_breach = floor is not None and any(
        breakdown.get(f, 0) < floor for f in spec.get("floor_fields", [])
    )
    below_floor_flag = bool(obj.get("belowFloor"))
    weak = obj.get("weakChapters") or []
    weak_breach = bool(spec.get("uses_weak_chapters")) and len(weak) > 0

    if expect_pass:
        if decision != "approve":
            notes.append(f"decision={decision!r} (want approve)")
        if not isinstance(score, int) or score < threshold:
            notes.append(f"score {score} < threshold {threshold}")
        if floor_breach:
            notes.append("floor breach")
        if below_floor_flag:
            notes.append("belowFloor=true")
        if weak_breach:
            notes.append(f"weakChapters={weak}")
        ok = (
            decision == "approve"
            and isinstance(score, int)
            and score >= threshold
            and sum_ok
            and not floor_breach
            and not below_floor_flag
            and not weak_breach
        )
        return ok, "; ".join(notes) or "approve-consistent"

    fail_trigger = (
        (isinstance(score, int) and score < threshold)
        or floor_breach
        or below_floor_flag
        or weak_breach
    )
    if decision != "revise":
        notes.append(f"decision={decision!r} (want revise)")
    if not fail_trigger:
        notes.append(f"no fail trigger (score {score}, threshold {threshold})")
    ok = decision == "revise" and sum_ok and fail_trigger
    return ok, "; ".join(notes) or "revise-consistent"


def _check_judge_alignment() -> list[dict[str, Any]]:
    """eval_judge の例を eval_set.yaml の expectedBand と相互参照する。"""
    doc = load_prompt("eval_judge")
    cases = load_eval_cases()
    rows: list[dict[str, Any]] = []

    # 良い例: eval_set にひもづく各オブジェクトの score が帯の中。
    good_notes: list[str] = []
    checked = 0
    good_ok = True
    for obj in _parse_jsonc_objects(doc.good_example or ""):
        cid, score = obj.get("id"), obj.get("score")
        band = (cases.get(cid) or {}).get("expectedBand")
        if cid is None or score is None or not _valid_band(band):
            continue
        checked += 1
        if not (band[0] <= score <= band[1]):
            good_ok = False
            good_notes.append(f"{cid} score {score} outside band {band}")
    if checked == 0:
        good_ok = False
        good_notes.append("no eval_set-linked objects found")
    rows.append(
        {
            "id": "fewshot_eval_judge_good",
            "passed": good_ok,
            "detail": "; ".join(good_notes) or f"{checked} judge scores within band",
        }
    )

    # 悪い例: 「悪い挙動」＝落とすべき案を帯の外（甘く）採点していること。
    bad_notes: list[str] = []
    bad_ok = False
    for obj in _parse_jsonc_objects(doc.bad_example or ""):
        cid, score = obj.get("id"), obj.get("score")
        band = (cases.get(cid) or {}).get("expectedBand")
        if cid is None or score is None or not _valid_band(band):
            continue
        if not (band[0] <= score <= band[1]):
            bad_ok = True
            bad_notes.append(f"{cid} score {score} correctly outside band {band}")
    if not bad_ok:
        bad_notes.append("bad example does not fall outside any eval_set band")
    rows.append(
        {"id": "fewshot_eval_judge_bad", "passed": bad_ok, "detail": "; ".join(bad_notes)}
    )
    return rows


def check_fewshot_eval_alignment() -> list[dict[str, Any]]:
    """採点系プロンプトの 良い例/悪い例 と eval 帯・閾値の整合を決定的に検証する。"""
    rows: list[dict[str, Any]] = []
    for role, spec in SCORING_EXAMPLE_SPECS.items():
        doc = load_prompt(role)
        for kind, expect_pass, raw in (
            ("good", True, doc.good_example),
            ("bad", False, doc.bad_example),
        ):
            rid = f"fewshot_{role}_{kind}"
            if not raw:
                rows.append({"id": rid, "passed": False, "detail": "example block missing"})
                continue
            objs = _parse_jsonc_objects(raw)
            if not objs:
                rows.append({"id": rid, "passed": False, "detail": "no JSON object parsed"})
                continue
            ok, detail = _check_scoring_verdict(objs[0], spec, expect_pass=expect_pass)
            rows.append({"id": rid, "passed": ok, "detail": detail})
    rows.extend(_check_judge_alignment())
    return rows


def main() -> int:
    report = evaluate_pipeline()
    alignment = check_fewshot_eval_alignment()
    failed = [r for r in report if not r["passed"]] + [r for r in alignment if not r["passed"]]
    for row in report:
        mark = "PASS" if row["passed"] else "FAIL"
        print(f"{mark} {row['id']}: score={row['score']} threshold={row['threshold']} {row['detail']}")
    for row in alignment:
        mark = "PASS" if row["passed"] else "FAIL"
        print(f"{mark} {row['id']}: {row['detail']}")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
