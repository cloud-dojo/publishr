"""実LLM経路で STEP0→1→2→3→4 を一気通貫で回し、出力一式をファイルに吐く品質ループ用ハーネス。

「AI Studio のサイトに手で1個ずつ貼る」を置き換える。本番と同じコード
（prompt loader / output_schema / few-shot / google_search grounding）を通すので、
memory `feedback-verify-production-faithful` の言う本番忠実性は手貼りより高い。

バックエンドは --backend で選ぶ（既定 vertex）:
  - vertex   : GCP Vertex（ADC・project publishr-498123）。Imagen/eval も同経路で本番忠実度が高い。
  - aistudio : AI Studio APIキー（GOOGLE_API_KEY）。GCP不要だが前払い残高/無料枠に依存。

  # 既定（Vertex・推奨。ADC 済みなら準備不要）。企業TLSプロキシ下なので truststore を被せる:
  uv run --with truststore python -m scripts.run_aistudio_batch --user u_mita
  uv run --with truststore python -m scripts.run_aistudio_batch --user u_mita --threshold 85  # 差し戻し誘発
  uv run --with truststore python -m scripts.run_aistudio_batch --user u_mita --limit 1       # STEP4を1冊に

  # AI Studio キー経路を使う場合（GOOGLE_API_KEY を環境に置いてから）:
  uv run --with truststore python -m scripts.run_aistudio_batch --user u_mita --backend aistudio

切替の仕組み: google.genai/adk は GOOGLE_GENAI_USE_VERTEXAI で経路を決める（TRUE=Vertex / FALSE=AI Studio）。
本スクリプトは google/adk を import する前に env を確定させる。SSLKEYLOGFILE 除去は自動。

- STEP1 読者分析は既定 mock（fixture・課金ゼロ）。STEP2/3/4 を実Gemini で回す。
- 表紙 Imagen・フル本文(modeB) は対象外（Imagen は Vertex 固定 / フル本文は PR-6）。
  本文字数の検証は run_body_once を同じ backend で。
- grounding 忠実性（URL実在＋本文一致）は standing manual flag。引用URL一覧を吐くので人手で照合する。
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

# Windows コンソール(cp932)でも ⇄ ★ ◆ … を出せるよう UTF-8 に固定（出力は元から UTF-8 で書く）。
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(encoding="utf-8")
    except (AttributeError, ValueError):
        pass

JST = timezone(timedelta(hours=9))
DEMO_NOW = datetime(2026, 6, 3, 6, 0, tzinfo=JST)  # run_planning と揃える（水朝の本命 run）

_REPO_ROOT = Path(__file__).resolve().parents[1]
_DEFAULT_OUT = _REPO_ROOT.parent / "publishr_other" / "aistudio_runs"

_URL_RE = re.compile(r"https?://[^\s)>\]」】、,\"'`]+")

_KEY_HELP = """\
GOOGLE_API_KEY（または GEMINI_API_KEY）が未設定です。

  1. https://aistudio.google.com/apikey を開く（Googleアカウントでログイン）
  2. 「APIキーを作成」→ 生成された AIza... をコピー
  3. このシェルに置いて再実行:
       PowerShell : $env:GOOGLE_API_KEY = "AIza..."
       bash       : export GOOGLE_API_KEY=AIza...

