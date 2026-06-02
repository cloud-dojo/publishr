from __future__ import annotations

from fastapi import APIRouter, Depends
from publishr_schema import User

from ..deps import get_repository
from ..errors import NotFoundError
from ..repositories.protocol import RepositoryProtocol

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/{user_id}", response_model=User)
def get_user(user_id: str, repo: RepositoryProtocol = Depends(get_repository)) -> User:
    user = repo.get_user(user_id)
    if user is None:
        raise NotFoundError(f"user {user_id} が見つかりません")
    return user
