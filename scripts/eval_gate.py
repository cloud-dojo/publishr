"""C5.3 Eval judge ゲート（CI品質ゲート・MVP §9 / I-21）。

eval_set.yaml の cases(8) を judge で採点し、各ケースの expectedBand に収まれば「正答」。
ceil(87.5%)=8件中7件 正答でゲート通過、未満なら exit 1（CIがデプロイを止める）。
borderlineCases(2) は閾値70近傍の判別力チェック＝**診断専用**でゲート計算には含めない（I-21）。

judge backend:
  - mock（既定・CI常用）: 決定的ルーブリック採点（4観点×0-25・$0・オフライン）。
    判定根拠は readerProfile への踏み込み(relevance)/固有局面の差別化(differentiation)/
    観測grounding(researchUse)/タイトルのエッジ(titleHook)。`kind`/`expectedBand` は読まない。
    serendipity（教養/越境シグナルで内容検知）は①③④を読み替えて採点（嗜好整合・素材反映・
    問いかけ型フック）。閾値はhonmeiと同じ70（旧中レンジclamp[35,58]は2026-06-12廃止）。
  - vertex: 実 Gemini Pro judge（eval_judge.md ルーブリック・readerProfile＋plan を採点）。
    **課金**。`GOOGLE_GENAI_USE_VERTEXAI=TRUE`＋`GOOGLE_CLOUD_PROJECT/LOCATION`（ADC）が要る。
    C5.4 再現性・C5.5 閾値微調整はこの backend で実データを測る。GEAP（vertexai.evaluation）は
    本番ゲート寄せの別案として温存。

  uv run python -m scripts.eval_gate            # mock ゲート（$0・CI常用）
  uv run python -m scripts.eval_gate --backend vertex   # 実judge（Gemini Pro・課金）
"""

from __future__ import annotations

import argparse
import json
import math
import os
import sys
from pathlib import Path
from typing import Any, Optional

import yaml

ROOT = Path(__file__).resolve().parents[1]
EVAL_SET = ROOT / "eval" / "eval_set.yaml"

# --- 決定的 mock judge: 4観点 × 0-25（合計0-100・閾値70） --------------------
_RELEVANCE_KW = [
    "新任", "課長", "マネージャ", "マネジメント", "年上", "佐藤", "任せ", "委譲", "権限",
    "評価", "面談", "リニューアル", "しずく", "役員", "報告", "意思決定", "1on1", "部下",
    "チーム", "ブランド", "パーパス",
]
_GENERIC_TITLE_KW = ["入門", "教科書", "の基礎", "ロードマップ", "すべての", "5つの", "術"]
_SPECIFIC_DIFF_KW = ["限定", "固有", "具体", "marketGap", "局面", "に絞", "寄せ", "越境", "同時並行", "優先順位"]
_GENERIC_DIFF_KW = ["特になし", "一般的", "網羅", "体系的"]
_EVIDENCE_KW = [
    "メモ", "議事", "報告", "定例", "記入", "drive", "cal", "tsk", "drv_", "tasks",
    "就任", "戦略メモ", "企画書",
]
_MISS_MARK = "あえて外す"
# 教養/越境（業務外の教養テーマ）シグナル＝serendipity検知。
_SERENDIPITY_KW = ["越境", "教養", "隣接領域", "宗教", "哲学", "思想", "信仰"]
# serendipity の①読み替え（2026-06-12・旧中レンジclamp[35,58]を廃止）:
# ①は「嗜好・許容度との整合」で測る。形式整合（読み切り/ストーリー/追体験等＝
# readingGenres「事例・ストーリーで学ぶ」への適合）と読者語彙との接点密度を見る。
# ③は観測groundingでなく「教養素材（歴史・宗教等のフレーム・marketGap）の反映」を見る
# （whyNowForYou が課題・観測に言及しないのは棚書き文法＝仕様のため）。
_SERENDIPITY_FIT_KW = ["ストーリー", "読み切り", "追体験", "疑似体験", "対話", "事例", "物語", "ショート"]
_SERENDIPITY_MATERIAL_KW = [
    "歴史", "興亡", "宗教", "哲学", "思想", "古典", "文明", "制度", "共同体", "信仰", "物語", "marketGap",
]


