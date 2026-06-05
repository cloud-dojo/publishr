"""LLM モデル割当の単一情報源（Pro/Flash ハイブリッド）。

role → Gemini モデルid を一元管理する。**mock経路では未使用＝P0bの実装シーム**。
判断が重い工程＝Pro／観測・調査寄り＝Flash（正本: docs/design/adk-control-flow.md §5・
agent-io-contract.md §9）。実モデルidは env（PUBLISHR_MODEL_PRO / _FLASH）で上書き可。
"""

from __future__ import annotations

import os

PRO_DEFAULT = "gemini-2.5-pro"
FLASH_DEFAULT = "gemini-2.5-flash"

# role → tier（"pro" | "flash"）。registry.StepSpec.model_role と一致させる。
_ROLE_TIER: dict[str, str] = {
    "reader_analyst": "pro",
    "sub_reader_context": "flash",
    "sub_market": "flash",
    "sub_theme_insight": "flash",
    "plan_owner": "pro",
    "plan_leader": "pro",
    "persona_generator": "pro",
    "author_preview": "pro",
    "editor_preview": "pro",
    "cover": "flash",
    "modeb_author": "pro",
    "modeb_editor": "pro",
    "eval_judge": "pro",
}


def _pro() -> str:
    return os.environ.get("PUBLISHR_MODEL_PRO", PRO_DEFAULT)


def _flash() -> str:
    return os.environ.get("PUBLISHR_MODEL_FLASH", FLASH_DEFAULT)


def model_for(role: str) -> str:
    """role に対応する Gemini モデルid を返す。未知 role は KeyError。"""
    try:
        tier = _ROLE_TIER[role]
    except KeyError as exc:
        raise KeyError(f"unknown agent role: {role!r}") from exc
    return _pro() if tier == "pro" else _flash()


def roles() -> list[str]:
    return list(_ROLE_TIER)
