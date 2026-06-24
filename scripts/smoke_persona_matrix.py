"""被験者ブロック生成（verify-prompts インナーループ用・$0・オフライン・ADK非依存）。

本番（各 vertex_agent）と同形の被験者プロンプトを fixtures から決定的に組む：

    system = build_system_text(role, state) + "\\n\\n# 入力\\n" + render_template(<role入力テンプレ>, state)

- responseSchema ＝ registry の output_schema の JSON schema（AI Studio の Structured output 相当）
- model ＝ 本番tier（Pro→opus / Flash→sonnet）
- 入力 fixture の `_meta`（検証用の注釈）は除去して本体のみ流す（本番が渡す範囲に合わせる）

入力テンプレ（`_*_INPUTS`）は各 vertex_agent の写し。**正本はそちら**（ADK を引かないため複製）。
本モジュールは Claude/Vertex/GCP/ADK を一切 import しない純粋関数。verify-prompts スキルが
本モジュールの出力を Agent ツール（被験者）に渡し、出力を smoke_discipline で検査する。

  uv run python -m scripts.smoke_persona_matrix --role persona_generator --persona u_sakura --theme honmei
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from publishr_schema import ReaderProfile3Layer, fixtures_dir  # noqa: E402

from publishr_agents.llm.provider import _ROLE_TIER  # noqa: E402
from publishr_agents.prompts import loader, render  # noqa: E402
from publishr_agents.prompts.registry import spec_for  # noqa: E402

# ── 入力テンプレ（各 vertex_agent の "# 入力" 以降の写し・正本はそちら） ──────────
# planning/vertex_agent.py
_SUB_READER_INPUTS = """# 読者プロファイル(3層・特に currentWork)
{{readerProfile}}
# themeKind
{{themeKind}}
# 仮テーマ
{{tentativeTheme}}
subReaderContext のJSONのみを出力せよ。"""

_SUB_MARKET_INPUTS = """# 仮テーマ
{{tentativeTheme}}
# 読者(base)
{{readerBase}}
出力: 売れ筋・既製本・marketGap を含む調査結果（実在書名・出典URLを可能な限り付す）。"""

_SUB_THEME_INPUTS = """# 仮テーマ
{{tentativeTheme}}
出力: 章立ての根拠になる keyPoints（出典URLを可能な限り付す）。"""

_LEADER_INPUTS = """# 企画書(PlanProposal)
{{planDraft}}
# 読者プロファイル(3層)
{{readerProfile}}
# 市場調査(subMarket・差別化と調査反映の判定材料)
{{subMarket}}
# themeKind
{{themeKind}}
# threshold
{{threshold}}
# round（このラウンド番号）
{{round}}
注: round が 3 のときは、たとえ弱くても最良案を必ず decision="approve" とせよ（revise 禁止＝棚を空にしない）。
LeaderVerdict のJSONのみを出力せよ。"""

# casting/vertex_agent.py
_CASTING_INPUTS = """# 承認企画(PlanProposal・8項目)
{{approvedPlan}}
# 読者プロファイル(stylePreference 参照)
{{readerProfile}}
# お気に入り著者（任意・約15%で1枠採用・空なら採用なし）
{{favoriteAuthors}}
GeneratedPersonaSet（personas[5]＋reason）のJSONのみを出力せよ。"""

# grounding（google_search）併用ロール＝被験者には WebSearch を許可（結果は Gemini grounding の近似）。
_GROUNDING_ROLES = {"sub_market", "sub_theme_insight"}

# user メッセージ（本番の起動トリガー。入力は全て system 側にあるので便宜上の文）。
_TRIGGER = {
    "reader_analyst": "観測データから読者プロファイル(3層)を作成してください",
    "sub_reader_context": "調査（読者局面）を実施してください",
    "sub_market": "調査（市場・競合）を実施してください",
    "sub_theme_insight": "調査（テーマ知見）を実施してください",
    "plan_owner": "企画書を作成してください",
    "plan_leader": "企画書を採点してください",
    "persona_generator": "この企画に合う著者を4人キャスティングしてください",
    "editor_chief_themes": "今週の棚の編集意図と4サブテーマ（各チーム割当）を決めてください",
    "serendipity_themes": "セレンディピティの4テーマを選んでください",
    "author_casting": "この企画に合う著者候補を3人生成し、最適な1人を選抜してください",
}


def subject_model(role: str) -> str:
    """本番tier（Pro/Flash）→ Claude被験者モデル（opus/sonnet）。未知 role は KeyError。"""
    try:
        tier = _ROLE_TIER[role]
    except KeyError as exc:
        raise KeyError(f"unknown role: {role!r}") from exc
    return "opus" if tier == "pro" else "sonnet"


# ── fixtures ───────────────────────────────────────────────
def _fx() -> Path:
    return fixtures_dir()


def _strip_meta(d: Any) -> Any:
    """`_` 始まりキー（`_meta` 等の注釈）を除去（本番が渡さないため）。"""
    if isinstance(d, dict):
        return {k: v for k, v in d.items() if not (isinstance(k, str) and k.startswith("_"))}
    return d


def _load_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _reader_profile(persona: str) -> dict:
    return _strip_meta(_load_json(_fx() / "reader_profiles" / f"{persona}.json"))


def _plan(persona: str, theme_kind: str) -> dict:
    return _strip_meta(_load_json(_fx() / "plan_proposals" / f"{persona}_{theme_kind}.json"))


def _user(persona: str) -> dict:
    users = _load_json(_fx() / "users.json")
    rows = users if isinstance(users, list) else users.get("users", [])
    for u in rows:
        if u.get("id") == persona or u.get("uid") == persona:
            return u
    raise KeyError(f"user not found in users.json: {persona!r}")


def _parse_dt(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def _derive_theme(persona: str, theme_kind: str, profile: dict) -> str:
    """planning.deterministic.derive_theme を遅延 import で再利用（ADK非依存）。"""
    from publishr_agents.planning.deterministic import derive_theme  # noqa: PLC0415

    return derive_theme(ReaderProfile3Layer.model_validate(profile), theme_kind)


def build_state(
    role: str,
    persona: str,
    theme_kind: str = "honmei",
    *,
    favorite_authors: Optional[list[dict[str, Any]]] = None,
    prev_outputs: Optional[dict[str, Any]] = None,
    threshold: int = 70,
    round: int = 1,
    theme: Optional[str] = None,
    now: Optional[datetime] = None,
) -> dict[str, Any]:
    """role 別に本番 init_state と同形の state を fixtures から組む。"""
    prev = prev_outputs or {}

    if role == "reader_analyst":
        # observationBundle は observe.fixture_source（決定的・オフライン）で本番同経路に組む。
        from publishr_agents.observe.fixture_source import FixtureObservationSource  # noqa: PLC0415
        from publishr_schema import User  # noqa: PLC0415

        user = User.model_validate(_user(persona))
        if now is None:
            rp = _load_json(_fx() / "reader_profiles" / f"{persona}.json")
            now = _parse_dt(rp.get("generatedAt")) or datetime.now(timezone.utc)
        bundle = FixtureObservationSource().collect(user, now=now)
        return {
            "observationBundle": bundle.model_dump(by_alias=True),
            "prevProfile": None,
            "initialProfile": user.initial_profile.model_dump(by_alias=True) if user.initial_profile else None,
        }

    profile = _reader_profile(persona)
    needs_theme = role in ("sub_reader_context", "sub_market", "sub_theme_insight", "plan_owner", "plan_leader")
    if theme is None and needs_theme:
        theme = _derive_theme(persona, theme_kind, profile)

    if role == "sub_reader_context":
        return {"readerProfile": profile, "themeKind": theme_kind, "tentativeTheme": theme}
    if role == "sub_market":
        return {"tentativeTheme": theme, "readerBase": profile.get("base", {})}
    if role == "sub_theme_insight":
        return {"tentativeTheme": theme}
    if role == "plan_owner":
        return {
            "readerProfile": profile,
            "themeKind": theme_kind,
            "subReaderContext": prev.get("subReaderContext"),
            "subMarket": prev.get("subMarket"),
            "subThemeInsight": prev.get("subThemeInsight"),
            "rejectionFeedback": prev.get("rejectionFeedback"),
        }
    if role == "plan_leader":
        return {
            "planDraft": prev.get("planDraft") or _plan(persona, theme_kind),
            "readerProfile": profile,
            "subMarket": prev.get("subMarket"),
            "themeKind": theme_kind,
            "threshold": threshold,
            "round": round,
        }
    if role == "persona_generator":
        return {
            "approvedPlan": _plan(persona, theme_kind),
            "readerProfile": profile,
            "favoriteAuthors": favorite_authors or [],
        }
    # v3 4テーマ1-1-1-1（2026-06-23）: 編集長テーマ設定 / セレンディピティ / 著者キャスティング。
    # 入力は各 .md の user_template（loaderが抽出＝本番I/O正本）を使う＝vertex_agent写しに依存しない。
    if role in ("editor_chief_themes", "serendipity_themes"):
        return {"readerProfile": profile, "themeKind": theme_kind}
    if role == "author_casting":
        return {
            "approvedPlan": _plan(persona, theme_kind),
            "readerProfile": profile,
            "favoriteAuthors": favorite_authors or [],
        }
    raise KeyError(f"unsupported role for matrix: {role!r}")


def _input_template(role: str) -> str:
    if role == "reader_analyst":
        return loader.load_prompt("step1_reader_analyst").user_template or ""
    if role == "plan_owner":
        return loader.load_prompt("step2_plan_owner").user_template or ""
    # 新STEP2-0/3 role は各 .md の user_template を正本に使う（vertex_agent 写しに依存しない）
    if role in ("editor_chief_themes", "serendipity_themes", "author_casting"):
        return loader.load_prompt(spec_for(role).prompt_file).user_template or ""
    return {
        "sub_reader_context": _SUB_READER_INPUTS,
        "sub_market": _SUB_MARKET_INPUTS,
        "sub_theme_insight": _SUB_THEME_INPUTS,
        "plan_leader": _LEADER_INPUTS,
        "persona_generator": _CASTING_INPUTS,
    }[role]


def subject_block(
    role: str,
    persona: str = "u_sakura",
    theme_kind: str = "honmei",
    *,
    favorite_authors: Optional[list[dict[str, Any]]] = None,
    prev_outputs: Optional[dict[str, Any]] = None,
    threshold: int = 70,
    round: int = 1,
    theme: Optional[str] = None,
    now: Optional[datetime] = None,
) -> dict[str, Any]:
    """本番フェイスフルな被験者ブロックを返す。

    戻り: {role, persona, themeKind, model, system, responseSchema, trigger}
    - system ＝ build_system_text（few-shot本番条件込み）＋ "# 入力" ＋ 役割別入力ブロック
    - responseSchema ＝ output_schema の JSON schema（無スキーマ role は None）
    - model ＝ opus/sonnet（本番tier対応）
    """
    spec = spec_for(role)  # 未知 role はここで KeyError
    state = build_state(
        role, persona, theme_kind,
        favorite_authors=favorite_authors, prev_outputs=prev_outputs,
        threshold=threshold, round=round, theme=theme, now=now,
    )
    system = (
        render.build_system_text(role, state)
        + "\n\n# 入力\n"
        + render.render_template(_input_template(role), state)
    )
    response_schema = spec.output_schema.model_json_schema(by_alias=True) if spec.output_schema else None
    return {
        "role": role,
        "persona": persona,
        "themeKind": theme_kind,
        "model": subject_model(role),
        "system": system,
        "responseSchema": response_schema,
        "grounding": role in _GROUNDING_ROLES,  # True なら被験者に WebSearch を許可（grounding近似）
        "trigger": _TRIGGER.get(role, "指示に従って指定スキーマのJSONのみを出力してください"),
    }


def main(argv: Optional[list[str]] = None) -> int:
    p = argparse.ArgumentParser(description="被験者ブロック生成（verify-prompts用・$0・ADK非依存）")
    p.add_argument("--role", required=True, help="registry のrole（persona_generator / plan_owner 等）")
    p.add_argument("--persona", default="u_sakura", help="u_sakura / u_mita")
    p.add_argument("--theme", default="honmei", help="themeKind: honmei / serendipity")
    p.add_argument("--favorites", help="favoriteAuthors JSON のパス（任意）")
    p.add_argument("--prev", help="prev_outputs JSON のパス（任意・前段出力の連結）")
    p.add_argument("--round", type=int, default=1)
    p.add_argument("--threshold", type=int, default=70)
    p.add_argument("--json", action="store_true", help="ブロック全体を機械可読JSONで出力")
    args = p.parse_args(argv)

    favs = _load_json(Path(args.favorites)) if args.favorites else None
    prev = _load_json(Path(args.prev)) if args.prev else None
    blk = subject_block(
        args.role, args.persona, args.theme,
        favorite_authors=favs, prev_outputs=prev, round=args.round, threshold=args.threshold,
    )
    if args.json:
        print(json.dumps(blk, ensure_ascii=False, indent=2))
    else:
        print(f"# model\n{blk['model']}\n")
        print(f"# system\n{blk['system']}\n")
        sch = json.dumps(blk["responseSchema"], ensure_ascii=False) if blk["responseSchema"] else "(なし)"
        print(f"# responseSchema\n{sch}\n")
        print(f"# trigger\n{blk['trigger']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