def _count(text: str, kws: list[str]) -> int:
    """マッチした「種類」数（presence）。"""
    return sum(1 for k in kws if k in text)


def _occ(text: str, kws: list[str]) -> int:
    """総出現回数（on-topic の密度を見る）。"""
    return sum(text.count(k) for k in kws)


def judge_plan_mock(plan: dict[str, Any]) -> dict[str, int]:
    """企画(PlanProposal)を4観点×0-25で決定的に採点する（mock judge）。"""
    title = str(plan.get("tentativeTitle", ""))
    diff = str(plan.get("diffFromMarket", ""))
    why = str(plan.get("whyNowForYou", ""))
    parts = [title, str(plan.get("readerSituation", "")), why, str(plan.get("coreMessage", ""))]
    parts += [str(x) for x in plan.get("keyInsights", [])]
    parts += [str(x) for x in plan.get("agendaOutline", [])]
    body = " ".join(parts)

    sbody = body + " " + diff
    serendipity = _count(sbody, _SERENDIPITY_KW) > 0

    # ②differentiation: 固有局面への具体化。specific 語があれば「〜でなく一般的」の否定形に騙されない。
    # （honmei/serendipity 共通）
    spec = _count(diff, _SPECIFIC_DIFF_KW)
    if spec == 0 and any(g in diff for g in _GENERIC_DIFF_KW):
        differentiation = 5
    else:
        differentiation = min(25, 8 + spec * 6)

    if serendipity:
        # ①読み替え: 嗜好・許容度との整合（形式整合シグナル＋読者語彙との接点密度）
        relevance = min(25, 9 + _count(sbody, _SERENDIPITY_FIT_KW) * 3 + min(_occ(sbody, _RELEVANCE_KW), 8))
        # ③読み替え: 教養素材（歴史・宗教等のフレーム・marketGap）の反映
        research = min(25, 9 + _count(sbody, _SERENDIPITY_MATERIAL_KW) * 3)
        # ④: 問いかけ型のフック＋素材・形式の固有性
        question = 4 if ("？" in title or "?" in title or "なぜ" in title) else 0
        title_hook = min(25, 9 + question + _count(title, _SERENDIPITY_FIT_KW + _SERENDIPITY_MATERIAL_KW) * 3)
    else:
        # ①relevance: 読者の局面語の出現密度
        relevance = min(25, _occ(body, _RELEVANCE_KW) * 3)
        # ③researchUse: 観測 grounding（あえて外す=未接地）
        if _MISS_MARK in why:
            research = 2
        else:
            research = min(25, _count(why, _EVIDENCE_KW) * 7)
        # ④titleHook: タイトルの局面エッジ。一般的な定型語は減点。
        title_hook = min(25, 6 + _occ(title, _RELEVANCE_KW) * 6)
        if any(g in title for g in _GENERIC_TITLE_KW):
            title_hook = min(title_hook, 8)

    total = relevance + differentiation + research + title_hook
    return {
        "relevance": relevance,
        "differentiation": differentiation,
        "researchUse": research,
        "titleHook": title_hook,
        "raw": total,
        "serendipity": serendipity,
        "total": total,
    }


def _normalize_judge_json(data: dict[str, Any]) -> dict[str, int]:
    """judge の JSON（`{score, scoreBreakdown:{4観点}, ...}`）を mock 互換 dict に整える。

    各観点 0-25 / total 0-100 にクランプ。score 欠落時は4観点の合計で埋める。run_gate は
    total のみ使うが、breakdown 表示・再現性ハーネスのため全キーを返す。
    """
    bd = data.get("scoreBreakdown") or {}

    def _axis(key: str) -> int:
        try:
            return max(0, min(25, int(bd.get(key, 0))))
        except (TypeError, ValueError):
            return 0

    relevance = _axis("relevance")
    differentiation = _axis("differentiation")
    research = _axis("researchUse")
    title = _axis("titleHook")
    raw = relevance + differentiation + research + title
    try:
        total = int(data.get("score", raw))
    except (TypeError, ValueError):
        total = raw
    total = max(0, min(100, total))
    return {
        "relevance": relevance,
        "differentiation": differentiation,
        "researchUse": research,
        "titleHook": title,
        "raw": raw,
        # 実judgeは eval_judge.md のルーブリック側で serendipity ①読み替えを行う＝コード側では何もしない。
        "serendipity": False,
        "total": total,
    }


