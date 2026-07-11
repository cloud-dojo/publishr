"""prompt_review_dump の review_payload.json を、人間が価値観採点しやすい単一HTMLに整形する。

レビュー運用4層モデルの **層2（人間・価値観）** の道具。
複数セル（被験者×テーマ）の payload を1枚のギャラリーに集約し、各STEPの出力＋自動フラグ
（smoke_discipline を再利用）＋価値観採点欄（◎○△✗＋コメント・localStorage退避）を並べる。
改修後は前回 verdicts.yaml を baseline に渡すと、出力ハッシュが変わったカードだけ「要再レビュー」
に色付く（差分レビュー）。

  uv run python -m scripts.review_gallery artifacts/prompt-review/<run>/review_payload.json
  uv run python -m scripts.review_gallery A/review_payload.json B/review_payload.json --out artifacts/prompt-review/gallery.html
  uv run python -m scripts.review_gallery <new>/review_payload.json --baseline <prev>/verdicts.yaml

純整形・$0。実LLMは一切呼ばない（discipline は決定的・オフライン）。価値観採点は人間が下す。
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
from pathlib import Path
from typing import Any, Optional

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.smoke_discipline import run_discipline_checks  # noqa: E402

# 価値観スコアカードの採点キー → STEP別の割当。
# 同じ出力を二度見しないため、各STEPで見るディメンションだけ採点欄を出す。
DIMS = {
    "relevance": "①局面的中",
    "differentiation": "②差別化",
    "researchUse": "③調査活用",
    "titleHook": "④タイトル",
    "personaFront": "⑤著者前面化",
    "abstraction": "⑥型⇄重さ",
    "deliveryReason": "⑦入荷理由",
    "authorWarmth": "⑧体温",
    "diversity": "⑨棚多様性",
    "serendipity": "⑩セレンディピティ",
}
PLAN_DIMS = ["relevance", "differentiation", "researchUse", "titleHook"]
CASTING_DIMS = ["personaFront", "authorWarmth"]
PREVIEW_DIMS = ["abstraction", "deliveryReason"]
SHELF_DIMS = ["diversity", "serendipity"]

# ⑦ deliveryReason 観測ソース metric（参考値・緑/赤判定はしない）。
_DR_SOURCE_KW = [
    "Drive", "ドライブ", "カレンダー", "Calendar", "予定", "タスク", "Tasks",
    "議事", "メモ", "資料", "1on1", "面談", "定例", "報告", "稟議", "監査",
]
_DR_DATE_PATS = [re.compile(r"\d{1,2}\s*[/／]\s*\d{1,2}"), re.compile(r"\d{1,2}月\d{1,2}日")]


def _hash(obj: Any) -> str:
    blob = json.dumps(obj, ensure_ascii=False, sort_keys=True)
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()[:12]


def delivery_reason_metric(text: str) -> dict[str, int]:
    """deliveryReason が観測ソースを名指ししているかの参考値（⑦の半自動化）。0なら定型文の疑い。"""
    text = text or ""
    ids = len(re.findall(r"(?:drv_|cal_|tsk_)\d+", text))
    kw = sum(text.count(k) for k in _DR_SOURCE_KW)
    dates = sum(len(p.findall(text)) for p in _DR_DATE_PATS)
    return {"idHits": ids, "sourceKwHits": kw, "dateHits": dates, "chars": len(text)}


def _safe_discipline(role: str, raw: Any, context: Optional[dict[str, Any]] = None) -> dict[str, Any]:
    """run_discipline_checks を安全に呼ぶ（誤検出・例外でギャラリーを壊さない）。"""
    if not isinstance(raw, dict):
        return {}
    try:
        rep = run_discipline_checks(role, raw, context=context or {})
    except Exception as exc:  # noqa: BLE001 — 整形ツールは落とさず注記する
        return {"error": f"{type(exc).__name__}: {exc}"}
    return {
        "role": role,
        "schemaOk": rep.schema_ok,
        "violations": rep.violations,
        "unknownFields": rep.unknown_fields,
        "flags": rep.flags,
        "metrics": {k: v for k, v in rep.metrics.items()},
    }


def _market_gap(planning: dict[str, Any]) -> str:
    """planning.research から marketGap らしき文字列を拾う（plan_owner の marketGapCitation 用・任意）。"""
    research = planning.get("research") or {}
    for key in ("subMarket", "sub_market", "market"):
        sub = research.get(key)
        if isinstance(sub, dict):
            for gk in ("marketGap", "market_gap"):
                if sub.get(gk):
                    return str(sub[gk])
    return ""


def build_cell(payload: dict[str, Any]) -> dict[str, Any]:
    manifest = payload.get("manifest") or {}
    user_id = manifest.get("userId", "?")
    theme_kind = manifest.get("themeKind", "honmei")
    code = f"{user_id}__{theme_kind}"
    planning = payload.get("planning") or {}
    market_gap = _market_gap(planning)

    reader = payload.get("readerProfile") or {}
    cw = reader.get("currentWork") or {}
    rb = reader.get("readingBehavior") or {}
    base = reader.get("base") or {}
    reader_view = {
        "position": base.get("position", ""),
        "currentSituation": cw.get("currentSituation", ""),
        "activeWorkThemes": cw.get("activeWorkThemes") or [],
        "challenges": cw.get("challenges") or [],
        "serendipityTolerance": rb.get("serendipityTolerance", ""),
        "discipline": _safe_discipline("reader_analyst", reader),
    }

    tas = planning.get("themeAssignmentSet") or {}
    ei = tas.get("editorialIntent") or {}
    assignments = []
    for a in tas.get("assignments") or []:
        t = (a or {}).get("theme") or {}
        assignments.append({"teamId": a.get("teamId", ""), "name": t.get("name", ""), "role": t.get("role", "")})
    shelf = {
        "editorialIntent": {
            "shelfConcept": ei.get("shelfConcept", ""),
            "readerExperience": ei.get("readerExperience", ""),
            "balanceConstraints": ei.get("balanceConstraints") or [],
        },
        "assignments": assignments,
        "rounds": planning.get("rounds"),
        "verdictHistory": planning.get("verdictHistory") or [],
        "rejectLog": planning.get("rejectLog") or [],
        "hash": _hash(tas),
        "discipline": _safe_discipline(
            "editor_chief_themes", tas, {"theme_kind": theme_kind}
        ),
    }

    plans_by_id = {p.get("proposalId"): p for p in (planning.get("planSet") or {}).get("plans") or []}

    books = []
    for b in payload.get("books") or []:
        plan = b.get("plan") or {}
        pid = plan.get("proposalId") or plan.get("proposal_id") or ""
        plan = plans_by_id.get(pid, plan)
        casting = b.get("casting") or {}
        drafts = b.get("drafts") or []
        draft0 = drafts[0] if drafts else {}
        bd = draft0.get("bookDraft") or {}
        verdict = draft0.get("verdict") or {}
        shelved = (b.get("shelved") or [{}])[0]

        plan_ctx = {"theme_kind": theme_kind, "market_gap": market_gap}
        casting_ctx = {"favorite_authors": None}

        books.append({
            "id": pid,
            "plan": {
                "tentativeTitle": plan.get("tentativeTitle", ""),
                "theme": plan.get("theme", ""),
                "themeRole": plan.get("themeRole", ""),
                "bookRole": plan.get("bookRole", ""),
                "utility": plan.get("utility", ""),
                "emotionalTone": plan.get("emotionalTone", ""),
                "readerSituation": plan.get("readerSituation", ""),
                "whyNowForYou": plan.get("whyNowForYou", ""),
                "coreMessage": plan.get("coreMessage", ""),
                "diffFromMarket": plan.get("diffFromMarket", ""),
                "keyInsights": plan.get("keyInsights") or [],
                "agendaOutline": plan.get("agendaOutline") or [],
                "recommendedAuthorTypes": plan.get("recommendedAuthorTypes") or [],
                "hash": _hash(plan),
                "discipline": _safe_discipline("plan_owner", plan, plan_ctx),
            },
            "casting": {
                "candidates": [
                    {
                        "name": c.get("name", ""),
                        "voiceStyle": c.get("voiceStyle", ""),
                        "format": c.get("format", ""),
                        "persona": c.get("persona", ""),
                        "fromFavorite": c.get("fromFavorite", False),
                    }
                    for c in casting.get("candidates") or []
                ],
                "chosenName": (casting.get("chosen") or {}).get("name", ""),
                "selectionReason": casting.get("selectionReason", ""),
                "hash": _hash(casting),
                "discipline": _safe_discipline("author_casting", casting, casting_ctx),
            },
            "preview": {
                "title": bd.get("title", ""),
                "deliveryReason": bd.get("deliveryReason", ""),
                "problemToSolve": bd.get("problemToSolve", ""),
                "prefaceSample": bd.get("prefaceSample", ""),
                "agenda": bd.get("agenda") or [],
                "verdict": {
                    "score": verdict.get("score"),
                    "scoreBreakdown": verdict.get("scoreBreakdown") or {},
                    "decision": verdict.get("decision"),
                    "editorFeedback": verdict.get("editorFeedback"),
                },
                "deliveryReasonMetric": delivery_reason_metric(bd.get("deliveryReason", "")),
                "hash": _hash(bd),
                "discipline": _safe_discipline("author_preview", bd),
                "verdictDiscipline": _safe_discipline("editor_preview", verdict),
            },
            "cover": {
                "coverVariant": shelved.get("coverVariant", ""),
                "coverPrompt": shelved.get("coverPrompt", ""),
                "hash": _hash({"v": shelved.get("coverVariant"), "p": shelved.get("coverPrompt")}),
                "discipline": _safe_discipline("cover", shelved),
            },
        })

    return {
        "id": f"{user_id} / {theme_kind}",
        "code": code,
        "manifest": manifest,
        "reader": reader_view,
        "shelf": shelf,
        "books": books,
    }


def _load_baseline(path: Optional[str]) -> dict[str, Any]:
    if not path:
        return {}
    try:
        import yaml  # pyyaml は eval_harness 等で既に依存
        return yaml.safe_load(Path(path).read_text(encoding="utf-8")) or {}
    except Exception as exc:  # noqa: BLE001
        print(f"warn: baseline 読み込み失敗（差分なしで続行）: {exc}", file=sys.stderr)
        return {}


HTML_SHELL = r"""<!doctype html>
<html lang="ja">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>__TITLE__</title>
<style>
:root{ --bg:#0f1115; --panel:#171a21; --panel2:#1d212b; --bd:#2a2f3a; --fg:#e6e8ee; --mut:#9aa3b2;
  --good:#3fb950; --warn:#d29922; --bad:#f85149; --acc:#58a6ff; --gray:#6e7681; }
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--fg);font:14px/1.6 -apple-system,"Segoe UI",Roboto,"Hiragino Kaku Gothic ProN",Meiryo,sans-serif}
header{position:sticky;top:0;z-index:5;background:var(--panel);border-bottom:1px solid var(--bd);padding:10px 16px;display:flex;gap:12px;align-items:center;flex-wrap:wrap}
header h1{font-size:15px;margin:0;font-weight:600}
.tabs{display:flex;gap:6px;flex-wrap:wrap}
.tab{padding:5px 12px;border:1px solid var(--bd);border-radius:999px;background:var(--panel2);color:var(--mut);cursor:pointer;font-size:13px}
.tab.active{color:var(--fg);border-color:var(--acc);background:#1b2740}
.toolbar{margin-left:auto;display:flex;gap:8px;align-items:center;flex-wrap:wrap}
.toolbar label{color:var(--mut);font-size:12px;display:flex;gap:4px;align-items:center;cursor:pointer}
button.act{padding:5px 10px;border:1px solid var(--bd);border-radius:6px;background:var(--panel2);color:var(--fg);cursor:pointer;font-size:12px}
button.act:hover{border-color:var(--acc)}
main{padding:16px;max-width:1180px;margin:0 auto}
.step{margin:18px 0 6px;font-size:12px;letter-spacing:.06em;color:var(--mut);text-transform:uppercase;border-bottom:1px solid var(--bd);padding-bottom:4px}
.panel{background:var(--panel);border:1px solid var(--bd);border-radius:10px;padding:12px 14px;margin:8px 0}
.cards{display:grid;grid-template-columns:repeat(auto-fill,minmax(330px,1fr));gap:12px}
.card{background:var(--panel);border:1px solid var(--bd);border-radius:10px;padding:12px;display:flex;flex-direction:column;gap:6px}
.card.changed{border-color:var(--bad);box-shadow:0 0 0 1px var(--bad) inset}
.card.unchanged{opacity:.62}
.card h3{margin:0;font-size:14px}
.kv{font-size:12.5px;color:var(--fg)} .kv b{color:var(--mut);font-weight:600;margin-right:4px}
.muted{color:var(--mut)} .small{font-size:12px}
.tagrow{display:flex;gap:6px;flex-wrap:wrap;margin:2px 0}
.tag{font-size:11px;padding:1px 7px;border-radius:999px;border:1px solid var(--bd);color:var(--mut)}
.badge{font-size:11px;padding:1px 7px;border-radius:6px;display:inline-block;margin:1px 0}
.b-v{background:#3a1416;color:#ffb4ac;border:1px solid #6e2b2b}
.b-f{background:#3a2c0a;color:#f0cd8a;border:1px solid #6e561d}
.b-m{background:#16263a;color:#9ec7ff;border:1px solid #284a6e}
.b-ok{background:#0f2a18;color:#7ee2a0;border:1px solid #245a36}
.flags{display:flex;flex-direction:column;gap:3px;margin-top:4px}
.score{display:flex;gap:10px;flex-wrap:wrap;margin-top:8px;padding-top:8px;border-top:1px dashed var(--bd)}
.dim{display:flex;flex-direction:column;gap:3px}
.dim .lab{font-size:11px;color:var(--mut)}
.grades{display:flex;gap:3px}
.g{width:24px;height:24px;border-radius:6px;border:1px solid var(--bd);background:var(--panel2);color:var(--mut);cursor:pointer;font-size:13px;line-height:22px;text-align:center;padding:0}
.g.sel{color:#fff;border-color:var(--acc)}
.g[data-v="3"].sel{background:#1f6f3a;border-color:var(--good)}
.g[data-v="2"].sel{background:#2d5fa6;border-color:var(--acc)}
.g[data-v="1"].sel{background:#7a5a12;border-color:var(--warn)}
.g[data-v="0"].sel{background:#7a2620;border-color:var(--bad)}
textarea.cmt{width:100%;margin-top:6px;background:var(--panel2);color:var(--fg);border:1px solid var(--bd);border-radius:6px;padding:6px;font:12px/1.5 inherit;resize:vertical;min-height:34px}
.reread{font-size:11px;color:var(--bad);font-weight:600}
.prev{font-size:11px;color:var(--gray)}
details{margin-top:4px} summary{cursor:pointer;color:var(--mut);font-size:12px}
pre{white-space:pre-wrap;word-break:break-word;background:var(--panel2);border:1px solid var(--bd);border-radius:6px;padding:8px;font-size:11.5px;margin:4px 0}
.hint{color:var(--mut);font-size:12px;margin:6px 0 0}
.cellwrap{display:none} .cellwrap.active{display:block}
</style>
</head>
<body>
<header>
  <h1>__TITLE__</h1>
  <div class="tabs" id="tabs"></div>
  <div class="toolbar">
    <label><input type="checkbox" id="flagsOnly"> ⚐フラグだけ</label>
    <label><input type="checkbox" id="changedOnly"> 変わったカードだけ</label>
    <button class="act" id="exportBtn">verdicts.yaml を出力</button>
  </div>
</header>
<main id="root"></main>
<script>
const DATA = __DATA__;
const BASELINE = __BASELINE__;
const GID = "rv:" + DATA.cells.map(c=>c.code).sort().join("|");
const DIMS = __DIMS__;
const PLAN_DIMS=__PLAN_DIMS__, CASTING_DIMS=__CASTING_DIMS__, PREVIEW_DIMS=__PREVIEW_DIMS__, SHELF_DIMS=__SHELF_DIMS__;
const GRADES=[["3","◎"],["2","○"],["1","△"],["0","✗"]];

function esc(s){return (s==null?"":String(s)).replace(/[&<>]/g,m=>({"&":"&amp;","<":"&lt;",">":"&gt;"}[m]));}
function lsKey(cell,scope,dim){return GID+":"+cell+":"+scope+":"+dim;}
function getScore(cell,scope,dim){return localStorage.getItem(lsKey(cell,scope,dim));}
function setScore(cell,scope,dim,v){localStorage.setItem(lsKey(cell,scope,dim),v);}
function getCmt(cell,scope){return localStorage.getItem(lsKey(cell,scope,"_cmt"))||"";}
function setCmt(cell,scope,v){localStorage.setItem(lsKey(cell,scope,"_cmt"),v);}

function baselineHash(cellCode, kind, id){
  try{
    const c=(BASELINE.cells||{})[cellCode]; if(!c) return null;
    if(kind==="shelf"){ return (c.shelf||{}).outputHash||null; }
    const grp=c[kind]||{}; const e=grp[id]; return e? (e.outputHash||null) : null;
  }catch(e){ return null; }
}
function changeState(cellCode, kind, id, curHash){
  const bh=baselineHash(cellCode,kind,id);
  if(BASELINE.cells===undefined) return "none";
  if(bh===null) return "changed";
  return bh===curHash? "unchanged":"changed";
}

function discBadges(d){
  if(!d) return "";
  if(d.error) return `<span class="badge b-f">discipline error: ${esc(d.error)}</span>`;
  let out=[];
  if(d.schemaOk===false) out.push(`<span class="badge b-v">schema NG</span>`);
  (d.violations||[]).forEach(v=>out.push(`<span class="badge b-v" title="${esc(v)}">✗ ${esc(v.slice(0,46))}</span>`));
  (d.flags||[]).forEach(f=>out.push(`<span class="badge b-f" title="${esc(f)}">⚐ ${esc(f.slice(0,46))}</span>`));
  const m=d.metrics||{}; Object.keys(m).forEach(k=>out.push(`<span class="badge b-m">${esc(k)}=${esc(m[k])}</span>`));
  if(!out.length) out.push(`<span class="badge b-ok">規律OK</span>`);
  return `<div class="flags">`+out.join("")+`</div>`;
}
function hasFlag(d){ return d && (d.error||d.schemaOk===false||(d.violations||[]).length||(d.flags||[]).length); }

function scoreRow(cell,scope,dims){
  let h=`<div class="score">`;
  dims.forEach(dim=>{
    const cur=getScore(cell,scope,dim);
    h+=`<div class="dim"><span class="lab">${esc(DIMS[dim])}</span><div class="grades">`;
    GRADES.forEach(([v,sym])=>{
      h+=`<button class="g${cur===v?' sel':''}" data-v="${v}" data-cell="${cell}" data-scope="${scope}" data-dim="${dim}">${sym}</button>`;
    });
    h+=`</div></div>`;
  });
  h+=`</div><textarea class="cmt" placeholder="コメント（keep/fix/risk/example）" data-cell="${cell}" data-scope="${scope}">${esc(getCmt(cell,scope))}</textarea>`;
  return h;
}

function rrTag(state){ return state==="changed"?`<span class="reread">● 要再レビュー</span>`:(state==="unchanged"?`<span class="prev">前回から不変</span>`:""); }

function bookCard(cell, kind, id, title, inner, disc, dims, curHash){
  const state=changeState(cell, kind, id, curHash);
  const cls = state==="changed"?" changed":(state==="unchanged"?" unchanged":"");
  const scope = kind+":"+id;
  return `<div class="card${cls}" data-flag="${hasFlag(disc)?1:0}" data-state="${state}">
    <h3>${esc(title)} ${rrTag(state)}</h3>
    ${inner}
    ${discBadges(disc)}
    ${scoreRow(cell, scope, dims)}
  </div>`;
}

function renderCell(c){
  let h=`<div class="cellwrap" id="cell-${c.code}">`;
  // メタ
  const L=c.manifest.llm||{};
  h+=`<div class="panel small muted">被験者 <b style="color:var(--fg)">${esc(c.manifest.userId)}</b> ・ themeKind <b style="color:var(--fg)">${esc(c.manifest.themeKind)}</b>
    ・ LLM reader=${esc(L.reader)} planning=${esc(L.planning)} preview=${esc(L.preview)} cover=${esc(L.cover)}
    ・ threshold=${esc(c.manifest.threshold)} ・ imagen=${esc(L.imagen)}
    ${L.planning==='mock'?'<span class="badge b-f" style="margin-left:8px">⚠ mock＝canned固定。価値観採点は --llm vertex で</span>':''}</div>`;

  // STEP1 reader（採点なし・前提の目視）
  h+=`<div class="step">STEP1 読者分析（採点なし・観測取りこぼしの目視）</div>`;
  const r=c.reader;
  h+=`<div class="panel"><div class="kv"><b>position</b>${esc(r.position)}</div>
    <div class="kv"><b>currentSituation</b>${esc(r.currentSituation)}</div>
    <div class="kv"><b>activeWorkThemes</b>${esc((r.activeWorkThemes||[]).join(" / "))}</div>
    <div class="kv"><b>challenges</b>${esc((r.challenges||[]).join(" / ")||"（空）")}</div>
    <div class="kv"><b>serendipityTolerance</b>${esc(r.serendipityTolerance)}</div>
    ${discBadges(r.discipline)}</div>`;

  // STEP2-0 棚（editorialIntent + 多様性 + leaderラウンド）→ ⑨⑩
  h+=`<div class="step">STEP2-0 編集長＝棚の設計（⑨棚多様性 / ⑩セレンディピティ）</div>`;
  const s=c.shelf; const shelfState=changeState(c.code,"shelf","_",s.hash);
  let shelfInner=`<div class="kv"><b>shelfConcept</b>${esc(s.editorialIntent.shelfConcept)}</div>
    <div class="kv"><b>readerExperience</b>${esc(s.editorialIntent.readerExperience)}</div>
    <div class="tagrow">`+ (s.assignments||[]).map(a=>`<span class="tag">${esc(a.teamId)}:${esc(a.role)}｜${esc((a.name||'').slice(0,22))}</span>`).join("")+`</div>`;
  if((s.rejectLog||[]).length){ shelfInner+=`<details><summary>rejectLog（差し戻し証跡 ${s.rejectLog.length}）</summary>`+
    s.rejectLog.map(e=>`<pre>round ${esc(e.round)} belowFloor=${esc((e.belowFloor||[]).join(','))}\n${esc(e.rejectionFeedback)}</pre>`).join("")+`</details>`; }
  if((s.verdictHistory||[]).length){ shelfInner+=`<div class="small muted">verdict: `+s.verdictHistory.map(v=>`R${esc(v.round)} ${esc(v.decision)}(${esc(v.score)})`).join(" → ")+`</div>`; }
  h+=`<div class="card${shelfState==='changed'?' changed':(shelfState==='unchanged'?' unchanged':'')}" data-flag="${hasFlag(s.discipline)?1:0}" data-state="${shelfState}">
    <h3>棚全体 ${rrTag(shelfState)}</h3>${shelfInner}${discBadges(s.discipline)}${scoreRow(c.code,"shelf:_",SHELF_DIMS)}</div>`;

  // STEP2 企画（plan_owner ×4 + leader）→ ①②③④
  h+=`<div class="step">STEP2 企画（①局面的中 / ②差別化 / ③調査活用 / ④タイトル）</div><div class="cards">`;
  c.books.forEach(b=>{
    const p=b.plan;
    const inner=`<div class="tagrow"><span class="tag">${esc(p.themeRole)}</span><span class="tag">${esc(p.bookRole)}</span><span class="tag">${esc(p.utility)}</span><span class="tag">${esc(p.emotionalTone)}</span></div>
      <div class="kv"><b>whyNow</b>${esc(p.whyNowForYou)}</div>
      <div class="kv"><b>coreMessage</b>${esc(p.coreMessage)}</div>
      <div class="kv"><b>diffFromMarket</b>${esc(p.diffFromMarket)}</div>
      <div class="small muted">keyInsights: ${esc((p.keyInsights||[]).join(' / '))}</div>
      <div class="small muted">agenda: ${esc((p.agendaOutline||[]).join(' → '))}</div>`;
    h+=bookCard(c.code,"plans",b.id, p.tentativeTitle||b.id, inner, p.discipline, PLAN_DIMS, p.hash);
  });
  h+=`</div>`;

  // STEP3 キャスティング → ⑤⑧
  h+=`<div class="step">STEP3 著者キャスティング（⑤著者前面化 / ⑧体温）</div><div class="cards">`;
  c.books.forEach(b=>{
    const ca=b.casting;
    const cand=(ca.candidates||[]).map(x=>`<div class="small ${x.name===ca.chosenName?'':'muted'}">${x.name===ca.chosenName?'★ ':''}${esc(x.name)}（${esc(x.voiceStyle)}×${esc(x.format)}）${x.fromFavorite?' [fav]':''}</div>`).join("");
    const chosenP=(ca.candidates||[]).find(x=>x.name===ca.chosenName)||{};
    const inner=`${cand}<div class="kv" style="margin-top:4px"><b>persona</b>${esc((chosenP.persona||'').slice(0,160))}</div>
      <div class="kv"><b>選抜理由</b>${esc(ca.selectionReason)}</div>`;
    h+=bookCard(c.code,"casting",b.id, "著者: "+(ca.chosenName||b.id), inner, ca.discipline, CASTING_DIMS, ca.hash);
  });
  h+=`</div>`;

  // STEP4 プレビュー → ⑥⑦（＋④はSTEP2で）
  h+=`<div class="step">STEP4 プレビュー（⑥型⇄重さ / ⑦入荷理由）</div><div class="cards">`;
  c.books.forEach(b=>{
    const pv=b.preview; const m=pv.deliveryReasonMetric||{};
    const v=pv.verdict||{}; const sb=v.scoreBreakdown||{};
    const drWarn=(m.idHits+ m.sourceKwHits + m.dateHits)===0;
    const inner=`<div class="kv"><b>deliveryReason</b>${esc(pv.deliveryReason)}</div>
      <div class="small ${drWarn?'reread':'muted'}">⑦ソース参照: id=${m.idHits} 語=${m.sourceKwHits} 日付=${m.dateHits}${drWarn?'（ソース不在＝定型文の疑い）':''}</div>
      <div class="kv"><b>problemToSolve</b>${esc(pv.problemToSolve)}</div>
      <details><summary>prefaceSample / agenda</summary><pre>${esc(pv.prefaceSample)}</pre><div class="small muted">${esc((pv.agenda||[]).map(a=>(a.chapter||'')+':'+(a.summary||'')).join(' / '))}</div></details>
      <div class="small muted">担当編集: score=${esc(v.score)} (${esc(sb.rawInsight)}/${esc(sb.personaForward)}/${esc(sb.catchiness)}) ${esc(v.decision)}</div>
      ${discBadges(pv.verdictDiscipline)}`;
    h+=bookCard(c.code,"preview",b.id, pv.title||b.id, inner, pv.discipline, PREVIEW_DIMS, pv.hash);
  });
  h+=`</div>`;

  h+=`<div class="hint">採点は自動保存（この端末のlocalStorage）。改修後は前回 verdicts.yaml を <code>--baseline</code> に渡すと、変わったカードだけ「要再レビュー」に色付きます。</div>`;
  h+=`</div>`;
  return h;
}

function buildYaml(){
  const lines=["meta:","  reviewer: tetsuda","  galleryId: "+JSON.stringify(GID),"cells:"];
  DATA.cells.forEach(c=>{
    lines.push("  "+c.code+":");
    const emit=(kind,scopeId,hash,dims)=>{
      const scope=kind+":"+scopeId;
      const sc={}; let any=false;
      dims.forEach(d=>{const v=getScore(c.code,scope,d); if(v!==null){sc[d]=Number(v);any=true;}});
      const cmt=getCmt(c.code,scope);
      if(!any && !cmt) return null;
      let s="      outputHash: "+hash+"\n";
      s+="      scores: {"+Object.keys(sc).map(k=>k+": "+sc[k]).join(", ")+"}\n";
      if(cmt) s+="      comment: "+JSON.stringify(cmt)+"\n";
      return s;
    };
    // shelf
    const sh=emit("shelf","_",c.shelf.hash,SHELF_DIMS);
    if(sh){ lines.push("    shelf:"); lines.push(sh.replace(/\n$/,"").split("\n").map(x=>"  "+x).join("\n")); }
    [["plans",b=>b.plan.hash,PLAN_DIMS],["casting",b=>b.casting.hash,CASTING_DIMS],["preview",b=>b.preview.hash,PREVIEW_DIMS]].forEach(([kind,hf,dims])=>{
      const blocks=[];
      c.books.forEach(b=>{ const e=emit(kind,b.id,hf(b),dims); if(e) blocks.push("      "+b.id+":\n"+e.split("\n").map(x=>x?"  "+x:x).join("\n").replace(/\n$/,"")); });
      if(blocks.length){ lines.push("    "+kind+":"); blocks.forEach(bl=>lines.push(bl)); }
    });
  });
  return lines.join("\n")+"\n";
}

function applyFilters(){
  const fo=document.getElementById("flagsOnly").checked;
  const co=document.getElementById("changedOnly").checked;
  document.querySelectorAll(".card").forEach(card=>{
    let show=true;
    if(fo && card.dataset.flag!=="1") show=false;
    if(co && card.dataset.state!=="changed") show=false;
    card.style.display = show? "":"none";
  });
}

function mount(){
  document.title=DATA.meta.title;
  const tabs=document.getElementById("tabs"), root=document.getElementById("root");
  DATA.cells.forEach((c,i)=>{
    const t=document.createElement("div"); t.className="tab"+(i===0?" active":""); t.textContent=c.id; t.dataset.code=c.code;
    t.onclick=()=>{document.querySelectorAll(".tab").forEach(x=>x.classList.remove("active"));t.classList.add("active");
      document.querySelectorAll(".cellwrap").forEach(x=>x.classList.remove("active"));
      document.getElementById("cell-"+c.code).classList.add("active"); applyFilters();};
    tabs.appendChild(t);
  });
  root.innerHTML=DATA.cells.map(renderCell).join("");
  const first=document.querySelector(".cellwrap"); if(first) first.classList.add("active");

  root.addEventListener("click",e=>{
    const g=e.target.closest(".g"); if(!g) return;
    const {cell,scope,dim,v}=g.dataset;
    const sibs=g.parentElement.querySelectorAll(".g");
    const was=getScore(cell,scope,dim);
    if(was===v){ localStorage.removeItem(lsKey(cell,scope,dim)); g.classList.remove("sel"); }
    else{ sibs.forEach(s=>s.classList.remove("sel")); g.classList.add("sel"); setScore(cell,scope,dim,v); }
  });
  root.addEventListener("input",e=>{
    const t=e.target.closest("textarea.cmt"); if(!t) return; setCmt(t.dataset.cell,t.dataset.scope,t.value);
  });
  document.getElementById("flagsOnly").onchange=applyFilters;
  document.getElementById("changedOnly").onchange=applyFilters;
  document.getElementById("exportBtn").onclick=()=>{
    const blob=new Blob([buildYaml()],{type:"text/yaml"});
    const a=document.createElement("a"); a.href=URL.createObjectURL(blob); a.download="verdicts.yaml"; a.click();
  };
  applyFilters();
}
mount();
</script>
</body>
</html>
"""


def render_html(cells: list[dict[str, Any]], baseline: dict[str, Any], title: str) -> str:
    data = {"meta": {"title": title}, "cells": cells}

    def js(obj: Any) -> str:
        return json.dumps(obj, ensure_ascii=False).replace("</", "<\\/")

    return (
        HTML_SHELL
        .replace("__TITLE__", title)
        .replace("__DATA__", js(data))
        .replace("__BASELINE__", js(baseline) if baseline else "{}")
        .replace("__DIMS__", js(DIMS))
        .replace("__PLAN_DIMS__", js(PLAN_DIMS))
        .replace("__CASTING_DIMS__", js(CASTING_DIMS))
        .replace("__PREVIEW_DIMS__", js(PREVIEW_DIMS))
        .replace("__SHELF_DIMS__", js(SHELF_DIMS))
    )


def main(argv: Optional[list[str]] = None) -> int:
    p = argparse.ArgumentParser(description="review_payload.json を価値観採点ギャラリー(HTML)に整形する")
    p.add_argument("payloads", nargs="+", help="review_payload.json のパス（複数＝複数セル）")
    p.add_argument("--out", default=None, help="出力HTML（既定: artifacts/prompt-review/gallery.html）")
    p.add_argument("--baseline", default=None, help="前回 verdicts.yaml（差分レビュー用）")
    p.add_argument("--title", default="Publishr 価値観レビュー ギャラリー")
    args = p.parse_args(argv)

    cells = []
    for path in args.payloads:
        payload = json.loads(Path(path).read_text(encoding="utf-8"))
        cells.append(build_cell(payload))

    baseline = _load_baseline(args.baseline)
    out = Path(args.out) if args.out else (ROOT / "artifacts" / "prompt-review" / "gallery.html")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(render_html(cells, baseline, args.title), encoding="utf-8")

    print(f"ギャラリー出力: {out}")
    print(f"セル: {', '.join(c['code'] for c in cells)}")
    flagged = sum(
        1
        for c in cells
        for b in c["books"]
        for k in ("plan", "casting", "preview", "cover")
        if (b[k].get("discipline") or {}).get("violations") or (b[k].get("discipline") or {}).get("flags")
    )
    print(f"自動フラグの付いた出力: {flagged}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
