"""プロンプトを実行用 instruction にレンダリングする（P0bシーム）。

- `{{var}}` と `{{a.b}}`（ネスト）を state から差し込む（ADKネイティブ注入はトップレベルのみのため
  自前で展開する）。
- few-shot: 採点系は常時ON、生成系は `PROMPT_FEWSHOT`（既定 on）で ON/OFF。生成系には overfit 防止注記を添える。
ADK には依存しない（ctx は `.state` を持つ duck-typing）。**mock経路では未使用**。
"""

from __future__ import annotations

import json
import os
import re
from typing import Any, Callable

from .loader import load_prompt
from .registry import spec_for

_VAR = re.compile(r"\{\{\s*([A-Za-z0-9_.]+)\s*\}\}")
_OVERFIT_NOTE = "（形式・踏み込みの参考。内容はコピーせず、必ず入力に従うこと）"


def _resolve(path: str, state: Any) -> Any:
    cur: Any = state
    for part in path.split("."):
        # ADK の State は dict 非継承の Mapping。pydantic 等は属性アクセス。
        if hasattr(cur, "get") and not hasattr(cur, "model_fields"):
            try:
                cur = cur.get(part)
            except Exception:
                cur = None
        else:
            cur = getattr(cur, part, None)
        if cur is None:
            return None
    return cur


def _stringify(value: Any) -> str:
    if hasattr(value, "model_dump"):  # pydantic（ADKがstateに型のまま入れる場合）
        try:
            value = value.model_dump(by_alias=True)
        except Exception:
            pass
    if isinstance(value, (dict, list)):
        return json.dumps(value, ensure_ascii=False)
    return str(value)


def _inject(template: str, state: dict) -> str:
    def repl(match: re.Match) -> str:
        value = _resolve(match.group(1), state)
        return "" if value is None else _stringify(value)

    text = _VAR.sub(repl, template)
    # 未解決の {{...}}（空白/記号入りで非対応）は波括弧を外して素通し（LLMに生の波括弧を見せない）
    return re.sub(r"\{\{(.*?)\}\}", lambda m: m.group(1).strip(), text)


def render_template(template: str, state: dict | None = None) -> str:
    """{{var}} / {{a.b}} を state から差し込む（公開API・MiniLoop等の入力ブロック組立に使用）。"""
    return _inject(template, state or {})


def fewshot_enabled(role: str) -> bool:
    spec = spec_for(role)
    if spec.fewshot_always_on:
        return True
    return os.environ.get("PROMPT_FEWSHOT", "on").lower() != "off"


def build_system_text(role: str, state: dict | None = None) -> str:
    spec = spec_for(role)
    doc = load_prompt(spec.prompt_file)
    text = _inject(doc.system, state or {})
    if doc.good_example and fewshot_enabled(role):
        note = "" if spec.is_scoring else f"\n{_OVERFIT_NOTE}"
        text = f"{text}\n\n# 参考出力例{note}\n```\n{doc.good_example}\n```"
    return text


def make_instruction(role: str) -> Callable[[Any], str]:
    """ADK LlmAgent.instruction 用の InstructionProvider を返す。"""

    def _provider(ctx: Any) -> str:
        state = getattr(ctx, "state", {}) or {}
        return build_system_text(role, state)

    return _provider
