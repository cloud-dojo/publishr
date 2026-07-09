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
    "editor_chief_themes": "pro",    # v3 4テーマ: 編集長テーマ設定（棚の背骨・判断が重い）
    "sub_reader_context": "flash",
    "sub_market": "flash",
    "sub_theme_insight": "flash",
    "sub_trend": "flash",            # v3 4テーマ: トレンド調査（grounding・抽出寄り）
    "sub_competitors": "flash",      # v3 4テーマ: 競合書籍調査（grounding・抽出寄り）
    "sub_classics": "flash",         # v3 4テーマ: 古典・本質調査（grounding・抽出寄り）
    "plan_owner": "pro",
    "plan_leader": "pro",
    "editor_chief_gate": "pro",      # v3 4テーマ: 編集長セットゲート（ポートフォリオ採点・判断が重い）
    "author_casting": "pro",         # v3 4テーマ: 著者キャスティング（人格設計・判断が重い）
    "serendipity_themes": "pro",     # v3: セレンディピティのテーマ選定（判断が重い）
    "persona_generator": "pro",
    "author_preview": "pro",
    "editor_preview": "pro",
    # ⚠️ PARKED（将来実装・画像生成）: cover は現行メインパイプライン未接続。将来の装丁再結線用に温存。
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
