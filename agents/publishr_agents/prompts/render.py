"""プロンプトを実行用 instruction にレンダリングする（P0bシーム）。

- `{{var}}` と `{{a.b}}`（ネスト）を state から差し込む（ADKネイティブ注入はトップレベルのみのため
  自前で展開する）。
- few-shot: 採点系は常時ON、生成系は `PROMPT_FEWSHOT`（既定 on）で ON/OFF。生成系には overfit 防止注記を添える。
ADK には依存しない（ctx は `.state` を持つ duck-typing）。**mock経路では未使用**。
"""

from __future__ import annotations

import os
import re
from typing import Any, Callable

from .loader import load_prompt
from .registry import spec_for

_VAR = re.compile(r"\{\{\s*([A-Za-z0-9_.]+)\s*\}\}")
_OVERFIT_NOTE = "（形式・踏み込みの参考。内容はコピーせず、必ず入力に従うこと）"


def _resolve(path: str, state: dict) -> Any:
    cur: Any = state
    for part in path.split("."):
        cur = cur.get(part) if isinstance(cur, dict) else getattr(cur, part, None)
        if cur is None:
            return None
    return cur


def _inject(template: str, state: dict) -> str:
    def repl(match: re.Match) -> str:
        value = _resolve(match.group(1), state)
        return "" if value is None else str(value)

    return _VAR.sub(repl, template)


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