def _loads_judge_response(text: Optional[str]) -> dict[str, Any]:
    """実judgeの応答テキストを JSON 化する。

    `resp.text` は None になりうる（finish_reason=SAFETY/MAX_TOKENS 等で text part 無し）ので
    明確に失敗させる。response_mime_type=json でも稀に ```json フェンスが付くので剥がす。
    """
    if not text or not isinstance(text, str):
        raise ValueError("judge 応答が空です（SAFETY/MAX_TOKENS 等で本文なしの可能性）")
    s = text.strip()
    if s.startswith("```"):
        s = s[3:]
        if s[:4].lower() == "json":
            s = s[4:]
        if s.endswith("```"):
            s = s[:-3]
        s = s.strip()
    return json.loads(s)


def _judge_user_content(plan: dict[str, Any], reader_profile: Optional[dict[str, Any]]) -> str:
    """judge へ渡す user コンテンツ（readerProfile＋plan）を組む。

    eval_set.yaml は YAML 由来で `date` 等の非JSON型を含むため `default=str` で文字列化する。
    """
    parts: list[str] = []
    if reader_profile is not None:
        parts.append(
            "読者プロファイル:\n"
            + json.dumps(reader_profile, ensure_ascii=False, indent=2, default=str)
        )
    parts.append(
        "採点対象の企画(PlanProposal):\n" + json.dumps(plan, ensure_ascii=False, indent=2, default=str)
    )
    parts.append("上記を4観点（各0〜25）で採点し、指定のJSONのみを返してください。")
    return "\n\n".join(parts)


def judge_plan_vertex(
    plan: dict[str, Any], *, reader_profile: Optional[dict[str, Any]] = None
) -> dict[str, int]:
    """実 Gemini Pro で企画を採点する（eval_judge.md ルーブリック・4観点×0-25）。

    **GCP課金**。`GOOGLE_GENAI_USE_VERTEXAI=TRUE` ＋ `GOOGLE_CLOUD_PROJECT/LOCATION`
    （既定 publishr-498123 / asia-northeast1）が要る。judge は readerProfile＋plan を読むので
    （eval_judge.md I/O）reader_profile を渡す。temperature は `PUBLISHR_JUDGE_TEMPERATURE`
    （既定0.0＝最も再現的・C5.4 はこれを上げて実ブレを測る）。mock 互換 dict を返す。
    """
    from google import genai  # noqa: PLC0415 — vertex 経路のみ遅延 import（mock床を汚さない）
    from google.genai import types  # noqa: PLC0415

    from publishr_agents.llm.provider import model_for  # noqa: PLC0415
    from publishr_agents.prompts.loader import load_prompt  # noqa: PLC0415

    os.environ.setdefault("GOOGLE_GENAI_USE_VERTEXAI", "TRUE")
    project = os.environ.get("GOOGLE_CLOUD_PROJECT", "publishr-498123")
    location = os.environ.get("GOOGLE_CLOUD_LOCATION", "asia-northeast1")
    model = model_for("eval_judge")  # role→モデルの単一正本（PUBLISHR_MODEL_PRO で上書き可）
    temperature = float(os.environ.get("PUBLISHR_JUDGE_TEMPERATURE", "0.0"))

    doc = load_prompt("eval_judge")
    system = doc.system
    if doc.good_example:  # few-shot 校正アンカー（registry: eval_judge は fewshot 常時ON）
        system += "\n\n# 採点例（校正アンカー）\n" + doc.good_example

    client = genai.Client(vertexai=True, project=project, location=location)
    resp = client.models.generate_content(
        model=model,
        contents=_judge_user_content(plan, reader_profile),
        config=types.GenerateContentConfig(
            system_instruction=system,
            temperature=temperature,
            response_mime_type="application/json",
        ),
    )
    return _normalize_judge_json(_loads_judge_response(resp.text))


def judge_plan(
    plan: dict[str, Any],
    *,
    backend: str = "mock",
    reader_profile: Optional[dict[str, Any]] = None,
) -> dict[str, int]:
    if backend == "vertex":
        return judge_plan_vertex(plan, reader_profile=reader_profile)
    return judge_plan_mock(plan)


