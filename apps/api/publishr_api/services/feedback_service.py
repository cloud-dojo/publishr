"""読後フィードバックの反映（★評価・続編希望・読了率など）。"""

from __future__ import annotations

from datetime import datetime, timezone

from publishr_schema import Book

from ..errors import NotFoundError
from ..repositories.protocol import RepositoryProtocol
from ..schemas import FeedbackInput


def apply_feedback(repo: RepositoryProtocol, book_id: str, payload: FeedbackInput) -> Book:
    book = repo.get_book(book_id)
    if book is None:
        raise NotFoundError(f"book {book_id} が見つかりません")
    updates = payload.model_dump(exclude_unset=True)
    # 読了率の更新＝読書イベント。最後に読んだ時刻をサーバ側で刻む（「最近読んだ本」の並び順）。
    # クライアント送信値は信用せず、read_percent が来たら常にサーバ時刻で上書きする。
    if updates.get("read_percent") is not None:
        updates["last_read_at"] = datetime.now(timezone.utc).isoformat()
    new_feedback = book.feedback.model_copy(update=updates)
    return repo.upsert_book(book.model_copy(update={"feedback": new_feedback}))
