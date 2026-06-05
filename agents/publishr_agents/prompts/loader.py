"""packages/prompts/*.md から実行用プロンプトを抽出する（P0bシーム）。

各 .md は「1ファイル＝1エージェント仕様」。system プロンプトは
`## 完成プロンプト（system）` 直後のフェンス、または（step2_research_subs のみ）
各 `**system**:` 直後のフェンスから抽出する。user template / ✅良い例も任意で取り出す。
`PUBLISHR_PROMPTS_DIR` で参照先を上書き可。
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Callable, Optional


def prompts_dir() -> Path:
    override = os.environ.get("PUBLISHR_PROMPTS_DIR")
    if override:
        return Path(override)
    # loader.py: agents/publishr_agents/prompts/loader.py → parents[3] == repo root
    return Path(__file__).resolve().parents[3] / "packages" / "prompts"


@dataclass(frozen=True)
class PromptDoc:
    name: str
    system: str
    user_template: Optional[str]
    good_example: Optional[str]


def _read_lines(name: str) -> list[str]:
    return (prompts_dir() / f"{name}.md").read_text(encoding="utf-8").splitlines()


def _fence_after(lines: list[str], start: int) -> Optional[tuple[str, int]]:
    """start 以降で最初のフェンスブロックを返す → (本文, 閉じフェンスの次index)。"""
    i = start
    n = len(lines)
    while i < n and not lines[i].lstrip().startswith("```"):
        i += 1
    if i >= n:
        return None
    i += 1  # 開きフェンスの次へ
    body: list[str] = []
    while i < n and not lines[i].lstrip().startswith("```"):
        body.append(lines[i])
        i += 1
    return "\n".join(body).strip(), i + 1


def _collect_blocks(lines: list[str], is_marker: Callable[[str], bool]) -> list[str]:
    blocks: list[str] = []
    i = 0
    n = len(lines)
    while i < n:
        if is_marker(lines[i]):
            found = _fence_after(lines, i + 1)
            if found:
                body, nxt = found
                if body:
                    blocks.append(body)
                    i = nxt
                    continue
        i += 1
    return blocks


def _is_system_marker(line: str) -> bool:
    s = line.strip()
    return ("完成プロンプト（system）" in s) or s.startswith("**system**")


def _is_user_marker(line: str) -> bool:
    return "完成プロンプト（user template）" in line


def _is_good_marker(line: str) -> bool:
    s = line.strip()
    return s.startswith("#") and "✅" in s


@lru_cache
def load_prompt(name: str) -> PromptDoc:
    lines = _read_lines(name)
    system_blocks = _collect_blocks(lines, _is_system_marker)
    if not system_blocks:
        raise ValueError(f"no system prompt block found in {name}.md")
    user_blocks = _collect_blocks(lines, _is_user_marker)
    good_blocks = _collect_blocks(lines, _is_good_marker)
    return PromptDoc(
        name=name,
        system="\n\n".join(system_blocks),
        user_template=user_blocks[0] if user_blocks else None,
        good_example=good_blocks[0] if good_blocks else None,
    )
