"""企画会議エージェントのプロンプト（packages/prompts/planning.json）を読み込む。

MVPは決定的キャンド出力だが、ペルソナ指示を実体として持つことで
将来 PUBLISHR_LLM=vertex に切り替えた際そのまま実プロンプトとして使える。"""

from __future__ import annotations

import json
import os
from functools import lru_cache
from pathlib import Path


def _prompts_dir() -> Path:
    override = os.environ.get("PUBLISHR_PROMPTS_DIR")
    if override:
        return Path(override)
    # prompts.py: agents/publishr_agents/prompts.py → parents[2] == repo root
    return Path(__file__).resolve().parents[2] / "packages" / "prompts"


@lru_cache
def planning_prompts() -> dict:
    with open(_prompts_dir() / "planning.json", encoding="utf-8") as f:
        return json.load(f)
