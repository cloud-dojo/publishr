"""旧構想 planning.json ローダ（mock パイプラインの企画者名のみに使用・後方互換）。

新構想の本番プロンプトは `loader.py`（packages/prompts/*.md）。本モジュールは mock の
ParallelAgent 企画者名のために planning.json を読むだけ。`PUBLISHR_PROMPTS_DIR` で上書き可。
"""

from __future__ import annotations

import json
import os
from functools import lru_cache
from pathlib import Path


def _prompts_dir() -> Path:
    override = os.environ.get("PUBLISHR_PROMPTS_DIR")
    if override:
        return Path(override)
    # legacy.py: agents/publishr_agents/prompts/legacy.py → parents[3] == repo root
    return Path(__file__).resolve().parents[3] / "packages" / "prompts"


@lru_cache
def planning_prompts() -> dict:
    with open(_prompts_dir() / "planning.json", encoding="utf-8") as f:
        return json.load(f)
