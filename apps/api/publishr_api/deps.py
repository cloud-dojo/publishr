"""依存性注入: 設定に応じてリポジトリ実装を返す（シングルトン）。"""

from __future__ import annotations

from functools import lru_cache

from .config import settings
from .repositories.mock_repository import MockRepository
from .repositories.protocol import RepositoryProtocol


@lru_cache
def get_repository() -> RepositoryProtocol:
    if settings.data_source == "firestore":
        from .repositories.firestore_repository import FirestoreRepository

        return FirestoreRepository(owner_uid=settings.demo_uid)
    return MockRepository()
