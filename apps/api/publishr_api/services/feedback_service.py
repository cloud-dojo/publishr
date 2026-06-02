"""読後フィードバックの反映（★評価・続編希望・読了率など）。"""

from __future__ import annotations

from publishr_schema import Book

from ..errors import NotFoundError
from ..repositories.protocol import RepositoryProtocol
from ..schemas import FeedbackInput


def apply_feedback(repo: RepositoryProtocol, book_id: str, payload: FeedbackInput) -> Book:
    book = repo.get_book(book_id)
    if book is None:
        raise NotFoundError(f"book {book_id} が見つかりません")
    updates = payload.model_dump(exclude_unset=True)
    new_feedback = book.feedback.model_copy(update=updates)
    return repo.upsert_book(book.model_copy(update={"feedback": new_feedback}))
