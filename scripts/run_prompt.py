"""単発プロンプト実行CLI（C5.1・全11プロンプトの実テスト/調整用）。

任意の1ロールについて「最終的にLLMへ渡る system＋user」を組み立て、mock（=表示のみ・$0）か
実Vertex（gated・課金）で1回流す。プロンプト調整時に **パイプライン全体を回さず1本だけ** 速く
試すための道具。正本は packages/prompts/*.md（loader/render/registry を共有＝二重管理しない）。

  # 組み立てたプロンプトを表示するだけ（オフライン・$0）
  uv run python -m scripts.run_prompt --role plan_leader --from-eval eval_01

  # 実Vertex で1本流す（課金・要 PUBLISHR_RUN_VERTEX=1・ADC）
  PUBLISHR_RUN_VERTEX=1 uv run python -m scripts.run_prompt --role reader_analyst \
      --input eval/prompt_inputs/reader_analyst.json --backend vertex

  uv run python -m scripts.run_prompt --list   # ロール一覧

段階別の入力は --input（任意JSON＝state）か --from-eval（eval_set.yaml の plan+readerProfile）で渡す。
プロンプトの {{var}} は state から差し込まれる（render.render_template / build_system_text）。
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Any

from publishr_agents.llm.provider import model_for
from publishr_agents.prompts.loader import load_prompt, load_section_system
from publishr_agents.prompts.registry import REGISTRY, spec_for
from publishr_agents.prompts.render import build_system_text, render_template

ROOT = Path(__file__).resolve().parents[1]
EVAL_SET = ROOT / "eval" / "eval_set.yaml"
OUT_DIR = ROOT / ".dev-logs" / "prompt_runs"

# step2_research_subs は1ファイルに3サブの **system** を持つ → セクション見出しで切り出す。
SUB_SECTIONS = {
    "sub_reader_context": "読者局面",
    "sub_market": "市場・競合",
    "sub_theme_insight": "テーマ知見",
}
# B/C は google_search grounding（text出力・output_schema 併用しない）。
GROUNDED_ROLES = {"sub_market", "sub_theme_insight"}
_DEFAULT_USER = "上記の指示と入力に従って、出力仕様どおりに生成してください。"


def assemble(role: str, state: dict[str, Any]) -> dict[str, Any]:
    """role と state から、実行時に渡る system / user / model を組み立てる（純粋・$0・テスト可能）。"""
    spec = spec_for(role)
    doc = load_prompt(spec.prompt_file)
    if role in SUB_SECTIONS:
        # サブはセクション単体の **system** を使う（merged ファイルではなく）。
        system = render_template(load_section_system(spec.prompt_file, SUB_SECTIONS[role]), state)
    else:
        system = build_system_text(role, state)  # few-shot 注入規律込み（採点系は常時ON）
    user = render_template(doc.user_template, state) if doc.user_template else _DEFAULT_USER
    return {
        "role": role,
        "model": model_for(role),
        "system": system,
        "user": user,
        "grounded": role in GROUNDED_ROLES,
        "structured": spec.output_schema is not None and role not in GROUNDED_ROLES,
        "is_scoring": spec.is_scoring,
    }


def _ensure_vertex_env() -> None:
    os.environ.setdefault("GOOGLE_GENAI_USE_VERTEXAI", "TRUE")
    os.environ.setdefault("GOOGLE_CLOUD_PROJECT", "publishr-498123")
    os.environ.setdefault("GOOGLE_CLOUD_LOCATION", "asia-northeast1")


def run_vertex(plan: dict[str, Any], *, temperature: float) -> str:
    """実Vertex で1回生成して応答テキストを返す（課金）。"""
    from google import genai
    from google.genai import types

    _ensure_vertex_env()
    client = genai.Client(
        vertexai=True,
        project=os.environ["GOOGLE_CLOUD_PROJECT"],
        location=os.environ["GOOGLE_CLOUD_LOCATION"],
    )
    cfg = types.GenerateContentConfig(
        system_instruction=plan["system"], temperature=temperature
    )
    if plan["grounded"]:
        try:
            cfg.tools = [types.Tool(google_search=types.GoogleSearch())]
        except Exception:  # noqa: BLE001 — SDK差異時は grounding 無しで続行（理由を表示）
            print("⚠ google_search tool を付与できず grounding 無しで実行します")
    elif plan["structured"]:
        cfg.response_mime_type = "application/json"
    resp = client.models.generate_content(model=plan["model"], contents=plan["user"], config=cfg)
    return resp.text or ""


def _load_state(args: argparse.Namespace) -> dict[str, Any]:
    if args.from_eval:
        import yaml  # noqa: PLC0415

        data = yaml.safe_load(EVAL_SET.read_text(encoding="utf-8"))
        case = next((c for c in data.get("cases", []) if c.get("id") == args.from_eval), None)
        if case is None:
            raise SystemExit(f"eval_set に case {args.from_eval!r} がありません")
        plan = case.get("plan")
        reader = data.get("readerProfile")
        # 採点系/企画系テンプレが参照しうるエイリアスを広めに用意（未使用キーは無害）。
        return {
            "plan": plan, "planDraft": plan, "approvedPlan": plan,
            "readerProfile": reader,
        }
    if args.input:
        if args.input == "-":
            import sys  # noqa: PLC0415

            raw = sys.stdin.read()
        else:
            raw = Path(args.input).read_text(encoding="utf-8")
        return json.loads(raw)
    return {}


def main() -> int:
    parser = argparse.ArgumentParser(description="単発プロンプト実行（C5.1）")
    parser.add_argument("--role", help=f"ロール（{', '.join(REGISTRY)}）")
    parser.add_argument("--input", help="state を渡すJSONファイル（'-'=stdin）")
    parser.add_argument("--from-eval", help="eval_set.yaml の case id（plan+readerProfile を state に）")
    parser.add_argument("--backend", default="mock", choices=["mock", "vertex"])
    parser.add_argument("--temperature", type=float, default=0.0)
    parser.add_argument("--save", action="store_true", help=".dev-logs/prompt_runs/ に保存")
    parser.add_argument("--list", action="store_true", help="ロール一覧を表示して終了")
    args = parser.parse_args()

    if args.list:
        for role, spec in REGISTRY.items():
            tier = spec.model_role
            tag = "採点" if spec.is_scoring else "生成"
            print(f"  {role:20s} {tag}  file={spec.prompt_file}  model={model_for(role)}")
        return 0

    if not args.role:
        raise SystemExit("--role を指定してください（--list で一覧）")
    if args.role not in REGISTRY:
        raise SystemExit(f"unknown role: {args.role}（--list で一覧）")
    if args.backend == "vertex" and os.environ.get("PUBLISHR_RUN_VERTEX") != "1":
        raise SystemExit("実Vertex は課金です。PUBLISHR_RUN_VERTEX=1 を付けて実行してください（ADC要）")

    state = _load_state(args)
    plan = assemble(args.role, state)

    print(f"== role={plan['role']} model={plan['model']} "
          f"({'採点' if plan['is_scoring'] else '生成'}"
          f"{' / grounded' if plan['grounded'] else ''}"
          f"{' / structured-json' if plan['structured'] else ''}) ==")
    print("\n----- SYSTEM -----\n" + plan["system"])
    print("\n----- USER -----\n" + plan["user"])

    output = None
    if args.backend == "vertex":
        print("\n----- VERTEX OUTPUT -----")
        output = run_vertex(plan, temperature=args.temperature)
        print(output)

    if args.save:
        OUT_DIR.mkdir(parents=True, exist_ok=True)
        out_file = OUT_DIR / f"{plan['role']}.json"
        out_file.write_text(
            json.dumps(
                {"role": plan["role"], "model": plan["model"], "system": plan["system"],
                 "user": plan["user"], "output": output},
                ensure_ascii=False, indent=2,
            ),
            encoding="utf-8",
        )
        print(f"\nsaved: {out_file}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
