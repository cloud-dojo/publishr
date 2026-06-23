from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, Query
from publishr_schema import Book

from ..deps import get_repository
from ..errors import NotFoundError
from ..repositories.protocol import RepositoryProtocol
from ..schemas import FeedbackInput, ReadingStateInput
from ..services import feedback_service, reading_service, reservation_service, write_queue
from .api import require_reserve_uid

router = APIRouter(prefix="/books", tags=["books"])


@router.get("", response_model=list[Book])
def list_books(
    status: Optional[str] = Query(None),
    shelf: Optional[str] = Query(None),
    repo: RepositoryProtocol = Depends(get_repository),
) -> list[Book]:
    return repo.list_books(status=status, shelf=shelf)


@router.get("/{book_id}", response_model=Book)
def get_book(book_id: str, repo: RepositoryProtocol = Depends(get_repository)) -> Book:
    book = repo.get_book(book_id)
    if book is None:
        raise NotFoundError(f"book {book_id} が見つかりません")
    return book


@router.post("/{book_id}/reserve", response_model=Book, deprecated=True)
async def reserve_book(
    book_id: str,
    repo: RepositoryProtocol = Depends(get_repository),
    _uid: str = Depends(require_reserve_uid),  # fail-closed: 課金時は認証必須
) -> Book:
    """旧予約モデルの互換エンドポイント（通常配本では使用しない）。"""
    book = reservation_service.reserve_now(repo, book_id, owner_uid=_uid)
    write_queue.enqueue(repo, book_id)
    return book


@router.post("/{book_id}/feedback", response_model=Book)
def post_feedback(
    book_id: str,
    payload: FeedbackInput,
    repo: RepositoryProtocol = Depends(get_repository),
) -> Book:
    return feedback_service.apply_feedback(repo, book_id, payload)


@router.post("/{book_id}/reading-state", response_model=Book)
def post_reading_state(
    book_id: str,
    payload: ReadingStateInput,
    repo: RepositoryProtocol = Depends(get_repository),
) -> Book:
    return reading_service.apply_reading_state(repo, book_id, payload)