def load_eval_set(path: Path = EVAL_SET) -> dict[str, Any]:
    with open(path, encoding="utf-8") as f:
        return yaml.safe_load(f)


def run_gate(eval_set: dict[str, Any], *, backend: str = "mock") -> dict[str, Any]:
    """cases を採点し、expectedBand 内なら正答。ceil(87.5%) 正答で通過。borderline は診断専用。"""
    reader_profile = eval_set.get("readerProfile")
    cases = eval_set.get("cases", [])
    results: list[dict[str, Any]] = []
    for c in cases:
        scored = judge_plan(c["plan"], backend=backend, reader_profile=reader_profile)
        lo, hi = c["expectedBand"]
        results.append(
            {
                "id": c["id"],
                "kind": c.get("kind"),
                "score": scored["total"],
                "band": [lo, hi],
                "passed": lo <= scored["total"] <= hi,
                "breakdown": scored,
            }
        )

    diagnostics: list[dict[str, Any]] = []
    for c in eval_set.get("borderlineCases", []):
        scored = judge_plan(c["plan"], backend=backend, reader_profile=reader_profile)
        lo, hi = c["expectedBand"]
        diagnostics.append(
            {
                "id": c["id"],
                "kind": c.get("kind"),
                "score": scored["total"],
                "band": [lo, hi],
                "inBand": lo <= scored["total"] <= hi,
            }
        )

    n_pass = sum(1 for r in results if r["passed"])
    required = math.ceil(0.875 * len(cases)) if cases else 0
    return {
        "results": results,
        "diagnostics": diagnostics,
        "passed": n_pass,
        "required": required,
        "total": len(cases),
        "gate_pass": n_pass >= required,
    }


def _harden_windows_tls() -> None:
    """企業TLS検査プロキシ下の Windows 機向け TLS 対策（memory: publishr-windows-vertex-ssl）。

    1) SSLKEYLOGFILE を外す（OpenSSL native crash 回避）。2) truststore を注入（社内CAの厳格X.509拒否回避）。
    実Vertex（google.genai HTTPS）を叩く --backend vertex 経路でのみ必要（mock は不要）。
    """
    os.environ.pop("SSLKEYLOGFILE", None)
    try:
        import truststore  # noqa: PLC0415

        truststore.inject_into_ssl()
    except ImportError:
        sys.stderr.write(
            "[注意] truststore 未インストール。社内プロキシ下では証明書検証に失敗する可能性。\n"
            "        次で再実行: uv run --with truststore python -m scripts.eval_gate --backend vertex\n"
        )


def main(argv: Optional[list[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="C5.3 Eval judge ゲート")
    parser.add_argument(
        "--backend",
        default=os.environ.get("PUBLISHR_EVAL_BACKEND", "mock"),
        choices=["mock", "vertex"],
    )
    args = parser.parse_args(argv)
    if args.backend == "vertex":
        _harden_windows_tls()  # Windows企業TLS回避（実Vertex呼び出し前・mockは不要）

    rep = run_gate(load_eval_set(), backend=args.backend)
    print(
        f"== Eval judge ゲート（backend={args.backend}・正答=expectedBand内・"
        f"通過条件={rep['required']}/{rep['total']}） =="
    )
    for r in rep["results"]:
        mark = "PASS" if r["passed"] else "FAIL"
        b = r["breakdown"]
        srd = " serendipity=①読み替え" if b.get("serendipity") else ""
        print(
            f"{mark} {r['id']} [{r['kind']}] score={r['score']} band={r['band']} "
            f"(rel={b['relevance']} diff={b['differentiation']} res={b['researchUse']} title={b['titleHook']}{srd})"
        )
    print("-- borderline（閾値70近傍の判別力・診断専用・ゲート対象外） --")
    for d in rep["diagnostics"]:
        print(f"  {'in ' if d['inBand'] else 'OUT'} {d['id']} [{d['kind']}] score={d['score']} band={d['band']}")
    verdict = "PASS（デプロイ可）" if rep["gate_pass"] else "FAIL（デプロイ停止）"
    print(f"\nゲート: {rep['passed']}/{rep['total']} 正答（要 {rep['required']}）→ {verdict}")
    return 0 if rep["gate_pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