無料枠で gemini-2.5-pro / flash を叩けます（レート制限あり）。課金や GCP/ADC は不要。
"""


def _harden_windows_tls() -> None:
    """企業TLS検査プロキシ下の Windows 機向け TLS 対策（memory: publishr-windows-vertex-ssl）。

    1) SSLKEYLOGFILE を外す（OpenSSL の `no OPENSSL_Applink` ネイティブクラッシュ回避）。
    2) truststore を注入し OS 証明書ストアに委譲（社内CAの厳格X.509拒否を回避）。
    AI Studio 経路も同じ google.genai HTTPS クライアントを使うので同対策が要る。
    """
    os.environ.pop("SSLKEYLOGFILE", None)
    try:
        import truststore  # noqa: PLC0415

        truststore.inject_into_ssl()
    except ImportError:
        sys.stderr.write(
            "[注意] truststore 未インストール。社内プロキシ下では証明書検証に失敗する可能性。\n"
            "        次で再実行: uv run --with truststore python -m scripts.run_aistudio_batch ...\n"
        )


def _flatten_exc(exc: BaseException, _depth: int = 0) -> str:
    """例外ツリー（ExceptionGroup の .exceptions ・ __cause__/__context__）を辿り全文を連結。

    asyncio TaskGroup は実 ClientError を ExceptionGroup に包むので、素の str() では
    API_KEY_INVALID 等が表層に出ない。再帰的に集めてからパターン照合する。
    """
    if exc is None or _depth > 6:
        return ""
    parts = [f"{type(exc).__name__}: {exc}"]
    for sub in getattr(exc, "exceptions", None) or []:
        parts.append(_flatten_exc(sub, _depth + 1))
    for chained in (exc.__cause__, exc.__context__):
        if chained is not None and chained is not exc:
            parts.append(_flatten_exc(chained, _depth + 1))
    return " | ".join(p for p in parts if p)


def _diagnose(exc: Exception) -> str:
    """実Gemini呼び出しの例外を一行診断に落とす（よくある詰まりを名指し）。"""
    msg = _flatten_exc(exc)
    if "API_KEY_INVALID" in msg or "API key not valid" in msg:
        return "APIキーが無効です。AIza... の値を確認（GOOGLE_API_KEY）。"
    if "RESOURCE_EXHAUSTED" in msg or "429" in msg or "quota" in msg.lower():
        return (
            "無料枠のレート/クォータ超過（429）。STEP2 は調査サブ並列＋owner⇄leaderループで "
            "Pro 呼び出しがバースト発火し、無料Pro上限に当たりやすい。"
            "→ `--cheap`（全工程 flash・無料枠が緩い）で再実行するか、キーに課金(pay-as-you-go)を有効化。"
        )
    if "SERVICE_DISABLED" in msg or "has not been used in project" in msg or "aiplatform.googleapis.com" in msg and "enable" in msg.lower():
        return "Vertex AI API が未有効。`gcloud services enable aiplatform.googleapis.com --project=publishr-498123`。"
    if "BILLING_DISABLED" in msg or "billing" in msg.lower():
        return "GCPプロジェクトの課金が無効。Cloud Console で publishr-498123 の課金を有効化。"
    if "PERMISSION_DENIED" in msg or "403" in msg:
        return "権限エラー（403）。Vertex なら ADC の権限/プロジェクト、AI Studio なら Generative Language API を確認。"
    if "prepayment credits are depleted" in msg:
        return "AI Studio の前払い残高がゼロ。ai.studio/projects でチャージするか --backend vertex に切替。"
    if "CERTIFICATE_VERIFY_FAILED" in msg:
        return "証明書検証失敗。`uv run --with truststore python -m ...` で再実行（社内CA委譲）。"
    return f"{type(exc).__name__}: {msg[:300]}"


def _setup_backend(backend: str, *, project: str, location: str) -> None:
    """google/adk を import する前に、選んだ実LLMバックエンドの env を確定させる。"""
    if backend == "aistudio":
        if not (os.environ.get("GOOGLE_API_KEY") or os.environ.get("GEMINI_API_KEY")):
            sys.stderr.write(_KEY_HELP)
            raise SystemExit(2)
        os.environ["GOOGLE_GENAI_USE_VERTEXAI"] = "FALSE"
    else:  # vertex（既存 run_*.py と同じ）
        os.environ["GOOGLE_GENAI_USE_VERTEXAI"] = "TRUE"
        os.environ.setdefault("GOOGLE_CLOUD_PROJECT", project)
        os.environ.setdefault("GOOGLE_CLOUD_LOCATION", location)


def _resolve_now(now_arg: str | None) -> datetime:
    if now_arg:
        s = now_arg[:-1] + "+00:00" if now_arg.endswith("Z") else now_arg
        dt = datetime.fromisoformat(s)
        return dt if dt.tzinfo else dt.replace(tzinfo=JST)
    return DEMO_NOW


def _dump(out_dir: Path, name: str, payload) -> Path:
    path = out_dir / name
    if isinstance(payload, str):
        path.write_text(payload, encoding="utf-8")
    else:
        path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return path


def _collect_urls(label: str, value) -> list[tuple[str, str]]:
    """value（dict/str/list）に含まれる http(s) URL を (label, url) で拾う。"""
    text = value if isinstance(value, str) else json.dumps(value, ensure_ascii=False)
    seen: set[str] = set()
    out: list[tuple[str, str]] = []
    for m in _URL_RE.findall(text):
        url = m.rstrip(".,;)")
        if url not in seen:
            seen.add(url)
            out.append((label, url))
    return out


def _grounding_md(planning: dict) -> str:
    rows: list[tuple[str, str]] = []
    rows += _collect_urls("subMarket(市場・競合)", planning.get("subMarket"))
    rows += _collect_urls("subThemeInsight(テーマ知見)", planning.get("subThemeInsight"))
    rows += _collect_urls("approvedPlan(企画書)", planning.get("approvedPlan"))
    lines = [
        "# Grounding 引用URL 照合チェックリスト",
        "",
        "standing manual flag（memory: grounding忠実性）。各URLを開き、**実在するか**＋"
        "**本文の主張と内容が一致するか**を人手で確認する。",
        "",
        f"抽出URL数: {len(rows)}",
        "",
    ]
    if not rows:
        lines.append("（URLが本文に1件も無い → grounding が効いていない可能性。要確認）")
    for label, url in rows:
        lines.append(f"- [ ] `{label}` {url}")
    return "\n".join(lines) + "\n"


def _summary_md(args, profile, planning: dict, personas, drafts: list) -> str:
    plan = planning.get("approvedPlan") or {}
    backend_label = (
        f"Vertex (project={os.environ.get('GOOGLE_CLOUD_PROJECT')})"
        if args.backend == "vertex"
        else "AI Studio APIキー"
    )
    lines = [
        f"# 品質バッチ run — {args.user}",
        "",
        f"- 実行時刻(JST): {datetime.now(JST).isoformat(timespec='seconds')}",
        f"- backend: {backend_label}",
        f"- few-shot: PROMPT_FEWSHOT={os.environ.get('PROMPT_FEWSHOT', 'on(既定)')}"
        "  ※✅例は u_sakura ベース。u_mita 被験時はリーク注意（memory: publishr-prompt-quality-loop）",
        f"- 段別LLM: reader={args.reader_llm} / plan・cast・preview={args.backend} / threshold={args.threshold}"
        + ("  [--cheap: 全工程flash]" if args.cheap else ""),
        "",
        "## STEP1 読者",
        f"- position: {profile.base.position if profile.base else '(なし)'}",
        f"- challenges: {len(profile.current_work.challenges) if profile.current_work else 0}件",
        "",
        "## STEP2 企画（差し戻し遷移）",
        f"- 仮テーマ: {planning.get('theme')}",
    ]
    for v in planning.get("verdictHistory", []):
        lines.append(f"  - R{v.get('round')}: score={v.get('score')} decision={v.get('decision')}")
    lines += [
        f"- rounds={planning.get('rounds')} forced_approve={planning.get('forced_approve')}",
        f"- 採用タイトル: {plan.get('tentativeTitle', '(なし)')}",
        "",
        "## STEP3 キャスティング",
    ]
    for p in personas.personas:
        fav = " ★お気に入り" if p.from_favorite else ""
        lines.append(f"- {p.name}: {p.voice_style} × {p.format}{fav}")
    lines += ["", "## STEP4 プレビュー draft"]
    for d in drafts:
        bd = d.get("bookDraft", {})
        v = d.get("verdict") or {}
        preface = bd.get("prefaceSample", "") or ""
        lines.append(f"- ◆ {bd.get('title', '(無題)')}")
        lines.append(
            f"    編集: score={v.get('score')} decision={v.get('decision')} "
            f"editRounds={d.get('editRounds')} / prefaceSample={len(preface)}字"
        )
    lines += [
        "",
        "## 次の照合（人手）",
        "- grounding_urls.md の各URLを開いて実在＋内容一致を確認",
        "- 02_planning.json の diffFromMarket / whyNowForYou が u_mita の局面に刺さっているか",
        "- 本文字数の実測は別途: `uv run --with truststore python -m scripts.run_body_once --book-id <id> --llm vertex`",
    ]
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(
        description="実LLM経路で STEP0→1→2→3→4 を一気通貫で回し出力をファイル化（既定 backend=vertex）"
    )
    parser.add_argument("--user", default="u_mita", help="被験ユーザー（既定 u_mita）")
    parser.add_argument("--backend", choices=["vertex", "aistudio"], default="vertex", help="実LLMバックエンド（既定 vertex）")
    parser.add_argument("--project", default="publishr-498123", help="Vertex の GCP プロジェクト")
    parser.add_argument("--location", default="asia-northeast1", help="Vertex のロケーション")
    parser.add_argument("--reader-llm", default="mock", choices=["mock", "real"], help="STEP1（既定 mock＝節約 / real=選択backend）")
    parser.add_argument("--theme", default=None, help="仮テーマ（省略時 ReaderProfile から導出）")
    parser.add_argument("--threshold", type=int, default=70, help="承認閾値（高いほど差し戻しを誘発）")
    parser.add_argument("--limit", type=int, default=None, help="STEP4 で処理する冊数の上限")
    parser.add_argument("--fewshot", choices=["on", "off", "keep"], default="keep", help="PROMPT_FEWSHOT 上書き")
    parser.add_argument(
        "--cheap",
        action="store_true",
        help="全工程を flash に固定（無料枠が緩い・端から端までの smoke 用。Pro 品質は落ちる）",
    )
    parser.add_argument("--out", default=str(_DEFAULT_OUT), help="出力ルート（既定 ../publishr_other/aistudio_runs）")
    parser.add_argument("--now", default=None, help="観測の基準時刻（ISO8601）")
    args = parser.parse_args()

    _harden_windows_tls()
    _setup_backend(args.backend, project=args.project, location=args.location)
    if args.fewshot != "keep":
        os.environ["PROMPT_FEWSHOT"] = args.fewshot
    if args.cheap:
        # provider.py は PUBLISHR_MODEL_PRO / _FLASH を尊重する。Pro を flash に倒してコスト/上限を抑える。
        os.environ["PUBLISHR_MODEL_PRO"] = os.environ.get("PUBLISHR_MODEL_FLASH", "gemini-2.5-flash")
        print("   [--cheap] 全工程 flash で実行（Pro 品質は出ない）", flush=True)
    # 段別 LLM: 内部関数は llm="vertex" で実LLM経路に入る（実バックエンドは env が決める）。
    reader_mode = "vertex" if args.reader_llm == "real" else "mock"

    from publishr_schema import PlanProposal, load_users

    user = next((u for u in load_users() if u.id == args.user), None)
    if user is None:
        raise SystemExit(f"ユーザーが見つかりません: {args.user}")

    out_dir = Path(args.out) / f"{args.user}_{datetime.now(JST).strftime('%Y%m%d_%H%M%S')}"
    out_dir.mkdir(parents=True, exist_ok=True)

    from publishr_agents.casting import cast_personas
    from publishr_agents.observe import FixtureObservationSource, collect_observation
    from publishr_agents.planning import run_planning
    from publishr_agents.preview import run_preview
    from publishr_agents.reader import analyze_reader

    now = _resolve_now(args.now)
    source = FixtureObservationSource()

    print(f"== 品質バッチ（backend={args.backend} user={args.user} reader={args.reader_llm} threshold={args.threshold}）==", flush=True)
    if args.backend == "vertex":
        print(f"   Vertex: project={os.environ.get('GOOGLE_CLOUD_PROJECT')} location={os.environ.get('GOOGLE_CLOUD_LOCATION')}", flush=True)
    print(f"   出力先: {out_dir}", flush=True)

    # STEP0 観測
    bundle = collect_observation(user, now=now, source=source)
    _dump(out_dir, "00_observation.json", {
        "drive": len(bundle.drive.files), "calendar": len(bundle.calendar.events), "tasks": len(bundle.tasks.items),
    })
    print(f"STEP0 観測: drive={len(bundle.drive.files)} calendar={len(bundle.calendar.events)} tasks={len(bundle.tasks.items)}", flush=True)

    # STEP1 読者
    profile = analyze_reader(bundle, user=user, llm=reader_mode)
    _dump(out_dir, "01_reader_profile.json", profile.model_dump(by_alias=True))
    print(f"STEP1 読者: {profile.base.position if profile.base else ''}", flush=True)

    planning: dict = {}
    try:
        # STEP2 企画（実Gemini・grounding）
        print("STEP2 企画（実Gemini・3サブ調査＋owner⇄leader 最大3R）… 実行中", flush=True)
        planning = run_planning(profile, theme=args.theme, threshold=args.threshold, llm="vertex")
        _dump(out_dir, "02_planning.json", planning)
        for v in planning.get("verdictHistory", []):
            print(f"  R{v.get('round')}: score={v.get('score')} decision={v.get('decision')}", flush=True)
        if not planning.get("approvedPlan"):
            _dump(out_dir, "grounding_urls.md", _grounding_md(planning))
            raise SystemExit("STEP2 で承認企画が出ませんでした（approvedPlan=None）。02_planning.json を確認。")
        plan = PlanProposal.model_validate(planning["approvedPlan"])
        print(f"STEP2 採用企画: {plan.tentative_title}", flush=True)

        # STEP3 キャスティング（実Gemini）
        print("STEP3 キャスティング（実Gemini）… 実行中", flush=True)
        personas = cast_personas(plan, reader_profile=profile, favorite_authors=list(user.favorite_authors or []), llm="vertex")
        _dump(out_dir, "03_casting.json", personas.model_dump(by_alias=True))
        print(f"STEP3 著者: {len(personas.personas)}人", flush=True)

        # STEP4 プレビュー（実Gemini・著者⇄編集長 1R）
        print(f"STEP4 プレビュー（実Gemini・limit={args.limit}）… 実行中", flush=True)
        drafts = run_preview(plan, personas.personas, reader_profile=profile, limit=args.limit, llm="vertex")
        _dump(out_dir, "04_preview.json", drafts)
        print(f"STEP4 draft: {len(drafts)}冊", flush=True)
    except SystemExit:
        raise
    except Exception as exc:  # noqa: BLE001 — 実LLM境界の例外を一行診断に落として中断
        if planning:
            _dump(out_dir, "grounding_urls.md", _grounding_md(planning))
        _dump(out_dir, "error.txt", _flatten_exc(exc))  # 生エラー全文（retryDelay/対象モデル/RPM・RPD 判別用）
        sys.stderr.write(f"\n[中断] 実Gemini呼び出しで失敗: {_diagnose(exc)}\n")
        sys.stderr.write(f"        生エラー: {out_dir / 'error.txt'}\n")
        sys.stderr.write(f"        途中までの出力: {out_dir}\n")
        return 1

    # grounding URL 照合チェックリスト ＋ 要約
    _dump(out_dir, "grounding_urls.md", _grounding_md(planning))
    _dump(out_dir, "summary.md", _summary_md(args, profile, planning, personas, drafts))

    print(f"\n✅ 完了: {out_dir}", flush=True)
    print("   - summary.md         … 全STEPの要約（まず読む）", flush=True)
    print("   - grounding_urls.md  … 引用URLの人手照合チェックリスト", flush=True)
    print("   - 00〜04_*.json      … 各STEPの生出力", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
