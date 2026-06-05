"""LLM モデル割当（Pro/Flash ハイブリッド）。P0bシーム＝mock経路では未使用。"""

from .provider import model_for, roles

__all__ = ["model_for", "roles"]
