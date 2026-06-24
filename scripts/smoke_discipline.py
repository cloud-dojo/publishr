"""STEP1–5 プロンプト規律スモーク（決定的・オフライン・$0）。

Gemini投入前の **プレフィルター**。被験者（Claude Agent）が生成した各STEPの出力JSONを
受け取り、モデル非依存で効く「規律違反」を決定的に検出する：

- schema汚染（フィールド名創作・想定外フィールド）  ← 確定違反
- 採点の自己整合（4観点和==score・floor・decision）   ← 確定違反（eval_harness再利用）
- approvedPlan 無改変（leaderがplanを書き換えていないか）← 確定違反
- claim/source 形式・必須項目充足                      ← 確定違反
- role越境 / 感情創作 / few-shot汚染 / 棚書き文法      ← 候補フラグ（最終判定はLLM採点役）

絶対品質の最終判定はGemini実機（scripts/eval_gate.py --backend vertex / AI Studio手動）に
委譲する。本モジュールは Claude/Vertex を一切呼ばない純粋関数＝CLAUDE.mdの「決定的層」。

非重複: eval_harness/eval_gate は eval/eval_set.yaml 8件の **CIゲート**。本モジュールは
任意ペルソナ×テーマで被験者が **実生成** した出力を検査する **改修インナーループ**。役割が違う。

  uv run python -m scripts.smoke_discipline --role plan_owner --input out.json
  uv run python -m scripts.smoke_discipline --role plan_leader --input verdict.json --context ctx.json
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional, get_args, get_origin

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from pydantic import BaseModel, ValidationError  # noqa: E402

from publishr_agents.prompts.loader import load_prompt  # noqa: E402
from publishr_agents.prompts.registry import spec_for  # noqa: E402
from scripts.eval_harness import (  # noqa: E402  — 採点整合は単一正本を再利用（二重管理しない）
    SCORING_EXAMPLE_SPECS,
    _check_scoring_verdict,
)

GEMINI_GATE_NOTE = (
    "⚠️ 最終ゲートは Gemini 実機です。本スモークは規律違反の自動検出＋候補フラグによる\n"
    "   プロンプト改修のインナーループで、絶対品質の合否は\n"
    "   `scripts/eval_gate.py --backend vertex`（実 Gemini Pro judge）または\n"
    "   AI Studio 手動貼り付け（publishr_other/aistudio_paste/）が下します。\n"
    "   WebSearch 書誌照合は Gemini grounding の近似で別物です。"
)

# role → SCORING_EXAMPLE_SPECS のキー（採点系のみ）
_SCORING_SPEC_KEY = {
    "plan_leader": "step2_plan_leader",
    "editor_preview": "step4_editor_preview",
    "modeb_editor": "modeB_editor_body",
}

# role越境シグナル（調査サブが企画担当者の仕事に踏み込んでいないか）。ヒットは候補フラグ＝LLMが確定。
_OVERREACH_KW: dict[str, list[str]] = {
    "sub_market": ["本書は", "本書", "企画案", "コンセプト", "タイトル案", "超訳", "ハウツー化", "実用書化", "と銘打"],
    "sub_theme_insight": ["本書は", "本書", "企画案", "章立て案", "コンセプト", "タイトル案"],
    "sub_reader_context": ["本書は", "企画案", "タイトル案"],
}
# 感情語（観測に本人の言葉として記述がなければ創作＝違反候補。スキャンはヒットのみ・判定はLLM）。
_EMOTION_KW = [
    "焦り", "焦って", "不安", "追い詰め", "萎縮", "恐れ", "怯え", "おびえ",
    "孤独", "重圧", "プレッシャー", "パニック", "絶望", "苦悩",
]
# ハウツー化シグナル（serendipityで約束してはいけない即効解決）。
_HOWTO_KW = ["すぐ使える", "ハウツー", "明日から", "即効", "ステップバイステップ", "実践テクニック", "型として持"]
# 読者の課題への直接言及（serendipity③＝棚書き文法では出てはいけない）。
_TASK_REF_KW = ["あなたの悩み", "あなたの課題", "お悩み", "直面する課題", "抱える問題", "あなたが抱える"]

# serendipity_themes（SerendipitySet）: 4テーマ・adjacency（隣接/反対/飛躍/ニッチ）で分散。
_SERENDIPITY_COUNT = 4
_ADJACENCY_KINDS = ["隣接", "反対", "飛躍", "ニッチ"]

# ── STEP3 persona（員数4・voiceStyle×format 2軸分散・薄さ・fromFavorite・人物名衝突） ──
# v3（4テーマ1-1-1-1）: persona_generator は1コール4人（1人/冊）。author_casting は1企画＝候補3→選抜1。
_PERSONA_COUNT = 4           # persona_generator（GeneratedPersonaSet.personas）= 4人
_AUTHOR_CANDIDATE_COUNT = 3  # author_casting（AuthorCasting.candidates）= 候補3人
_PERSONA_MIN_LEN = 60  # persona 本体の下限文字数（薄さ検出の目安）
# persona の「作り込み」シグナル（原体験・口癖・思想・経歴）。皆無＝薄さフラグ。
_PERSONA_RICH_KW = ["元", "原体験", "口癖", "信条", "経験", "出身", "歴", "『", "「", "を経て", "出会"]
# 既知の衝突名（読者本人・デモ登場人物・step3 few-shot 例の架空著者）。一致＝知財/整合の要確認フラグ。
# 過検出は許容（フラグ＝採点役が確定）。固有名は適宜追加する。
_KNOWN_NAMES = [
    "佐倉美咲", "三田裕樹", "田所", "高村", "佐々木", "佐藤健一",  # 読者本人・デモ登場人物
    "神崎玄一郎", "里見ほたる",  # step3 ✅良い出力例の架空著者（few-shot フルネーム コピー検出）
    "神崎", "里見",  # ↑の姓のみ流用（「里見ほのか」等）も few-shot 汚染として検出
]


# ── pydantic スキーマからの許可キー集合・未知フィールド再帰検出 ───────────────
def _model_of(annotation: Any) -> Optional[type[BaseModel]]:
    """list[Model] / Optional[Model] / Model からネストの BaseModel 型を取り出す。"""
    if isinstance(annotation, type) and issubclass(annotation, BaseModel):
        return annotation
    if get_origin(annotation) is None:
        return None
    for arg in get_args(annotation):
        m = _model_of(arg)
        if m:
            return m
    return None


def _allowed_keys(model_cls: type[BaseModel]) -> set[str]:
    keys: set[str] = set()
    for name, fi in model_cls.model_fields.items():
        keys.add(name)
        if fi.alias:
            keys.add(fi.alias)
    return keys


def _unknown_fields(model_cls: type[BaseModel], raw: Any, path: str = "") -> list[str]:
    """raw に含まれる「スキーマ未定義のキー」をネスト込みで列挙（フィールド名創作の検出）。

    pydantic は extra=ignore で未知キーを黙って捨てるため validate では検出できない。手動照合する。
    """
    if not isinstance(raw, dict):
        return []
    allowed = _allowed_keys(model_cls)
    child: dict[str, type[BaseModel]] = {}
    for name, fi in model_cls.model_fields.items():
        m = _model_of(fi.annotation)
        if m:
            child[name] = m
            if fi.alias:
                child[fi.alias] = m
    out: list[str] = []
    for k, v in raw.items():
        # `_meta` 等の `_` 始まりは fixture の注釈（モデル出力ではない）＝スキーマ汚染と見なさない。
        if isinstance(k, str) and k.startswith("_"):
            continue
        p = f"{path}{k}"
        if k not in allowed:
            out.append(p)
            continue
        if k in child:
            if isinstance(v, dict):
                out += _unknown_fields(child[k], v, p + ".")
            elif isinstance(v, list):
                for i, item in enumerate(v):
                    out += _unknown_fields(child[k], item, f"{p}[{i}].")
    return out


def validate_output(role: str, raw: dict[str, Any]) -> tuple[bool, Optional[BaseModel], list[str], list[str]]:
    """role の output_schema で検証。戻り: (schema_ok, parsed, unknown_fields, errors)。"""
    schema = spec_for(role).output_schema
    if schema is None:  # cover / modeb_author 等：スキーマ無し（決定的schemaチェック対象外）
        return True, None, [], []
    unknown = _unknown_fields(schema, raw)
    try:
        parsed = schema.model_validate(raw)
        return True, parsed, unknown, []
    except ValidationError as exc:
        errs = [f"{'.'.join(str(x) for x in e['loc'])}: {e['msg']}" for e in exc.errors()]
        return False, None, unknown, errs


# ── 必須非空 ───────────────────────────────────────────────
_REQUIRED_STR = {
    "plan_owner": ["tentative_title", "reader_situation", "why_now_for_you", "core_message", "diff_from_market"],
}
_REQUIRED_LIST = {
    "plan_owner": ["key_insights", "agenda_outline", "recommended_author_types"],
    "sub_reader_context": ["pain_points", "decisions", "evidence"],
    "sub_market": ["findings"],
    "sub_theme_insight": ["key_points"],
    "persona_generator": ["personas"],
}


def check_required_nonempty(role: str, parsed: BaseModel) -> list[str]:
    out: list[str] = []
    for f in _REQUIRED_STR.get(role, []):
        if not str(getattr(parsed, f, "") or "").strip():
            out.append(f"必須項目が空: {f}")
    for f in _REQUIRED_LIST.get(role, []):
        if not (getattr(parsed, f, None) or []):
            out.append(f"必須リストが空: {f}")
    return out


# ── テキストスキャン（候補フラグ） ─────────────────────────────
def _scan(text: str, kws: list[str]) -> list[str]:
    return [k for k in kws if k in (text or "")]


def scan_role_overreach(role: str, raw: dict[str, Any]) -> list[str]:
    kws = _OVERREACH_KW.get(role, [])
    if not kws:
        return []
    blob = json.dumps(raw, ensure_ascii=False)
    return _scan(blob, kws)


def scan_emotion_injection(text: str) -> list[str]:
    return _scan(text, _EMOTION_KW)


# ── few-shot 汚染（参考例との酷似）・marketGap 引用率 ─────────────
def _char_ngrams(s: str, n: int = 3) -> set[str]:
    s = "".join((s or "").split())
    return {s[i : i + n] for i in range(len(s) - n + 1)} if len(s) >= n else set()


def _jaccard(a: set[str], b: set[str]) -> float:
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def fewshot_contamination_score(output_text: str, good_example: str) -> float:
    """出力と good_example の文字3-gram Jaccard 類似率（1に近いほど例のコピー疑い）。"""
    return round(_jaccard(_char_ngrams(output_text), _char_ngrams(good_example)), 3)


def check_marketgap_citation(diff_from_market: str, market_gap: str) -> float:
    """diffFromMarket が subMarket.marketGap を引いているかの語彙重複率（低いと未引用疑い）。"""
    return round(_jaccard(_char_ngrams(diff_from_market, 2), _char_ngrams(market_gap, 2)), 3)


# ── evidence 接地・claim/source 形式 ──────────────────────────
def check_evidence_binding(role: str, parsed: BaseModel) -> list[str]:
    out: list[str] = []
    if role == "reader_analyst":
        cw = getattr(parsed, "current_work", None)
        challenges = getattr(cw, "challenges", []) if cw else []
        evidence = getattr(cw, "evidence", []) if cw else []
        if challenges and not evidence:
            out.append("challengesがあるのにevidenceが空（接地なし）")
        for i, e in enumerate(evidence):
            if not str(getattr(e, "claim", "") or "").strip():
                out.append(f"evidence[{i}].claim が空")
    if role == "sub_reader_context":
        for i, e in enumerate(getattr(parsed, "evidence", []) or []):
            if not str(getattr(e, "claim", "") or "").strip() or not str(getattr(e, "source", "") or "").strip():
                out.append(f"evidence[{i}] の claim/source が1対1で揃っていない")
    return out


# ── 採点系の自己整合・approvedPlan 無改変 ─────────────────────
_VERDICT_PLAN_FIELDS = [
    "tentativeTitle", "readerSituation", "whyNowForYou", "coreMessage",
    "diffFromMarket", "keyInsights", "agendaOutline", "recommendedAuthorTypes",
]


def check_scoring_consistency(role: str, raw: dict[str, Any]) -> Optional[tuple[bool, str]]:
    """採点系（leader/editor）の self-consistency を eval_harness のロジックで再利用判定。"""
    key = _SCORING_SPEC_KEY.get(role)
    if key is None:
        return None
    spec = SCORING_EXAMPLE_SPECS[key]
    expect_pass = raw.get("decision") == "approve"
    return _check_scoring_verdict(raw, spec, expect_pass=expect_pass)


def check_approved_plan_unchanged(raw: dict[str, Any], input_plan: dict[str, Any]) -> list[str]:
    """plan_leader が approve のとき approvedPlan が入力 planDraft と一致するか（無改変）。"""
    if raw.get("decision") != "approve":
        return []
    approved = raw.get("approvedPlan")
    if not approved:
        return ["decision=approve なのに approvedPlan が無い"]
    diffs: list[str] = []
    for f in _VERDICT_PLAN_FIELDS:
        if approved.get(f) != input_plan.get(f):
            diffs.append(f"approvedPlan.{f} が planDraft と不一致（leaderが書き換えた疑い）")
    return diffs


# ── serendipity 棚書き文法（owner ③） ─────────────────────────
def scan_serendipity_owner(parsed: BaseModel) -> list[str]:
    flags: list[str] = []
    why = str(getattr(parsed, "why_now_for_you", "") or "")
    if _scan(why, _TASK_REF_KW):
        flags.append(f"serendipity③が読者の課題に言及（棚書き文法違反候補）: {_scan(why, _TASK_REF_KW)}")
    howto = _scan(why + str(getattr(parsed, "core_message", "") or ""), _HOWTO_KW)
    if howto:
        flags.append(f"serendipityでハウツー化を約束している候補: {howto}")
    return flags


# ── STEP3 persona セットの規律（員数・2軸分散・薄さ・fromFavorite・人物名） ─────
def _norm_name(s: str) -> str:
    return "".join((s or "").split())


def _persona_list_checks(
    personas: list[Any], favs: list[dict[str, Any]], *, label: str = "persona"
) -> tuple[list[str], list[str], dict[str, Any]]:
    """著者リスト共通の規律（2軸分散・薄さ・fromFavorite・人物名衝突）。員数は呼出側で見る。

    persona_generator（personas）と author_casting（candidates）の双方から再利用する。
    """
    violations: list[str] = []
    flags: list[str] = []
    metrics: dict[str, Any] = {}
    n = len(personas)

    # voiceStyle×format の2軸分散（同一組み合わせの重複は確定違反）
    combos = [
        ((getattr(p, "voice_style", "") or "").strip(), (getattr(p, "format", "") or "").strip())
        for p in personas
    ]
    metrics["axisUnique"] = f"{len(set(combos))}/{len(combos)}"
    if personas and len(set(combos)) < len(combos):
        dups = sorted({c for c in combos if combos.count(c) > 1})
        violations.append(f"voiceStyle×format が2軸分散していない（重複の組み合わせ: {dups}）")

    # persona 薄さ（下限長未満 or 作り込みシグナル皆無 → 採点役が確定するフラグ）
    thin = [
        (getattr(p, "persona_id", "") or getattr(p, "name", ""))
        for p in personas
        if len((getattr(p, "persona", "") or "").strip()) < _PERSONA_MIN_LEN
        or not any(k in (getattr(p, "persona", "") or "") for k in _PERSONA_RICH_KW)
    ]
    if thin:
        flags.append(f"{label} が薄い（原体験・口癖・思想が乏しい候補）: {thin}")

    # fromFavorite 整合（favoriteAuthors 空なのに true は確定違反 / 非空なら採用率を metrics 化）
    from_fav = [
        (getattr(p, "persona_id", "") or getattr(p, "name", ""))
        for p in personas
        if getattr(p, "from_favorite", False)
    ]
    if not favs and from_fav:
        violations.append(f"favoriteAuthors が空なのに fromFavorite=true: {from_fav}")
    if favs:
        metrics["fromFavoriteAdopted"] = f"{len(from_fav)}/{n}"

    # 人物名衝突（読者本人・デモ登場人物・few-shot例の架空著者）→ 知財/整合の要確認フラグ
    known = [_norm_name(k) for k in _KNOWN_NAMES]
    hits = [
        getattr(p, "name", "")
        for p in personas
        if (nm := _norm_name(getattr(p, "name", ""))) and any(nm == k or nm in k or k in nm for k in known)
    ]
    if hits:
        flags.append(f"既知人物名との衝突（実在/デモ/few-shot例・知財/整合の要確認）: {hits}")

    return violations, flags, metrics


def check_persona_set(
    parsed: BaseModel, *, favorite_authors: Optional[list[dict[str, Any]]] = None
) -> tuple[list[str], list[str], dict[str, Any]]:
    """persona_generator 出力の STEP3 固有規律（員数4＝1人/冊）。戻り: (確定違反, 候補フラグ, メトリクス)。"""
    personas = list(getattr(parsed, "personas", []) or [])
    violations, flags, metrics = _persona_list_checks(personas, favorite_authors or [])
    if len(personas) != _PERSONA_COUNT:  # 員数厳守（確定違反）
        violations.insert(0, f"員数が{_PERSONA_COUNT}人でない（{len(personas)}人）")
    return violations, flags, metrics


def check_author_casting(
    parsed: BaseModel, *, favorite_authors: Optional[list[dict[str, Any]]] = None
) -> tuple[list[str], list[str], dict[str, Any]]:
    """author_casting（AuthorCasting）の STEP3 固有規律。候補3・chosen整合・選抜証跡。

    1企画＝候補3人を生成し最適1人を chosen に選ぶ（GeneratedPersonaSet の集合キャストとは別形）。
    """
    candidates = list(getattr(parsed, "candidates", []) or [])
    violations, flags, metrics = _persona_list_checks(candidates, favorite_authors or [], label="候補著者")

    # 候補員数3厳守（確定違反）
    if len(candidates) != _AUTHOR_CANDIDATE_COUNT:
        violations.insert(0, f"候補員数が{_AUTHOR_CANDIDATE_COUNT}人でない（{len(candidates)}人）")

    # chosen は candidates の1人と personaId で一致（選抜整合・確定違反）
    chosen = getattr(parsed, "chosen", None)
    cand_ids = {(getattr(c, "persona_id", "") or "") for c in candidates}
    if chosen is None:
        violations.append("chosen が無い（選抜結果が欠落）")
    else:
        cid = getattr(chosen, "persona_id", "") or ""
        if cid not in cand_ids:
            violations.append(f"chosen.personaId が candidates に無い（選抜整合違反）: {cid!r}")

    # 選抜理由＝書店で見える"なぜこの著者か"の証跡（必須非空・確定違反）
    if not str(getattr(parsed, "selection_reason", "") or "").strip():
        violations.append("selectionReason が空（“なぜこの著者か”の証跡が無い）")

    return violations, flags, metrics


def check_serendipity_set(parsed: BaseModel) -> tuple[list[str], list[str], dict[str, Any]]:
    """serendipity_themes（SerendipitySet）固有規律。員数4・adjacency分散・棚書き文法。

    隣接/反対/飛躍/ニッチで4テーマを散らす。whyForReader は教養接続（薄く）で、読者の課題への
    直撃や即効ハウツーを約束しない（棚書き文法）。
    """
    violations: list[str] = []
    flags: list[str] = []
    metrics: dict[str, Any] = {}
    themes = list(getattr(parsed, "themes", []) or [])
    n = len(themes)

    if n != _SERENDIPITY_COUNT:  # 員数4厳守（確定違反）
        violations.append(f"員数が{_SERENDIPITY_COUNT}テーマでない（{n}）")

    # adjacency（隣接/反対/飛躍/ニッチ）の分散（重複は分散不足の候補フラグ）
    adj = [(getattr(t, "adjacency", "") or "").strip() for t in themes]
    metrics["adjacencyUnique"] = f"{len(set(a for a in adj if a))}/{len(adj)}"
    if themes and len(set(adj)) < len(adj):
        dups = sorted({a for a in adj if a and adj.count(a) > 1})
        flags.append(f"adjacency（隣接/反対/飛躍/ニッチ）が分散していない（重複: {dups}）")

    # 棚書き文法：whyForReader が読者の課題に直撃 / 即効ハウツーを約束（候補フラグ）
    blob = " ".join(str(getattr(t, "why_for_reader", "") or "") for t in themes)
    if task := _scan(blob, _TASK_REF_KW):
        flags.append(f"serendipityが読者の課題に直接言及（棚書き文法違反候補）: {task}")
    if howto := _scan(blob, _HOWTO_KW):
        flags.append(f"serendipityでハウツー化/即効を約束している候補: {howto}")

    return violations, flags, metrics


# ── STEP4 プレビュー採点 / modeB 本文採点 / STEP5 装丁 固有規律 ──────────
_BODY_THRESHOLD = 70    # modeb_editor 合格（本文5観点×0〜20＝100）
_PREVIEW_THRESHOLD = 50  # editor_preview 合格（プレビュー3観点×0〜25＝75）
_PREVIEW_FLOOR = 10      # editor_preview 各観点の足切り


def check_body_verdict(raw: dict[str, Any]) -> tuple[list[str], list[str], dict[str, Any]]:
    """modeb_editor（BodyVerdict）固有：5観点合計の自己整合・weakChapters整合・revise時feedback。

    本文ルーブリック5観点（coherence/hook/relevance/personaConsistency/actionability・各0〜20）。
    approve は総合>=70・weakChapters空。revise は弱章列挙＋editorFeedback必須。
    （modeB は合格例で approve→editorFeedback=null を許容するため approve時のfeedbackは要求しない）
    """
    violations: list[str] = []
    flags: list[str] = []
    metrics: dict[str, Any] = {}
    bd = raw.get("scoreBreakdown") or {}
    comps = ["coherence", "hook", "relevance", "personaConsistency", "actionability"]
    vals = [bd.get(c) for c in comps]
    score = raw.get("score")
    if all(isinstance(v, (int, float)) for v in vals):
        total = sum(int(v) for v in vals)
        metrics["breakdownSum"] = f"{total} (score={score})"
        if isinstance(score, (int, float)) and int(score) != total:
            violations.append(f"score({score})が本文5観点合計({total})と不一致")
        for c, v in zip(comps, vals):
            if not (0 <= int(v) <= 20):
                violations.append(f"{c}が0〜20の範囲外（{v}）")
    decision = raw.get("decision")
    weak = raw.get("weakChapters") or []
    fb = raw.get("editorFeedback")
    if decision == "approve":
        if isinstance(score, (int, float)) and int(score) < _BODY_THRESHOLD:
            violations.append(f"approve なのに総合{score} < {_BODY_THRESHOLD}")
        if weak:
            violations.append(f"approve なのに weakChapters 非空（{weak}）")
    elif decision == "revise":
        if not weak:
            flags.append("revise なのに weakChapters が空（弱章未指定の候補）")
        if not (fb and str(fb).strip()):
            violations.append("revise なのに editorFeedback が空（差し戻し理由欠如）")
    return violations, flags, metrics


def check_editor_verdict(raw: dict[str, Any]) -> tuple[list[str], list[str], dict[str, Any]]:
    """editor_preview（EditorVerdict）固有：3観点合計の自己整合・足切り整合・approveでもfeedback必須。

    プレビュー3観点（rawInsight/personaForward/catchiness・各0〜25）。approve は総合>=50 かつ
    全観点>=10。**approve でも editorFeedback を null にしない**（ラバースタンプ禁止・I-18 6/23校正）。
    """
    violations: list[str] = []
    flags: list[str] = []
    metrics: dict[str, Any] = {}
    bd = raw.get("scoreBreakdown") or {}
    comps = ["rawInsight", "personaForward", "catchiness"]
    vals = [bd.get(c) for c in comps]
    score = raw.get("score")
    numeric = all(isinstance(v, (int, float)) for v in vals)
    if numeric:
        total = sum(int(v) for v in vals)
        metrics["breakdownSum"] = f"{total} (score={score})"
        if isinstance(score, (int, float)) and int(score) != total:
            violations.append(f"score({score})がプレビュー3観点合計({total})と不一致")
        for c, v in zip(comps, vals):
            if not (0 <= int(v) <= 25):
                violations.append(f"{c}が0〜25の範囲外（{v}）")
        if all(int(v) == 25 for v in vals):
            flags.append("3観点すべて満点（満点アンカー張り付きの候補）")
    decision = raw.get("decision")
    fb = raw.get("editorFeedback")
    if decision == "approve":
        if isinstance(score, (int, float)) and int(score) < _PREVIEW_THRESHOLD:
            violations.append(f"approve なのに総合{score} < {_PREVIEW_THRESHOLD}")
        if numeric and any(int(v) < _PREVIEW_FLOOR for v in vals):
            violations.append(f"approve なのに足切り観点あり（<{_PREVIEW_FLOOR}）")
        if not (fb and str(fb).strip()):
            violations.append("approve でも editorFeedback を残す規律に違反（ラバースタンプ・6/23校正）")
    elif decision == "revise":
        if not (fb and str(fb).strip()):
            violations.append("revise なのに editorFeedback が空（差し戻し理由欠如）")
    return violations, flags, metrics


_COVER_NOTEXT = ("no text", "no lettering")
_COVER_NOFACE = ("no real face", "no human face", "no real human face")
_COVER_TEXTBURN = ("with the title", "title text", "letters spelling", "text reading", "title written")


def check_cover_prompt(raw: dict[str, Any]) -> tuple[list[str], list[str], dict[str, Any]]:
    """cover（coverPrompt）固有：装丁メタ規律（文字を焼かない・実在人物の顔を避ける）。"""
    violations: list[str] = []
    flags: list[str] = []
    metrics: dict[str, Any] = {}
    cp = str(raw.get("coverPrompt", "") or "")
    if not cp.strip():
        violations.append("coverPrompt が空")
        return violations, flags, metrics
    low = cp.lower()
    if not any(k in low for k in _COVER_NOTEXT):
        violations.append("coverPrompt に no-text 指示（no text / no lettering）が無い（文字焼き込みの恐れ）")
    if not any(k in low for k in _COVER_NOFACE):
        violations.append("coverPrompt に no-faces 指示（no real faces 等）が無い（実在人物の顔の恐れ）")
    for kw in _COVER_TEXTBURN:
        if kw in low:
            flags.append(f"タイトル文字焼き込みの候補表現: '{kw}'")
    return violations, flags, metrics


@dataclass
class DisciplineReport:
    role: str
    schema_ok: bool
    unknown_fields: list[str] = field(default_factory=list)
    violations: list[str] = field(default_factory=list)  # 確定違反（決定的）
    flags: list[str] = field(default_factory=list)        # LLM採点役が確定する候補
    metrics: dict[str, Any] = field(default_factory=dict)
    errors: list[str] = field(default_factory=list)       # schema validate エラー

    @property
    def has_violations(self) -> bool:
        return bool(self.violations) or not self.schema_ok or bool(self.unknown_fields)


def run_discipline_checks(role: str, raw: dict[str, Any], *, context: Optional[dict[str, Any]] = None) -> DisciplineReport:
    """1件の被験者出力に決定的スモークをかける。context: input_plan/good_example/market_gap/theme_kind。"""
    context = context or {}
    rep = DisciplineReport(role=role, schema_ok=True)

    schema_ok, parsed, unknown, errors = validate_output(role, raw)
    rep.schema_ok, rep.unknown_fields, rep.errors = schema_ok, unknown, errors
    for u in unknown:
        rep.violations.append(f"スキーマ未定義フィールド（フィールド名創作の疑い）: {u}")

    if parsed is not None:
        rep.violations += check_required_nonempty(role, parsed)
        rep.violations += check_evidence_binding(role, parsed)

    # role越境（調査サブ）
    over = scan_role_overreach(role, raw)
    if over:
        rep.flags.append(f"role越境シグナル（調査の役割を超えた企画案的記述の候補）: {over}")

    # 採点系
    sc = check_scoring_consistency(role, raw)
    if sc is not None:
        ok, note = sc
        rep.metrics["scoringConsistency"] = note
        if not ok:
            rep.violations.append(f"採点の自己整合に違反: {note}")
    if role == "plan_leader" and context.get("input_plan"):
        rep.violations += check_approved_plan_unchanged(raw, context["input_plan"])

    # owner 固有
    if role == "plan_owner" and parsed is not None:
        situ_why = str(getattr(parsed, "reader_situation", "") or "") + str(getattr(parsed, "why_now_for_you", "") or "")
        emo = scan_emotion_injection(situ_why)
        if emo:
            rep.flags.append(f"感情語の使用（観測に本人の言葉がなければ創作＝要確認）: {emo}")
        good = context.get("good_example")
        if good is None:
            try:
                good = load_prompt(spec_for(role).prompt_file).good_example
            except Exception:
                good = None
        if good:
            blob = json.dumps(raw, ensure_ascii=False)
            rep.metrics["fewshotContamination"] = fewshot_contamination_score(blob, good)
        if context.get("market_gap"):
            rep.metrics["marketGapCitation"] = check_marketgap_citation(
                str(getattr(parsed, "diff_from_market", "") or ""), context["market_gap"]
            )
        if context.get("theme_kind") == "serendipity":
            rep.flags += scan_serendipity_owner(parsed)

    # sub_reader_context / reader_analyst 感情スキャン
    if role in ("sub_reader_context", "reader_analyst"):
        emo = scan_emotion_injection(json.dumps(raw, ensure_ascii=False))
        if emo:
            rep.flags.append(f"感情語の使用（観測に本人の言葉がなければ創作＝要確認）: {emo}")

    # persona_generator（STEP3）固有：員数4・2軸分散・薄さ・fromFavorite・人物名
    if role == "persona_generator" and parsed is not None:
        v, f, m = check_persona_set(parsed, favorite_authors=context.get("favorite_authors"))
        rep.violations += v
        rep.flags += f
        rep.metrics.update(m)

    # author_casting（STEP3・4テーマ）固有：候補3・chosen整合・選抜証跡・候補の2軸分散/薄さ
    if role == "author_casting" and parsed is not None:
        v, f, m = check_author_casting(parsed, favorite_authors=context.get("favorite_authors"))
        rep.violations += v
        rep.flags += f
        rep.metrics.update(m)

    # serendipity_themes（別ロジック）固有：員数4・adjacency分散・棚書き文法
    if role == "serendipity_themes" and parsed is not None:
        v, f, m = check_serendipity_set(parsed)
        rep.violations += v
        rep.flags += f
        rep.metrics.update(m)

    # modeb_editor（BodyVerdict）固有：5観点合計の自己整合・weakChapters整合・revise時feedback
    if role == "modeb_editor":
        v, f, m = check_body_verdict(raw)
        rep.violations += v
        rep.flags += f
        rep.metrics.update(m)

    # editor_preview（EditorVerdict）固有：3観点合計の自己整合・足切り整合・approveでもfeedback必須
    if role == "editor_preview":
        v, f, m = check_editor_verdict(raw)
        rep.violations += v
        rep.flags += f
        rep.metrics.update(m)

    # cover（coverPrompt）固有：装丁メタ規律（文字焼かない・実在人物の顔回避）
    if role == "cover":
        v, f, m = check_cover_prompt(raw)
        rep.violations += v
        rep.flags += f
        rep.metrics.update(m)

    return rep


def format_report(rep: DisciplineReport) -> str:
    lines = [f"== 規律スモーク: role={rep.role} =="]
    lines.append(f"schema: {'OK' if rep.schema_ok else 'FAIL'}")
    if rep.errors:
        lines.append("  validate errors:")
        lines += [f"    - {e}" for e in rep.errors]
    if rep.violations:
        lines.append(f"確定違反 ({len(rep.violations)}):")
        lines += [f"  ✗ {v}" for v in rep.violations]
    else:
        lines.append("確定違反: なし")
    if rep.flags:
        lines.append(f"要LLM確認フラグ ({len(rep.flags)}):")
        lines += [f"  ⚐ {f}" for f in rep.flags]
    if rep.metrics:
        lines.append("メトリクス:")
        lines += [f"  · {k} = {v}" for k, v in rep.metrics.items()]
    lines.append("")
    lines.append(GEMINI_GATE_NOTE)
    return "\n".join(lines)


def main(argv: Optional[list[str]] = None) -> int:
    p = argparse.ArgumentParser(description="STEP1–5 プロンプト規律スモーク（決定的・$0）")
    p.add_argument("--role", required=True, help="registry のrole（plan_owner / plan_leader / sub_market 等）")
    p.add_argument("--input", required=True, help="被験者出力JSONのパス")
    p.add_argument("--context", help="任意: input_plan/good_example/market_gap/theme_kind を持つJSON")
    p.add_argument("--json", action="store_true", help="機械可読JSONで出力")
    args = p.parse_args(argv)

    raw = json.loads(Path(args.input).read_text(encoding="utf-8"))
    context = json.loads(Path(args.context).read_text(encoding="utf-8")) if args.context else None
    rep = run_discipline_checks(args.role, raw, context=context)

    if args.json:
        print(json.dumps({
            "role": rep.role, "schemaOk": rep.schema_ok, "unknownFields": rep.unknown_fields,
            "violations": rep.violations, "flags": rep.flags, "metrics": rep.metrics,
            "errors": rep.errors, "hasViolations": rep.has_violations,
        }, ensure_ascii=False, indent=2))
    else:
        print(format_report(rep))
    return 1 if rep.has_violations else 0


if __name__ == "__main__":
    raise SystemExit(main())
