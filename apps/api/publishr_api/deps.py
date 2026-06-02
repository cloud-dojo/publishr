"""依存性注入: 設定に応じてリポジトリ実装を返す（シングルトン）。"""

from __future__ import annotations

from functools import lru_cache

from .config import settings
from .repositories.mock_repository import MockRepository
from .repositories.protocol import RepositoryProtocol


@lru_cache
def get_repository() -> RepositoryProtocol:
    if settings.data_source == "firestore":
        raise NotImplementedError("Firestore は将来対応（MVPは DATA_SOURCE=mock）")
    return MockRepository()
