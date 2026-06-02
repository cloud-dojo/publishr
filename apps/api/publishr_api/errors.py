"""ドメインエラー（HTTPステータスへ変換される）。"""

from __future__ import annotations


class NotFoundError(Exception):
    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


class ConflictError(Exception):
    """不正な状態遷移など（例: 既に予約済みの本を再予約）。"""

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message
