"""プロンプト・パッケージ。

- `legacy.planning_prompts()`: 旧 planning.json（mock パイプラインの企画者名に使用・後方互換）。
- `loader` / `registry` / `render`: v2 本番プロンプト（packages/prompts/*.md）の実行用シーム
  （**mock経路では未使用＝P0b**）。循環 import を避けるため __init__ では薄く planning_prompts のみ公開し、
  v2 シームはサブモジュール（`publishr_agents.prompts.loader` 等）から直接 import する。
"""

from .legacy import planning_prompts

__all__ = ["planning_prompts"]
