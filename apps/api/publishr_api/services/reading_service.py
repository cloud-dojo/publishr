"""読書中の表示粒度・ハイライト・付箋の反映。"""

from __future__ import annotations

from publishr_schema import Book, ReadingAnnotation

from ..errors import NotFoundError
from ..repositories.protocol import RepositoryProtocol
from ..schemas import ReadingStateInput


def apply_reading_state(repo: RepositoryProtocol, book_id: str, payload: ReadingStateInput) -> Book:
    book = repo.get_book(book_id)
    if book is None:
        raise NotFoundError(f"book {book_id} が見つかりません")

    updates: dict[str, object] = {}
    if payload.granularity is not None:
        updates["granularity"] = payload.granularity
    if payload.annotations is not None:
        updates["annotations"] = [
            ReadingAnnotation.model_validate(annotation.model_dump())
            for annotation in payload.annotations
        ]
    return repo.upsert_book(book.model_copy(update=updates))
